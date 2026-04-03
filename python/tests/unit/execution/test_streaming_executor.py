"""Testes unitários para StreamingToolExecutor."""

import asyncio
import sys
import types
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mindflow_backend.hooks.result import HookResult
from mindflow_backend.hooks.types import HookEvent, HookPermissionBehavior

if "redis" not in sys.modules:
    redis_module = types.ModuleType("redis")
    redis_asyncio_module = types.ModuleType("redis.asyncio")
    redis_module.asyncio = redis_asyncio_module
    sys.modules["redis"] = redis_module
    sys.modules["redis.asyncio"] = redis_asyncio_module

from mindflow_backend.runtime.execution.streaming_executor import (
    StreamingToolExecutor,
    ToolDefinition,
    ToolUseContext,
    CanUseToolFn,
)
from mindflow_backend.schemas.tools.streaming_types import (
    AbortController,
    ToolStatus,
    TrackedTool,
    StreamingToolResult,
)
from mindflow_backend.schemas.tools.result import ToolResult


async def _empty_async_gen():
    if False:
        yield None


@pytest.fixture
def abort_controller():
    """Fixture para AbortController."""
    return AbortController()


@pytest.fixture
def tool_context(abort_controller):
    """Fixture para ToolUseContext."""
    return ToolUseContext(
        session_id="test-session-123",
        abort_controller=abort_controller,
    )


@pytest.fixture
def mock_can_use_tool():
    """Fixture para função de permissão."""
    async def can_use(tool_name: str, tool_input: dict) -> tuple[bool, str | None]:
        return True, None
    return can_use


@pytest.fixture
def mock_tool_callable():
    """Fixture para callable de ferramenta."""
    async def tool_fn(tool_input: dict, context: Any) -> ToolResult:
        return ToolResult(
            success=True,
            result={"output": "test result"},
            tool_name=tool_input.get("tool_name", "test_tool"),
        )
    return tool_fn


@pytest.fixture
def tool_definitions(mock_tool_callable):
    """Fixture para definições de ferramentas."""
    return {
        "test_tool": ToolDefinition(
            name="test_tool",
            callable=mock_tool_callable,
            is_concurrency_safe=True,
        ),
        "unsafe_tool": ToolDefinition(
            name="unsafe_tool",
            callable=mock_tool_callable,
            is_concurrency_safe=False,
        ),
    }


class TestTrackedTool:
    """Testes para TrackedTool."""

    def test_initial_status(self):
        """Testa status inicial."""
        tool = TrackedTool(
            id="test-id",
            tool_name="test_tool",
            tool_input={"key": "value"},
        )
        assert tool.status == ToolStatus.PENDING
        assert tool.is_pending
        assert not tool.is_running
        assert not tool.is_terminal

    def test_mark_running(self):
        """Testa marcação como running."""
        tool = TrackedTool(
            id="test-id",
            tool_name="test_tool",
            tool_input={},
        )
        tool.mark_running()
        assert tool.status == ToolStatus.RUNNING
        assert tool.is_running
        assert tool.started_at is not None

    def test_mark_completed(self):
        """Testa marcação como completed."""
        tool = TrackedTool(
            id="test-id",
            tool_name="test_tool",
            tool_input={},
        )
        result = ToolResult(success=True, result="ok", tool_name="test_tool")
        tool.mark_completed(result)
        assert tool.status == ToolStatus.COMPLETED
        assert tool.is_terminal
        assert tool.result == result
        assert tool.completed_at is not None

    def test_mark_error(self):
        """Testa marcação como error."""
        tool = TrackedTool(
            id="test-id",
            tool_name="test_tool",
            tool_input={},
        )
        tool.mark_error("Test error")
        assert tool.status == ToolStatus.ERROR
        assert tool.is_terminal
        assert tool.error == "Test error"

    def test_mark_discarded(self):
        """Testa marcação como discarded."""
        tool = TrackedTool(
            id="test-id",
            tool_name="test_tool",
            tool_input={},
        )
        tool.mark_discarded()
        assert tool.status == ToolStatus.DISCARDED
        assert tool.is_terminal

    def test_execution_time_ms(self):
        """Testa cálculo de tempo de execução."""
        import time
        tool = TrackedTool(
            id="test-id",
            tool_name="test_tool",
            tool_input={},
        )
        tool.mark_running()
        time.sleep(0.01)  # 10ms
        tool.mark_error("done")
        assert tool.execution_time_ms >= 10


class TestAbortController:
    """Testes para AbortController."""

    def test_initial_state(self):
        """Testa estado inicial."""
        controller = AbortController()
        assert not controller.is_aborted
        assert controller.reason is None

    def test_abort(self):
        """Testa abort."""
        controller = AbortController()
        controller.abort("Test reason")
        assert controller.is_aborted
        assert controller.reason == "Test reason"

    def test_child_aborts_with_parent(self):
        """Testa que filho aborta com pai."""
        parent = AbortController()
        child = parent.create_child()
        parent.abort("Parent aborted")
        assert child.is_aborted
        assert child.reason == "Parent aborted"

    def test_check_or_raise_when_aborted(self):
        """Testa check_or_raise quando abortado."""
        from mindflow_backend.schemas.tools.streaming_types import ToolExecutionAbortedError
        controller = AbortController()
        controller.abort("Aborted")
        with pytest.raises(ToolExecutionAbortedError):
            controller.check_or_raise()

    def test_check_or_raise_when_not_aborted(self):
        """Testa check_or_raise quando não abortado."""
        controller = AbortController()
        controller.check_or_raise()  # Não deve levantar exceção


class TestStreamingToolExecutor:
    """Testes para StreamingToolExecutor."""

    def test_add_tool(self, tool_definitions, mock_can_use_tool, tool_context):
        """Testa adição de ferramenta."""
        executor = StreamingToolExecutor(
            tool_definitions=tool_definitions,
            can_use_tool=mock_can_use_tool,
            tool_use_context=tool_context,
        )

        tool = executor.add_tool(
            tool_use_id="tool-1",
            tool_name="test_tool",
            tool_input={"key": "value"},
        )

        assert tool.id == "tool-1"
        assert tool.tool_name == "test_tool"
        assert len(executor.tools) == 1

    @pytest.mark.asyncio
    async def test_add_concurrent_safe_tool_starts_immediately(
        self, tool_definitions, mock_can_use_tool, tool_context
    ):
        """Testa que ferramenta concurrent-safe inicia imediatamente."""
        executor = StreamingToolExecutor(
            tool_definitions=tool_definitions,
            can_use_tool=mock_can_use_tool,
            tool_use_context=tool_context,
            max_concurrent=5,
        )

        tool = executor.add_tool(
            tool_use_id="tool-1",
            tool_name="test_tool",
            tool_input={},
        )

        # Ferramenta concurrent-safe deve iniciar
        assert tool.is_concurrency_safe
        # Verifica que task foi criado
        assert "tool-1" in executor._running_tasks
        pending_tasks = list(executor._running_tasks.values())
        executor.discard()
        if pending_tasks:
            await asyncio.gather(*pending_tasks, return_exceptions=True)

    @pytest.mark.asyncio
    async def test_execute_tool_success(
        self, tool_definitions, mock_can_use_tool, tool_context
    ):
        """Testa execução bem-sucedida de ferramenta."""
        executor = StreamingToolExecutor(
            tool_definitions=tool_definitions,
            can_use_tool=mock_can_use_tool,
            tool_use_context=tool_context,
        )

        tool = executor.add_tool(
            tool_use_id="tool-1",
            tool_name="test_tool",
            tool_input={},
        )

        # Aguarda execução
        results = await executor.wait_all()

        assert len(results) == 2  # running + completed
        assert results[-1].status == ToolStatus.COMPLETED
        assert tool.status == ToolStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_tool_error(
        self, mock_can_use_tool, tool_context
    ):
        """Testa execução com erro."""
        async def failing_tool(tool_input: dict, context: Any) -> ToolResult:
            raise ValueError("Tool failed")

        tool_definitions = {
            "failing_tool": ToolDefinition(
                name="failing_tool",
                callable=failing_tool,
                is_concurrency_safe=True,
            ),
        }

        executor = StreamingToolExecutor(
            tool_definitions=tool_definitions,
            can_use_tool=mock_can_use_tool,
            tool_use_context=tool_context,
        )

        tool = executor.add_tool(
            tool_use_id="tool-1",
            tool_name="failing_tool",
            tool_input={},
        )

        results = await executor.wait_all()

        # Deve ter running + error
        assert results[-1].status == ToolStatus.ERROR
        assert tool.status == ToolStatus.ERROR

    @pytest.mark.asyncio
    async def test_permission_denied(
        self, tool_definitions, tool_context
    ):
        """Testa execução com permissão negada."""
        async def deny_all(tool_name: str, tool_input: dict) -> tuple[bool, str | None]:
            return False, "Not allowed"

        executor = StreamingToolExecutor(
            tool_definitions=tool_definitions,
            can_use_tool=deny_all,
            tool_use_context=tool_context,
        )

        tool = executor.add_tool(
            tool_use_id="tool-1",
            tool_name="test_tool",
            tool_input={},
        )

        results = await executor.wait_all()

        assert results[-1].status == ToolStatus.ERROR
        assert "Permission denied" in tool.error

    @pytest.mark.asyncio
    async def test_permission_request_hook_can_block_before_permission_check(
        self,
        tool_context,
        monkeypatch,
    ):
        """PermissionRequest hooks devem bloquear antes do check real de permissão."""
        called = False

        async def can_use(tool_name: str, tool_input: dict) -> tuple[bool, str | None]:
            nonlocal called
            called = True
            return True, None

        async def tool_fn(tool_input: dict, context: Any) -> dict:
            return {"ok": True}

        async def permission_request_hook(*args, **kwargs):
            yield HookResult(
                event=HookEvent.PERMISSION_REQUEST,
                command="permission-hook",
                status="blocked",
                behavior=HookPermissionBehavior.DENY,
                reason="blocked by permission hook",
            )

        monkeypatch.setattr(
            "mindflow_backend.runtime.execution.streaming_executor.PermissionRequestHandler.execute",
            permission_request_hook,
        )

        executor = StreamingToolExecutor(
            tool_definitions={
                "test_tool": ToolDefinition(
                    name="test_tool",
                    callable=tool_fn,
                    is_concurrency_safe=True,
                ),
            },
            can_use_tool=can_use,
            tool_use_context=tool_context,
        )

        tool = executor.add_tool(
            tool_use_id="tool-1",
            tool_name="test_tool",
            tool_input={},
        )

        await executor.wait_all()

        assert called is False
        assert tool.status == ToolStatus.ERROR
        assert "Permission blocked by hook" in (tool.error or "")

    @pytest.mark.asyncio
    async def test_pre_tool_hooks_use_processor_for_input_and_context(
        self,
        tool_context,
        mock_can_use_tool,
        monkeypatch,
    ):
        """PreToolUse deve usar HookResultProcessor para mutação de input e contexto."""

        async def tool_fn(tool_input: dict, context: Any) -> dict:
            return {"received": tool_input["path"]}

        async def pre_tool_hook(*args, **kwargs):
            yield HookResult(
                event=HookEvent.PRE_TOOL_USE,
                command="pre-hook",
                status="success",
                updated_input={"path": "/tmp/updated.txt"},
                add_context="hook context",
            )

        monkeypatch.setattr(
            "mindflow_backend.runtime.execution.streaming_executor.PermissionRequestHandler.execute",
            lambda *args, **kwargs: _empty_async_gen(),
        )
        executor = StreamingToolExecutor(
            tool_definitions={
                "test_tool": ToolDefinition(
                    name="test_tool",
                    callable=tool_fn,
                    is_concurrency_safe=True,
                ),
            },
            can_use_tool=mock_can_use_tool,
            tool_use_context=tool_context,
        )
        monkeypatch.setattr(executor._hook_manager, "execute_pre_tool", pre_tool_hook)

        tool = executor.add_tool(
            tool_use_id="tool-1",
            tool_name="test_tool",
            tool_input={"path": "/tmp/original.txt"},
        )

        await executor.wait_all()

        assert tool.status == ToolStatus.COMPLETED
        assert tool.result == {"received": "/tmp/updated.txt"}
        assert executor._tool_use_context.metadata["hook_context"] == "hook context"

    @pytest.mark.asyncio
    async def test_post_tool_hooks_update_tool_result_data(
        self,
        tool_context,
        mock_can_use_tool,
        monkeypatch,
    ):
        """PostToolUse deve aplicar updated_mcp_tool_output sem acessar atributos inexistentes."""

        async def tool_fn(tool_input: dict, context: Any) -> ToolResult:
            return ToolResult(data={"formatted": False})

        async def post_tool_hook(*args, **kwargs):
            yield HookResult(
                event=HookEvent.POST_TOOL_USE,
                command="post-hook",
                status="success",
                updated_mcp_tool_output={"formatted": True},
                add_context="post hook context",
            )

        monkeypatch.setattr(
            "mindflow_backend.runtime.execution.streaming_executor.PermissionRequestHandler.execute",
            lambda *args, **kwargs: _empty_async_gen(),
        )
        executor = StreamingToolExecutor(
            tool_definitions={
                "test_tool": ToolDefinition(
                    name="test_tool",
                    callable=tool_fn,
                    is_concurrency_safe=True,
                ),
            },
            can_use_tool=mock_can_use_tool,
            tool_use_context=tool_context,
        )
        monkeypatch.setattr(executor._hook_manager, "execute_post_tool", post_tool_hook)

        tool = executor.add_tool(
            tool_use_id="tool-1",
            tool_name="test_tool",
            tool_input={},
        )

        await executor.wait_all()

        assert tool.status == ToolStatus.COMPLETED
        assert isinstance(tool.result, ToolResult)
        assert tool.result.data == {"formatted": True}
        assert "post hook context" in executor._tool_use_context.metadata["hook_context"]

    @pytest.mark.asyncio
    async def test_discard(self, tool_definitions, mock_can_use_tool, tool_context):
        """Testa discard de ferramentas."""
        executor = StreamingToolExecutor(
            tool_definitions=tool_definitions,
            can_use_tool=mock_can_use_tool,
            tool_use_context=tool_context,
        )

        executor.add_tool(
            tool_use_id="tool-1",
            tool_name="test_tool",
            tool_input={},
        )
        executor.add_tool(
            tool_use_id="tool-2",
            tool_name="test_tool",
            tool_input={},
        )

        executor.discard()

        # Ferramentas pendentes devem ser discarded
        pending = executor.pending_tools
        assert len(pending) == 0

    @pytest.mark.asyncio
    async def test_concurrent_execution(
        self, mock_can_use_tool, tool_context
    ):
        """Testa execução concorrente."""
        import time

        execution_times = []

        async def slow_tool(tool_input: dict, context: Any) -> ToolResult:
            start = time.time()
            await asyncio.sleep(0.1)
            execution_times.append(time.time() - start)
            return ToolResult(
                success=True,
                result="done",
                tool_name="slow_tool",
            )

        tool_definitions = {
            "slow_tool": ToolDefinition(
                name="slow_tool",
                callable=slow_tool,
                is_concurrency_safe=True,
            ),
        }

        executor = StreamingToolExecutor(
            tool_definitions=tool_definitions,
            can_use_tool=mock_can_use_tool,
            tool_use_context=tool_context,
            max_concurrent=5,
        )

        # Adiciona 3 ferramentas
        for i in range(3):
            executor.add_tool(
                tool_use_id=f"tool-{i}",
                tool_name="slow_tool",
                tool_input={},
            )

        start_time = time.time()
        await executor.wait_all()
        total_time = time.time() - start_time

        # Execução paralela deve ser mais rápida que sequencial
        assert total_time < 0.3  # 3 * 0.1 = 0.3s se sequencial
        assert len(execution_times) == 3

    def test_get_stats(self, tool_definitions, mock_can_use_tool, tool_context):
        """Testa obtenção de estatísticas."""
        executor = StreamingToolExecutor(
            tool_definitions=tool_definitions,
            can_use_tool=mock_can_use_tool,
            tool_use_context=tool_context,
        )

        executor.add_tool(
            tool_use_id="tool-1",
            tool_name="test_tool",
            tool_input={},
        )

        stats = executor.get_stats()

        assert stats["total"] == 1
        assert stats["pending"] + stats["running"] >= 0
        assert "is_complete" in stats

    @pytest.mark.asyncio
    async def test_abort_on_error(self, mock_can_use_tool, tool_context):
        """Testa abort de irmãos em caso de erro."""
        call_count = 0

        async def counting_tool(tool_input: dict, context: Any) -> ToolResult:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("First tool fails")
            await asyncio.sleep(0.5)  # Ferramenta lenta
            return ToolResult(
                success=True,
                result="done",
                tool_name="counting_tool",
            )

        tool_definitions = {
            "counting_tool": ToolDefinition(
                name="counting_tool",
                callable=counting_tool,
                is_concurrency_safe=True,
            ),
        }

        executor = StreamingToolExecutor(
            tool_definitions=tool_definitions,
            can_use_tool=mock_can_use_tool,
            tool_use_context=tool_context,
            max_concurrent=5,
        )

        # Adiciona 2 ferramentas
        executor.add_tool(
            tool_use_id="tool-1",
            tool_name="counting_tool",
            tool_input={},
        )
        executor.add_tool(
            tool_use_id="tool-2",
            tool_name="counting_tool",
            tool_input={},
        )

        results = await executor.wait_all()

        # Deve ter erro e discarded
        statuses = [r.status for r in results]
        assert ToolStatus.ERROR in statuses


class TestStreamingToolResult:
    """Testes para StreamingToolResult."""

    def test_to_dict(self):
        """Testa conversão para dict."""
        result = StreamingToolResult(
            tool_id="tool-1",
            tool_name="test_tool",
            status=ToolStatus.COMPLETED,
            order=1,
        )

        data = result.to_dict()

        assert data["tool_id"] == "tool-1"
        assert data["tool_name"] == "test_tool"
        assert data["status"] == "completed"
        assert data["order"] == 1
