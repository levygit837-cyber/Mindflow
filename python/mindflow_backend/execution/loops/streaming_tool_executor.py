"""StreamingToolExecutor - Executa ferramentas conforme chegam no stream.

Executa ferramentas em paralelo quando são concurrent-safe,
com controle de concorrência via semáforo e abort controller
para cancelar subprocessos em caso de erro.

Inspirado no StreamingToolExecutor do Claude Code.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from mindflow_backend.hooks.handlers.permission_hook import (
    PermissionDeniedHandler,
    PermissionRequestHandler,
)
from mindflow_backend.hooks.manager import HookManager
from mindflow_backend.hooks.processor import HookResultProcessor
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.infra.error_handling import (
    classify_error,
    ErrorCategory,
    StreamingWatchdog,
    is_retryable,
    get_retry_delay,
    QuerySource,
)
from mindflow_backend.schemas.tools.result import ToolResult
from mindflow_backend.schemas.tools.streaming_types import (
    AbortController,
    StreamingToolResult,
    ToolExecutionAbortedError,
    ToolStatus,
    TrackedTool,
    create_child_abort_controller,
)
from mindflow_backend.execution.loops.tool_partition import partition_tool_calls

_logger = get_logger(__name__)


class CanUseToolFn(Protocol):
    """Protocol para função de verificação de permissão."""

    async def __call__(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> tuple[bool, str | None]:
        """Verifica se a ferramenta pode ser usada.

        Returns:
            Tuple de (allowed: bool, reason: str | None)
        """
        ...


class ToolCallable(Protocol):
    """Protocol para callable de ferramenta."""

    async def __call__(
        self,
        tool_input: dict[str, Any],
        context: Any,
    ) -> ToolResult:
        """Executa a ferramenta."""
        ...


@dataclass
class ToolDefinition:
    """Definição de uma ferramenta disponível.

    Attributes:
        name: Nome único da ferramenta
        callable: Função de execução
        is_concurrency_safe: Se pode rodar em paralelo
        description: Descrição da ferramenta
        is_read_only: Se não modifica estado (não aborta irmãos)
        interrupt_behavior: Como reagir a interrupções
        max_result_size_chars: Tamanho máximo do resultado
        timeout_seconds: Timeout de execução
    """

    name: str
    callable: ToolCallable
    is_concurrency_safe: bool = True
    description: str | None = None
    is_read_only: bool = False
    interrupt_behavior: str = "block"  # "cancel" ou "block"
    max_result_size_chars: int = 100_000
    timeout_seconds: float = 30.0


class ToolUseContext:
    """Contexto para uso de ferramentas."""

    def __init__(
        self,
        session_id: str,
        abort_controller: AbortController | None = None,
        cwd: str | None = None,
        permission_mode: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.session_id = session_id
        self.abort_controller = abort_controller or AbortController()
        self.cwd = cwd
        self.permission_mode = permission_mode
        self.metadata = metadata or {}


class StreamingToolExecutor:
    """Executa ferramentas conforme chegam no stream.

    Características:
    - Ferramentas concorrentes podem rodar em paralelo
    - Ferramentas não-concorrentes rodam sozinhas
    - Resultados são bufferados e emitidos em ordem de conclusão
    - Abort Controller cancela subprocessos em caso de erro

    Inspirado no StreamingToolExecutor do Claude Code.
    """

    def __init__(
        self,
        tool_definitions: dict[str, ToolDefinition],
        can_use_tool: CanUseToolFn,
        tool_use_context: ToolUseContext,
        max_concurrent: int = 5,
    ) -> None:
        self._tools: list[TrackedTool] = []
        self._tool_definitions = tool_definitions
        self._can_use_tool = can_use_tool
        self._tool_use_context = tool_use_context
        self._max_concurrent = max_concurrent

        # Abort Controller para subprocessos
        self._sibling_abort_controller = create_child_abort_controller(
            tool_use_context.abort_controller,
        )

        # Semáforo para controle de concorrência
        self._semaphore = asyncio.Semaphore(max_concurrent)

        # Estado interno
        self._has_errored = False
        self._discarded = False
        self._running_tasks: dict[str, asyncio.Task[None]] = {}
        self._result_queue: asyncio.Queue[StreamingToolResult] = asyncio.Queue()
        self._order_counter = 0

        # Integração com HookManager
        self._hook_manager = HookManager.get_instance()

        # Lock para operações thread-safe
        self._lock = asyncio.Lock()

    @property
    def tools(self) -> list[TrackedTool]:
        """Retorna lista de ferramentas rastreadas."""
        return self._tools

    @property
    def pending_tools(self) -> list[TrackedTool]:
        """Retorna ferramentas pendentes."""
        return [t for t in self._tools if t.is_pending]

    @property
    def running_tools(self) -> list[TrackedTool]:
        """Retorna ferramentas em execução."""
        return [t for t in self._tools if t.is_running]

    @property
    def completed_tools(self) -> list[TrackedTool]:
        """Retorna ferramentas completadas."""
        return [t for t in self._tools if t.status == ToolStatus.COMPLETED]

    @property
    def has_pending(self) -> bool:
        """Verifica se há ferramentas pendentes."""
        return any(t.is_pending for t in self._tools)

    @property
    def has_running(self) -> bool:
        """Verifica se há ferramentas em execução."""
        return any(t.is_running for t in self._tools)

    @property
    def is_complete(self) -> bool:
        """Verifica se todas as ferramentas terminaram."""
        return all(t.is_terminal for t in self._tools)

    def add_tool(
        self,
        tool_use_id: str,
        tool_name: str,
        tool_input: dict[str, Any],
        assistant_message: Any = None,
    ) -> TrackedTool:
        """Adiciona ferramenta à fila de execução.

        Se a ferramenta é concurrent-safe e não há erro,
        inicia execução imediatamente.

        Args:
            tool_use_id: ID único do uso da ferramenta
            tool_name: Nome da ferramenta
            tool_input: Input da ferramenta
            assistant_message: Mensagem do assistente

        Returns:
            TrackedTool criada
        """
        # Verifica se ferramenta existe
        if tool_name not in self._tool_definitions:
            _logger.warning(
                "unknown_tool_added",
                tool_name=tool_name,
                tool_use_id=tool_use_id,
            )

        tool_def = self._tool_definitions.get(tool_name)
        is_concurrency_safe = tool_def.is_concurrency_safe if tool_def else True

        tracked = TrackedTool(
            id=tool_use_id,
            tool_name=tool_name,
            tool_input=tool_input,
            assistant_message=assistant_message,
            is_concurrency_safe=is_concurrency_safe,
        )

        self._tools.append(tracked)

        # Se não há erro e é concurrent-safe, inicia execução
        if not self._has_errored and not self._discarded:
            if is_concurrency_safe:
                self._start_execution(tracked)
            elif not self.has_running:
                # Não-concurrent-safe só executa se não há outra rodando
                self._start_execution(tracked)

        return tracked

    def _start_execution(self, tool: TrackedTool) -> bool:
        """Inicia execução de uma ferramenta em background.

        Returns:
            True quando a task foi agendada no loop atual, False quando não há
            loop assíncrono ativo e a execução precisa ser diferida.
        """
        if tool.id in self._running_tasks:
            _logger.warning(
                "tool_already_running",
                tool_id=tool.id,
                tool_name=tool.tool_name,
            )
            return False

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            _logger.debug(
                "tool_execution_deferred_no_running_loop",
                tool_id=tool.id,
                tool_name=tool.tool_name,
            )
            return False

        tool.mark_running()
        task = loop.create_task(
            self._execute_tool_wrapper(tool),
            name=f"tool-{tool.id}",
        )
        self._running_tasks[tool.id] = task
        return True

    async def _schedule_pending_tools(self) -> None:
        """Agenda ferramentas pendentes quando já existe um loop em execução."""
        if self._has_errored or self._discarded:
            return

        async with self._lock:
            for tool in self._tools:
                if not tool.is_pending:
                    continue

                if tool.id in self._running_tasks:
                    continue

                if tool.is_concurrency_safe:
                    self._start_execution(tool)
                    continue

                if not self.has_running:
                    self._start_execution(tool)
                break

    async def _execute_tool_wrapper(self, tool: TrackedTool) -> None:
        """Wrapper para execução com cleanup."""
        try:
            await self._execute_tool(tool)
        except Exception as exc:
            _logger.error(
                "tool_execution_wrapper_error",
                tool_id=tool.id,
                tool_name=tool.tool_name,
                error=str(exc),
            )
            if not tool.is_terminal:
                tool.mark_error(str(exc))
                await self._emit_result(tool)
        finally:
            async with self._lock:
                self._running_tasks.pop(tool.id, None)
            # Tenta iniciar próxima ferramenta não-concurrent-safe
            await self._try_start_next_non_concurrent()

    async def _try_start_next_non_concurrent(self) -> None:
        """Tenta iniciar próxima ferramenta não-concurrent-safe."""
        if self._has_errored or self._discarded:
            return

        async with self._lock:
            if self.has_running:
                return

            for tool in self._tools:
                if tool.is_pending and not tool.is_concurrency_safe:
                    self._start_execution(tool)
                    break

    @staticmethod
    async def _collect_hook_results(
        generator: AsyncGenerator[Any, None],
    ) -> list[Any]:
        """Materializa async generators de hooks em uma lista."""
        return [item async for item in generator]

    def _append_hook_context(self, contexts: list[str]) -> None:
        """Acumula contexto adicional retornado por hooks."""
        merged = HookResultProcessor.merge_additional_contexts(
            [context for context in contexts if context],
        )
        if not merged:
            return

        existing = self._tool_use_context.metadata.get("hook_context")
        if existing:
            self._tool_use_context.metadata["hook_context"] = f"{existing}\n{merged}"
        else:
            self._tool_use_context.metadata["hook_context"] = merged

    @staticmethod
    def _apply_post_tool_output(
        original_result: Any,
        updated_output: Any,
    ) -> Any:
        """Aplica updated_mcp_tool_output preservando wrappers de ToolResult quando possível."""
        if updated_output is original_result:
            return original_result

        if isinstance(original_result, ToolResult):
            return original_result.model_copy(update={"data": updated_output})

        return updated_output

    async def _execute_tool(self, tool: TrackedTool) -> None:
        """Executa uma ferramenta com controle de concorrência.

        1. Verifica permissão via can_use_tool
        2. Executa hooks PreToolUse
        3. Executa ferramenta
        4. Executa hooks PostToolUse
        5. Retorna resultado
        """
        # Verifica abort
        self._sibling_abort_controller.check_or_raise()

        async with self._semaphore:
            await self._emit_result(tool)

            try:
                # 1. Hooks de solicitação de permissão
                permission_request_results = await self._collect_hook_results(
                    PermissionRequestHandler.execute(
                        tool_name=tool.tool_name,
                        tool_input=tool.tool_input,
                        tool_use_id=tool.id,
                        description=f"Tool '{tool.tool_name}' requested execution.",
                        session_id=self._tool_use_context.session_id,
                    )
                )
                blocked, block_reason = HookResultProcessor.should_block_execution(
                    permission_request_results,
                )
                if blocked:
                    tool.mark_error(
                        f"Permission blocked by hook: {block_reason or 'Permission denied'}",
                    )
                    await self._emit_result(tool)
                    return

                self._append_hook_context(
                    [
                        context
                        for context in (
                            result.add_context for result in permission_request_results
                        )
                        if context
                    ],
                )

                # 2. Verifica permissão real
                allowed, reason = await self._can_use_tool(
                    tool.tool_name,
                    tool.tool_input,
                )

                if not allowed:
                    await self._collect_hook_results(
                        PermissionDeniedHandler.execute(
                            tool_name=tool.tool_name,
                            tool_input=tool.tool_input,
                            tool_use_id=tool.id,
                            session_id=self._tool_use_context.session_id,
                        )
                    )
                    tool.mark_error(f"Permission denied: {reason}")
                    await self._emit_result(tool)
                    return

                # 3. Executa hooks PreToolUse
                pre_tool_results = await self._collect_hook_results(
                    self._hook_manager.execute_pre_tool(
                        tool_name=tool.tool_name,
                        tool_input=tool.tool_input,
                        tool_use_id=tool.id,
                        session_id=self._tool_use_context.session_id,
                        cwd=self._tool_use_context.cwd,
                        permission_mode=self._tool_use_context.permission_mode,
                    )
                )
                pre_processed = HookResultProcessor.process_pre_tool_results(
                    pre_tool_results,
                    tool.tool_input,
                )
                if not pre_processed["allowed"]:
                    tool.mark_error(
                        f"Blocked by hook: {pre_processed['reason'] or 'Denied'}",
                    )
                    await self._emit_result(tool)
                    return

                blocked, block_reason = HookResultProcessor.should_block_execution(
                    pre_tool_results,
                )
                if blocked:
                    tool.mark_error(f"Blocked by hook: {block_reason or 'Execution stopped'}")
                    await self._emit_result(tool)
                    return

                tool.tool_input = pre_processed["updated_input"]
                self._append_hook_context(pre_processed["additional_context"])

                # 4. Verifica abort novamente
                self._sibling_abort_controller.check_or_raise()

                # 5. Executa ferramenta
                tool_def = self._tool_definitions.get(tool.tool_name)
                if tool_def is None:
                    tool.mark_error(f"Tool not found: {tool.tool_name}")
                    await self._emit_result(tool)
                    return

                result = await tool_def.callable(
                    tool.tool_input,
                    self._tool_use_context,
                )

                # 6. Executa hooks PostToolUse
                post_tool_results = await self._collect_hook_results(
                    self._hook_manager.execute_post_tool(
                        tool_name=tool.tool_name,
                        tool_input=tool.tool_input,
                        tool_use_id=tool.id,
                        tool_response=result,
                        session_id=self._tool_use_context.session_id,
                        cwd=self._tool_use_context.cwd,
                        permission_mode=self._tool_use_context.permission_mode,
                    )
                )
                post_processed = HookResultProcessor.process_post_tool_results(
                    post_tool_results,
                    result,
                )
                self._append_hook_context(post_processed["additional_context"])
                result = self._apply_post_tool_output(
                    result,
                    post_processed["updated_output"],
                )

                tool.mark_completed(result)
                await self._emit_result(tool)

            except ToolExecutionAbortedError as exc:
                tool.mark_error(f"Aborted: {exc.reason}")
                await self._emit_result(tool)
                self._abort_siblings(f"Tool {tool.tool_name} aborted: {exc.reason}")

            except Exception as exc:
                # Classifica erro usando novo sistema
                error_category = classify_error(exc)

                _logger.error(
                    "tool_execution_error",
                    tool_id=tool.id,
                    tool_name=tool.tool_name,
                    error=str(exc),
                    error_category=error_category.value,
                    is_retryable=is_retryable(exc),
                )

                # Executa hooks PostToolFailure
                post_failure_results = await self._collect_hook_results(
                    self._hook_manager.execute_post_tool_failure(
                        tool_name=tool.tool_name,
                        tool_input=tool.tool_input,
                        tool_use_id=tool.id,
                        error=str(exc),
                        session_id=self._tool_use_context.session_id,
                        cwd=self._tool_use_context.cwd,
                    )
                )
                self._append_hook_context(
                    [
                        context
                        for context in (
                            result.add_context for result in post_failure_results
                        )
                        if context
                    ],
                )

                tool.mark_error(str(exc))
                await self._emit_result(tool)

    async def _emit_result(self, tool: TrackedTool) -> None:
        """Emite resultado para a fila."""
        self._order_counter += 1
        result = StreamingToolResult(
            tool_id=tool.id,
            tool_name=tool.tool_name,
            status=tool.status,
            result=tool.result,
            error=tool.error,
            execution_time_ms=tool.execution_time_ms,
            order=self._order_counter,
        )
        await self._result_queue.put(result)

    def _abort_siblings(self, reason: str) -> None:
        """Aborta ferramentas irmãs."""
        self._has_errored = True
        self._sibling_abort_controller.abort(reason)

        # Cancela tasks em andamento
        for task in self._running_tasks.values():
            if not task.done():
                task.cancel()

    async def get_remaining_results(self) -> AsyncGenerator[StreamingToolResult, None]:
        """Retorna resultados restantes conforme ficam prontos.

        Yields:
            StreamingToolResult na ordem de conclusão
        """
        await self._schedule_pending_tools()

        while not self.is_complete or not self._result_queue.empty():
            try:
                # Aguarda resultado com timeout para verificar se completo
                result = await asyncio.wait_for(
                    self._result_queue.get(),
                    timeout=0.1,
                )
                yield result
            except asyncio.TimeoutError:
                if self.is_complete and self._result_queue.empty():
                    break
                continue

    def discard(self) -> None:
        """Descarta todas as ferramentas pendentes.

        Cancela tasks em andamento e marca ferramentas como discarded.
        """
        self._discarded = True
        self._sibling_abort_controller.abort("Discarded")

        # Marca pendentes como discarded
        for tool in self._tools:
            if tool.is_pending:
                tool.mark_discarded()

        # Cancela tasks
        for task in self._running_tasks.values():
            if not task.done():
                task.cancel()

    async def wait_all(self) -> list[StreamingToolResult]:
        """Aguarda todas as ferramentas completarem e retorna resultados.

        Returns:
            Lista de StreamingToolResult em ordem de conclusão
        """
        while True:
            await self._schedule_pending_tools()

            running_tasks = list(self._running_tasks.values())
            if running_tasks:
                await asyncio.gather(*running_tasks, return_exceptions=True)
                continue

            if self.has_pending and not self._discarded and not self._has_errored:
                await asyncio.sleep(0)
                continue

            break

        results: list[StreamingToolResult] = []
        while not self._result_queue.empty():
            results.append(self._result_queue.get_nowait())

        results.sort(key=lambda result: result.order)
        return results

    async def execute_batch(
        self,
        tool_calls: list[dict[str, Any]],
    ) -> list[StreamingToolResult]:
        """Execute a batch of tool calls using Claude-style partition.

        This method is for post-API execution (when tool calls are received
        all at once after the LLM response). It partitions tools into
        concurrent-safe and serial batches, then executes them.

        Args:
            tool_calls: List of tool call dictionaries with 'name', 'args', 'id'

        Returns:
            List of StreamingToolResult in original tool-call order

        Example:
            >>> executor = StreamingToolExecutor(...)
            >>> tool_calls = [
            ...     {"name": "file_read", "args": {"path": "a.txt"}, "id": "1"},
            ...     ]
            >>> results = await executor.execute_batch(tool_calls)
        """
        if not tool_calls:
            return []

        # Partition tool calls into concurrent-safe and serial batches
        batches = partition_tool_calls(tool_calls, self._tool_definitions)

        all_results: list[StreamingToolResult] = []

        for batch in batches:
            if batch.is_concurrent_safe:
                # Execute concurrent-safe tools in parallel
                batch_results = await self._execute_concurrent_batch(batch.blocks)
            else:
                # Execute non-concurrent tools serially
                batch_results = await self._execute_serial_batch(batch.blocks)

            all_results.extend(batch_results)

        # Sort by original order (tool_call_id)
        all_results.sort(key=lambda r: r.tool_id)
        return all_results

    async def _execute_concurrent_batch(
        self,
        tool_calls: list[dict[str, Any]],
    ) -> list[StreamingToolResult]:
        """Execute a batch of concurrent-safe tools in parallel.

        Args:
            tool_calls: List of tool call dictionaries

        Returns:
            List of StreamingToolResult
        """
        semaphore = asyncio.Semaphore(self._max_concurrent)

        async def _run_single(tool_call: dict[str, Any]) -> StreamingToolResult:
            async with semaphore:
                return await self._execute_single_tool(tool_call)

        tasks = [asyncio.create_task(_run_single(tc)) for tc in tool_calls]
        return await asyncio.gather(*tasks)

    async def _execute_serial_batch(
        self,
        tool_calls: list[dict[str, Any]],
    ) -> list[StreamingToolResult]:
        """Execute a batch of tools serially.

        Args:
            tool_calls: List of tool call dictionaries

        Returns:
            List of StreamingToolResult
        """
        results = []
        for tool_call in tool_calls:
            result = await self._execute_single_tool(tool_call)
            results.append(result)
        return results

    async def _execute_single_tool(
        self,
        tool_call: dict[str, Any],
    ) -> StreamingToolResult:
        """Execute a single tool call.

        This is a simplified version of the full streaming execution path,
        used for batch execution where we don't need streaming progress.

        Args:
            tool_call: Tool call dictionary with 'name', 'args', 'id'

        Returns:
            StreamingToolResult with execution result
        """
        tool_name = tool_call.get("name", "")
        tool_args = tool_call.get("args", {})
        tool_use_id = tool_call.get("id", "") or str(uuid.uuid4())

        tool_def = self._tool_definitions.get(tool_name)

        if tool_def is None:
            return StreamingToolResult(
                tool_id=tool_use_id,
                tool_name=tool_name,
                status=ToolStatus.ERROR,
                result=None,
                error=f"Unknown tool: {tool_name}",
                execution_time_ms=0,
                order=0,
            )

        start_time = time.time()

        try:
            # Execute the tool
            result = await tool_def.callable(tool_args, self._tool_use_context)

            execution_time_ms = (time.time() - start_time) * 1000

            return StreamingToolResult(
                tool_id=tool_use_id,
                tool_name=tool_name,
                status=ToolStatus.COMPLETED if result.success else ToolStatus.ERROR,
                result=result,
                error=result.error if not result.success else None,
                execution_time_ms=execution_time_ms,
                order=0,
            )
        except Exception as exc:
            execution_time_ms = (time.time() - start_time) * 1000
            _logger.error(
                "batch_tool_execution_error",
                tool_name=tool_name,
                error=str(exc),
            )
            return StreamingToolResult(
                tool_id=tool_use_id,
                tool_name=tool_name,
                status=ToolStatus.ERROR,
                result=None,
                error=str(exc),
                execution_time_ms=execution_time_ms,
                order=0,
            )

    def get_stats(self) -> dict[str, Any]:
        """Retorna estatísticas do executor."""
        return {
            "total": len(self._tools),
            "pending": len(self.pending_tools),
            "running": len(self.running_tools),
            "completed": len(self.completed_tools),
            "errored": len([t for t in self._tools if t.status == ToolStatus.ERROR]),
            "discarded": len([t for t in self._tools if t.status == ToolStatus.DISCARDED]),
            "has_errored": self._has_errored,
            "discarded_executor": self._discarded,
            "is_complete": self.is_complete,
        }
