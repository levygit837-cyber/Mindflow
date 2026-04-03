"""HookManager — Core hook execution engine.

Singleton que registra e executa hooks para todos os eventos.
Equivalente de src/utils/hooks.ts do Claude Code.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any, Callable

import uuid

from mindflow_backend.hooks.context import HookContext
from mindflow_backend.hooks.event_broadcaster import (
    HookEventBroadcaster,
    HookExecutionEvent,
    HookExecutionState,
)
from mindflow_backend.hooks.matcher import HookMatcher
from mindflow_backend.hooks.registry import HookRegistry
from mindflow_backend.hooks.result import AggregatedHookResult, HookCommand, HookMatcher as HookMatcherData, HookResult
from mindflow_backend.hooks.timeout import TimeoutConfig, DEFAULT_HOOK_TIMEOUT
from mindflow_backend.hooks.types import HookEvent, HookPermissionBehavior
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


@dataclass(frozen=True)
class FunctionHook:
    """Function hook — callable registrado programaticamente.

    Equivalente de FunctionHookMatcher em src/utils/hooks.ts.
    """
    event: HookEvent
    matcher: str | None
    callback: Callable[..., Any]
    timeout: float = DEFAULT_HOOK_TIMEOUT

    def to_command(self) -> HookCommand:
        """Converte para HookCommand para registro consistente."""
        return HookCommand(type="function", command=None, timeout=int(self.timeout))


class HookManager:
    """Singleton que gerencia registro e execução de hooks.

    Padrão adaptado de Claude Code:
    - getHooksConfig() → registry.get_hooks_for_event()
    - getMatchingHooks() → _get_matching_hooks()
    - executeHooks() → execute() (async generator)
    - executePreToolHooks() → execute_pre_tool()
    - executePostToolHooks() → execute_post_tool()
    - executeStopHooks() → execute_stop()
    """

    _instance: HookManager | None = None

    def __init__(self) -> None:
        self._registry = HookRegistry()

    @classmethod
    def get_instance(cls) -> HookManager:
        """Retorna instância singleton."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def registry(self) -> HookRegistry:
        """Acesso ao registro de hooks."""
        return self._registry

    # ─── Métodos de Conveniência para Registro ──────────────────────

    def register_command(
        self,
        event: HookEvent,
        matcher: str | None,
        command: str,
        *,
        timeout: int | None = None,
        source: str = "config",
    ) -> None:
        """Registra hook de comando para um evento."""
        hook_cmd = HookCommand(type="command", command=command, timeout=timeout)
        self._registry.register_config_hook(event, matcher, hook_cmd)

    def register_function(
        self,
        event: HookEvent,
        matcher: str | None,
        callback: Callable[..., Any],
    ) -> None:
        """Registra hook de função para um evento."""
        self._registry.register_function_hook(event, matcher, callback)

    def register_plugin_commands(
        self,
        plugin_name: str,
        hooks_config: dict[str, list[dict[str, Any]]],
        *,
        session_id: str | None = None,
    ) -> None:
        """Registra hooks de plugin a partir da configuração.

        Formato de hooks_config:
        {
            "PreToolUse": [{"matcher": "read_file", "command": "..."}],
            "PostToolUse": [{"matcher": None, "command": "..."}],
            ...
        }
        """
        for event_str, hook_list in hooks_config.items():
            try:
                event = HookEvent(event_str)
            except ValueError:
                _logger.warning(
                    "unknown_hook_event_in_plugin_config",
                    plugin=plugin_name,
                    event=event_str,
                )
                continue

            for hook_dict in hook_list:
                matcher = hook_dict.get("matcher")
                raw_hooks = hook_dict.get("hooks")
                hook_items = raw_hooks if isinstance(raw_hooks, list) else [hook_dict]
                for hook_item in hook_items:
                    cmd = HookCommand(
                        type=hook_item.get("type", "command"),
                        command=hook_item.get("command"),
                        timeout=hook_item.get("timeout"),
                    )
                    self._registry.register_plugin_hook(
                        plugin_name,
                        event,
                        matcher,
                        cmd,
                        session_id=session_id,
                    )

    def unregister_plugin_commands(
        self,
        plugin_name: str,
        *,
        session_id: str | None = None,
    ) -> None:
        """Remove hooks de plugin."""
        self._registry.unregister_plugin_hooks(plugin_name, session_id=session_id)

    def register_skill_commands(
        self,
        skill_id: str,
        hooks_config: dict[str, list[dict[str, Any]]],
        *,
        session_id: str | None = None,
    ) -> None:
        """Registra hooks de skill."""
        for event_str, hook_list in hooks_config.items():
            try:
                event = HookEvent(event_str)
            except ValueError:
                _logger.warning(
                    "unknown_hook_event_in_skill_config",
                    skill_id=skill_id,
                    event=event_str,
                )
                continue

            for hook_dict in hook_list:
                matcher = hook_dict.get("matcher")
                raw_hooks = hook_dict.get("hooks")
                hook_items = raw_hooks if isinstance(raw_hooks, list) else [hook_dict]
                for hook_item in hook_items:
                    cmd = HookCommand(
                        type=hook_item.get("type", "command"),
                        command=hook_item.get("command"),
                        timeout=hook_item.get("timeout"),
                    )
                    self._registry.register_skill_hook(
                        skill_id,
                        event,
                        matcher,
                        cmd,
                        session_id=session_id,
                    )

    def unregister_skill_commands(
        self,
        skill_id: str,
        *,
        session_id: str | None = None,
    ) -> None:
        """Remove hooks de skill."""
        self._registry.unregister_skill_hooks(skill_id, session_id=session_id)

    def register_agent_commands(
        self,
        agent_id: str,
        hooks_config: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Registra hooks de agent (frontmatter hooks)."""
        for event_str, hook_list in hooks_config.items():
            try:
                event = HookEvent(event_str)
            except ValueError:
                _logger.warning(
                    "unknown_hook_event_in_agent_config",
                    agent=agent_id,
                    event=event_str,
                )
                continue

            for hook_dict in hook_list:
                matcher = hook_dict.get("matcher")
                raw_hooks = hook_dict.get("hooks")
                hook_items = raw_hooks if isinstance(raw_hooks, list) else [hook_dict]
                for hook_item in hook_items:
                    cmd = HookCommand(
                        type=hook_item.get("type", "command"),
                        command=hook_item.get("command"),
                        timeout=hook_item.get("timeout"),
                    )
                    self._registry.register_agent_hook(agent_id, event, matcher, cmd)

    # ─── Métodos de Execução ───────────────────────────────────────

    async def execute(
        self,
        event: HookEvent,
        context: HookContext,
        *,
        match_query: str | None = None,
        timeout: float = DEFAULT_HOOK_TIMEOUT,
        session_id: str | None = None,
        agent_id: str | None = None,
    ) -> AsyncGenerator[HookResult, None]:
        """Executa hooks para um evento — async generator.

        Equivalente de executeHooks() em src/utils/hooks.ts.
        O caller decide como processar cada resultado:
        - behavior='block': impedir execução da tool
        - behavior='allow': prosseguir com input atualizado
        - add_context: adicionar ao prompt do modelo

        Args:
            event: Evento de hook (PreToolUse, PostToolUse, etc.)
            context: Contexto do hook com dados do evento
            match_query: Query para filtrar hooks (ex: "Write", "Bash")
            timeout: Timeout padrão em segundos
            session_id: ID da sessão
            agent_id: ID do agente

        Usage:
            async for hook_result in manager.execute(HookEvent.PRE_TOOL_USE, ctx):
                if hook_result.behavior == "deny":
                    # Impedir execução
                    pass
        """
        # 1. Buscar hook matchers para o evento (já filtrados por match_query no registry)
        matchers = self._registry.get_hooks_for_event(
            event,
            session_id=session_id,
            agent_id=agent_id,
            match_query=match_query,
        )

        # 2. Executar cada hook command
        for matcher_data in matchers:
            for hook_cmd in matcher_data.hooks:
                try:
                    if hook_cmd.type == "command":
                        result = await self._execute_command(
                            hook_cmd, context, hook_cmd.timeout or timeout
                        )
                    elif hook_cmd.type == "function":
                        # Function hooks são executados separadamente
                        continue
                    else:
                        result = HookResult(
                            event=event,
                            command=hook_cmd.command or "",
                            status="error",
                            error=f"Unknown hook type: {hook_cmd.type}",
                        )
                    yield result
                except asyncio.TimeoutError:
                    yield HookResult(
                        event=event,
                        command=hook_cmd.command or "",
                        status="timeout",
                        error=f"Hook timed out after {hook_cmd.timeout or timeout}s",
                    )
                except Exception as exc:
                    _logger.error(
                        "hook_execution_error",
                        event=str(event),
                        command=hook_cmd.command,
                        error=str(exc),
                    )
                    yield HookResult(
                        event=event,
                        command=hook_cmd.command or "",
                        status="error",
                        error=str(exc),
                    )

        # 3. Executar function hooks (com pattern matching)
        for matcher_str, callback in self._registry.get_function_hooks(event):
            # Usar HookMatcher.matches() para verificar se o callback deve ser executado
            if match_query and not HookMatcher.matches(match_query, matcher_str):
                continue
            try:
                result = await self._execute_function(callback, context, timeout)
                yield result
            except Exception as exc:
                _logger.error(
                    "function_hook_execution_error",
                    event=str(event),
                    error=str(exc),
                )
                yield HookResult(
                    event=event,
                    command="<function>",
                    status="error",
                    error=str(exc),
                )

    # ─── Métodos de Conveniência para Eventos Específicos ──────────

    async def execute_pre_tool(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_use_id: str,
        session_id: str,
        *,
        cwd: str | None = None,
        permission_mode: str | None = None,
        timeout: float = DEFAULT_HOOK_TIMEOUT,
    ) -> AsyncGenerator[HookResult, None]:
        """Executa hooks PreToolUse — equivalente de executePreToolHooks do TS."""
        context = HookContext(
            hook_event_name=HookEvent.PRE_TOOL_USE,
            session_id=session_id,
            cwd=cwd,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_use_id=tool_use_id,
            permission_mode=permission_mode,
        )
        async for result in self.execute(
            HookEvent.PRE_TOOL_USE,
            context,
            match_query=tool_name,
            timeout=timeout,
            session_id=session_id,
        ):
            yield result

    async def execute_post_tool(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_use_id: str,
        tool_response: Any,
        session_id: str,
        *,
        cwd: str | None = None,
        permission_mode: str | None = None,
        timeout: float = DEFAULT_HOOK_TIMEOUT,
    ) -> AsyncGenerator[HookResult, None]:
        """Executa hooks PostToolUse — equivalente de executePostToolHooks do TS."""
        context = HookContext(
            hook_event_name=HookEvent.POST_TOOL_USE,
            session_id=session_id,
            cwd=cwd,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_use_id=tool_use_id,
            tool_response=tool_response,
            permission_mode=permission_mode,
        )
        async for result in self.execute(
            HookEvent.POST_TOOL_USE,
            context,
            match_query=tool_name,
            timeout=timeout,
            session_id=session_id,
        ):
            yield result

    async def execute_post_tool_failure(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_use_id: str,
        error: str,
        session_id: str,
        *,
        cwd: str | None = None,
        is_interrupt: bool = False,
        permission_mode: str | None = None,
        timeout: float = DEFAULT_HOOK_TIMEOUT,
    ) -> AsyncGenerator[HookResult, None]:
        """Executa hooks PostToolUseFailure — equivalente de executePostToolUseFailureHooks do TS."""
        context = HookContext(
            hook_event_name=HookEvent.POST_TOOL_USE_FAILURE,
            session_id=session_id,
            cwd=cwd,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_use_id=tool_use_id,
            error=error,
            is_interrupt=is_interrupt,
            permission_mode=permission_mode,
        )
        async for result in self.execute(
            HookEvent.POST_TOOL_USE_FAILURE,
            context,
            match_query=tool_name,
            timeout=timeout,
            session_id=session_id,
        ):
            yield result

    async def execute_stop(
        self,
        session_id: str,
        *,
        cwd: str | None = None,
        permission_mode: str | None = None,
        is_subagent: bool = False,
        agent_id: str | None = None,
        agent_type: str | None = None,
        timeout: float = DEFAULT_HOOK_TIMEOUT,
    ) -> AsyncGenerator[HookResult, None]:
        """Executa hooks Stop — equivalente de executeStopHooks do TS."""
        event = HookEvent.SUBAGENT_STOP if is_subagent else HookEvent.STOP
        context = HookContext(
            hook_event_name=event,
            session_id=session_id,
            cwd=cwd,
            permission_mode=permission_mode,
            agent_id=agent_id,
            agent_type=agent_type,
        )
        async for result in self.execute(
            event,
            context,
            timeout=timeout,
            session_id=session_id,
            agent_id=agent_id,
        ):
            yield result

    async def execute_user_prompt_submit(
        self,
        session_id: str,
        *,
        cwd: str | None = None,
        permission_mode: str | None = None,
        timeout: float = DEFAULT_HOOK_TIMEOUT,
    ) -> AsyncGenerator[HookResult, None]:
        """Executa hooks UserPromptSubmit."""
        context = HookContext(
            hook_event_name=HookEvent.USER_PROMPT_SUBMIT,
            session_id=session_id,
            cwd=cwd,
            permission_mode=permission_mode,
        )
        async for result in self.execute(
            HookEvent.USER_PROMPT_SUBMIT,
            context,
            timeout=timeout,
            session_id=session_id,
        ):
            yield result

    async def execute_session_start(
        self,
        session_id: str,
        *,
        cwd: str | None = None,
        permission_mode: str | None = None,
        timeout: float = DEFAULT_HOOK_TIMEOUT,
    ) -> AsyncGenerator[HookResult, None]:
        """Executa hooks SessionStart."""
        context = HookContext(
            hook_event_name=HookEvent.SESSION_START,
            session_id=session_id,
            cwd=cwd,
            permission_mode=permission_mode,
        )
        async for result in self.execute(
            HookEvent.SESSION_START,
            context,
            timeout=timeout,
            session_id=session_id,
        ):
            yield result

    async def execute_instructions_loaded(
        self,
        session_id: str,
        memory_type: str,
        file_path: str,
        content: str,
        *,
        cwd: str | None = None,
        timeout: float = DEFAULT_HOOK_TIMEOUT,
    ) -> AsyncGenerator[HookResult, None]:
        """Executa hooks InstructionsLoaded — disparado quando um MIND.md é carregado.

        Equivalente ao hook InstructionsLoaded do Claude Code.
        Permite validação, transformação ou logging de instruções carregadas.
        """
        context = HookContext(
            hook_event_name=HookEvent.INSTRUCTIONS_LOADED,
            session_id=session_id,
            cwd=cwd,
            extra={
                "memory_type": memory_type,
                "file_path": file_path,
                "content_length": len(content),
            },
        )
        async for result in self.execute(
            HookEvent.INSTRUCTIONS_LOADED,
            context,
            match_query=memory_type,
            timeout=timeout,
            session_id=session_id,
        ):
            yield result

    async def execute_mission_start(
        self,
        session_id: str,
        mission_id: str,
        mission_name: str,
        *,
        cwd: str | None = None,
        timeout: float = DEFAULT_HOOK_TIMEOUT,
    ) -> AsyncGenerator[HookResult, None]:
        """Executa hooks MissionStart — MindFlow específico."""
        context = HookContext(
            hook_event_name=HookEvent.MISSION_START,
            session_id=session_id,
            cwd=cwd,
            mission_id=mission_id,
            mission_name=mission_name,
        )
        async for result in self.execute(
            HookEvent.MISSION_START,
            context,
            match_query=mission_name,
            timeout=timeout,
            session_id=session_id,
        ):
            yield result

    async def execute_mission_stop(
        self,
        session_id: str,
        mission_id: str,
        mission_name: str,
        *,
        cwd: str | None = None,
        timeout: float = DEFAULT_HOOK_TIMEOUT,
    ) -> AsyncGenerator[HookResult, None]:
        """Executa hooks MissionStop — MindFlow específico."""
        context = HookContext(
            hook_event_name=HookEvent.MISSION_STOP,
            session_id=session_id,
            cwd=cwd,
            mission_id=mission_id,
            mission_name=mission_name,
        )
        async for result in self.execute(
            HookEvent.MISSION_STOP,
            context,
            match_query=mission_name,
            timeout=timeout,
            session_id=session_id,
        ):
            yield result

    async def execute_session_end(
        self,
        session_id: str,
        reason: str,
        *,
        cwd: str | None = None,
        timeout: float = DEFAULT_HOOK_TIMEOUT,
    ) -> AsyncGenerator[HookResult, None]:
        """Executa hooks SessionEnd."""
        context = HookContext(
            hook_event_name=HookEvent.SESSION_END,
            session_id=session_id,
            reason=reason,
            cwd=cwd,
        )
        async for result in self.execute(
            HookEvent.SESSION_END,
            context,
            match_query=reason,
            timeout=timeout,
            session_id=session_id,
        ):
            yield result

    async def execute_stop_failure(
        self,
        session_id: str,
        stop_error: str,
        *,
        cwd: str | None = None,
        timeout: float = DEFAULT_HOOK_TIMEOUT,
    ) -> AsyncGenerator[HookResult, None]:
        """Executa hooks StopFailure."""
        context = HookContext(
            hook_event_name=HookEvent.STOP_FAILURE,
            session_id=session_id,
            stop_error=stop_error,
            cwd=cwd,
        )
        async for result in self.execute(
            HookEvent.STOP_FAILURE,
            context,
            match_query=stop_error,
            timeout=timeout,
            session_id=session_id,
        ):
            yield result

    async def execute_pre_compact(
        self,
        session_id: str,
        trigger: str,
        *,
        cwd: str | None = None,
        timeout: float = DEFAULT_HOOK_TIMEOUT,
    ) -> AsyncGenerator[HookResult, None]:
        """Executa hooks PreCompact."""
        context = HookContext(
            hook_event_name=HookEvent.PRE_COMPACT,
            session_id=session_id,
            trigger=trigger,
            cwd=cwd,
        )
        async for result in self.execute(
            HookEvent.PRE_COMPACT,
            context,
            match_query=trigger,
            timeout=timeout,
            session_id=session_id,
        ):
            yield result

    async def execute_post_compact(
        self,
        session_id: str,
        trigger: str,
        summary: str,
        *,
        cwd: str | None = None,
        timeout: float = DEFAULT_HOOK_TIMEOUT,
    ) -> AsyncGenerator[HookResult, None]:
        """Executa hooks PostCompact."""
        context = HookContext(
            hook_event_name=HookEvent.POST_COMPACT,
            session_id=session_id,
            trigger=trigger,
            summary=summary,
            cwd=cwd,
        )
        async for result in self.execute(
            HookEvent.POST_COMPACT,
            context,
            match_query=trigger,
            timeout=timeout,
            session_id=session_id,
        ):
            yield result

    async def execute_notification(
        self,
        session_id: str,
        notification_type: str,
        *,
        cwd: str | None = None,
        timeout: float = DEFAULT_HOOK_TIMEOUT,
    ) -> AsyncGenerator[HookResult, None]:
        """Executa hooks Notification."""
        context = HookContext(
            hook_event_name=HookEvent.NOTIFICATION,
            session_id=session_id,
            notification_type=notification_type,
            cwd=cwd,
        )
        async for result in self.execute(
            HookEvent.NOTIFICATION,
            context,
            match_query=notification_type,
            timeout=timeout,
            session_id=session_id,
        ):
            yield result

    async def execute_task_created(
        self,
        session_id: str,
        task_id: str,
        task_name: str,
        *,
        cwd: str | None = None,
        timeout: float = DEFAULT_HOOK_TIMEOUT,
    ) -> AsyncGenerator[HookResult, None]:
        """Executa hooks TaskCreated."""
        context = HookContext(
            hook_event_name=HookEvent.TASK_CREATED,
            session_id=session_id,
            task_id=task_id,
            task_name=task_name,
            cwd=cwd,
        )
        async for result in self.execute(
            HookEvent.TASK_CREATED,
            context,
            match_query=task_name,
            timeout=timeout,
            session_id=session_id,
        ):
            yield result

    async def execute_task_completed(
        self,
        session_id: str,
        task_id: str,
        task_name: str,
        *,
        cwd: str | None = None,
        timeout: float = DEFAULT_HOOK_TIMEOUT,
    ) -> AsyncGenerator[HookResult, None]:
        """Executa hooks TaskCompleted."""
        context = HookContext(
            hook_event_name=HookEvent.TASK_COMPLETED,
            session_id=session_id,
            task_id=task_id,
            task_name=task_name,
            cwd=cwd,
        )
        async for result in self.execute(
            HookEvent.TASK_COMPLETED,
            context,
            match_query=task_name,
            timeout=timeout,
            session_id=session_id,
        ):
            yield result

    async def execute_setup(
        self,
        session_id: str,
        setup_trigger: str,
        *,
        cwd: str | None = None,
        timeout: float = DEFAULT_HOOK_TIMEOUT,
    ) -> AsyncGenerator[HookResult, None]:
        """Executa hooks Setup."""
        context = HookContext(
            hook_event_name=HookEvent.SETUP,
            session_id=session_id,
            setup_trigger=setup_trigger,
            cwd=cwd,
        )
        async for result in self.execute(
            HookEvent.SETUP,
            context,
            match_query=setup_trigger,
            timeout=timeout,
            session_id=session_id,
        ):
            yield result

    async def execute_config_change(
        self,
        session_id: str,
        config_key: str,
        old_value: Any,
        new_value: Any,
        *,
        cwd: str | None = None,
        timeout: float = DEFAULT_HOOK_TIMEOUT,
    ) -> AsyncGenerator[HookResult, None]:
        """Executa hooks ConfigChange."""
        context = HookContext(
            hook_event_name=HookEvent.CONFIG_CHANGE,
            session_id=session_id,
            config_key=config_key,
            old_value=old_value,
            new_value=new_value,
            cwd=cwd,
        )
        async for result in self.execute(
            HookEvent.CONFIG_CHANGE,
            context,
            match_query=config_key,
            timeout=timeout,
            session_id=session_id,
        ):
            yield result

    async def execute_file_changed(
        self,
        session_id: str,
        file_path: str,
        *,
        cwd: str | None = None,
        timeout: float = DEFAULT_HOOK_TIMEOUT,
    ) -> AsyncGenerator[HookResult, None]:
        """Executa hooks FileChanged."""
        context = HookContext(
            hook_event_name=HookEvent.FILE_CHANGED,
            session_id=session_id,
            file_path=file_path,
            cwd=cwd,
        )
        async for result in self.execute(
            HookEvent.FILE_CHANGED,
            context,
            match_query=file_path,
            timeout=timeout,
            session_id=session_id,
        ):
            yield result

    async def execute_cwd_changed(
        self,
        session_id: str,
        old_cwd: str,
        new_cwd: str,
        *,
        cwd: str | None = None,
        timeout: float = DEFAULT_HOOK_TIMEOUT,
    ) -> AsyncGenerator[HookResult, None]:
        """Executa hooks CwdChanged."""
        context = HookContext(
            hook_event_name=HookEvent.CWD_CHANGED,
            session_id=session_id,
            old_cwd=old_cwd,
            new_cwd=new_cwd,
            cwd=cwd,
        )
        async for result in self.execute(
            HookEvent.CWD_CHANGED,
            context,
            match_query=new_cwd,
            timeout=timeout,
            session_id=session_id,
        ):
            yield result

    # ─── Executores Internos ───────────────────────────────────────

    async def _execute_command(
        self,
        cmd: HookCommand,
        ctx: HookContext,
        timeout: float,
    ) -> HookResult:
        """Executa hook como subprocess — equivalente de execCommandHook do TS.

        Args:
            cmd: Comando do hook com timeout opcional
            ctx: Contexto do hook
            timeout: Timeout padrão (usado se cmd.timeout não especificado)

        Returns:
            HookResult com status e output do comando
        """
        # Usa TimeoutConfig para obter timeout efetivo
        # Precedência: cmd.timeout > event-specific > default
        effective_timeout = TimeoutConfig.get_timeout(
            event=str(ctx.hook_event_name),
            hook_timeout=float(cmd.timeout) if cmd.timeout else None,
        )

        # Se timeout padrão foi passado explicitamente, usa ele
        if timeout != DEFAULT_HOOK_TIMEOUT:
            effective_timeout = timeout

        hook_id = str(uuid.uuid4())
        hook_name = cmd.command or "<command>"
        await self._emit_hook_execution_event(
            state=HookExecutionState.STARTED,
            hook_id=hook_id,
            hook_name=hook_name,
            ctx=ctx,
        )

        proc = await asyncio.create_subprocess_shell(
            cmd.command or "",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Pass context via stdin (equivalente ao TypeScript json input)
        json_input = json.dumps(ctx.to_dict()).encode()

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(input=json_input),
                timeout=effective_timeout,
            )
        except asyncio.TimeoutError:
            # Kill process on timeout
            try:
                proc.kill()
                await proc.wait()
            except Exception:
                pass
            result = HookResult(
                event=ctx.hook_event_name,
                command=cmd.command or "",
                status="timeout",
                error=f"Hook timed out after {effective_timeout}s",
            )
            await self._emit_hook_execution_event(
                state=HookExecutionState.COMPLETED,
                hook_id=hook_id,
                hook_name=hook_name,
                ctx=ctx,
                outcome=result.status,
            )
            return result

        stdout_str = stdout_bytes.decode().strip()
        stderr_str = stderr_bytes.decode().strip()

        if proc.returncode != 0:
            result = self._build_nonzero_exit_result(
                ctx=ctx,
                command=cmd.command or "",
                returncode=proc.returncode,
                stderr=stderr_str,
            )
            await self._emit_hook_execution_event(
                state=HookExecutionState.COMPLETED,
                hook_id=hook_id,
                hook_name=hook_name,
                ctx=ctx,
                stdout=stdout_str or None,
                stderr=stderr_str or None,
                output=stdout_str or None,
                exit_code=proc.returncode,
                outcome=result.status,
            )
            return result

        if not stdout_str:
            result = HookResult(
                event=ctx.hook_event_name,
                command=cmd.command or "",
                status="success",
            )
            await self._emit_hook_execution_event(
                state=HookExecutionState.COMPLETED,
                hook_id=hook_id,
                hook_name=hook_name,
                ctx=ctx,
                exit_code=proc.returncode,
                outcome=result.status,
            )
            return result

        try:
            response = json.loads(stdout_str)
            result = HookResult.from_response(ctx.hook_event_name, cmd.command or "", response)
        except json.JSONDecodeError:
            # Hook output is plain text — treat as add_context
            result = HookResult(
                event=ctx.hook_event_name,
                command=cmd.command or "",
                status="success",
                raw_output=stdout_str,
                add_context=stdout_str,
            )
        await self._emit_hook_execution_event(
            state=HookExecutionState.COMPLETED,
            hook_id=hook_id,
            hook_name=hook_name,
            ctx=ctx,
            stdout=stdout_str or None,
            stderr=stderr_str or None,
            output=stdout_str or None,
            exit_code=proc.returncode,
            outcome=result.status,
        )
        return result

    async def _execute_function(
        self,
        callback: Callable[..., Any],
        ctx: HookContext,
        timeout: float,
    ) -> HookResult:
        """Executa function hook — equivalente de function hook execution do TS.

        Args:
            callback: Função callback assíncrona
            ctx: Contexto do hook
            timeout: Timeout padrão

        Returns:
            HookResult com status e output da função
        """
        # Usa TimeoutConfig para obter timeout efetivo
        effective_timeout = TimeoutConfig.get_timeout(
            event=str(ctx.hook_event_name),
            hook_timeout=None,  # Function hooks não têm timeout configurável individual
        )

        # Se timeout padrão foi passado explicitamente, usa ele
        if timeout != DEFAULT_HOOK_TIMEOUT:
            effective_timeout = timeout

        hook_id = str(uuid.uuid4())
        hook_name = getattr(callback, "__name__", "<function>")
        await self._emit_hook_execution_event(
            state=HookExecutionState.STARTED,
            hook_id=hook_id,
            hook_name=hook_name,
            ctx=ctx,
        )

        try:
            result = await asyncio.wait_for(callback(ctx), timeout=effective_timeout)
            if isinstance(result, HookResult):
                final_result = result
            elif isinstance(result, dict):
                final_result = HookResult.from_response(
                    ctx.hook_event_name,
                    "<function>",
                    result,
                )
            else:
                final_result = HookResult(
                    event=ctx.hook_event_name,
                    command="<function>",
                    status="success",
                )
        except asyncio.TimeoutError:
            final_result = HookResult(
                event=ctx.hook_event_name,
                command="<function>",
                status="timeout",
                error=f"Function hook timed out after {effective_timeout}s",
            )
        except Exception as exc:
            final_result = HookResult(
                event=ctx.hook_event_name,
                command="<function>",
                status="error",
                error=str(exc),
            )
        await self._emit_hook_execution_event(
            state=HookExecutionState.COMPLETED,
            hook_id=hook_id,
            hook_name=hook_name,
            ctx=ctx,
            outcome=final_result.status,
        )
        return final_result

    def _build_nonzero_exit_result(
        self,
        *,
        ctx: HookContext,
        command: str,
        returncode: int,
        stderr: str,
    ) -> HookResult:
        """Converte códigos de saída não-zero em HookResult com semântica por evento."""
        message = stderr or f"Exit code {returncode}"
        try:
            event = HookEvent(str(ctx.hook_event_name))
        except ValueError:
            event = None

        if returncode == 2 and event in {
            HookEvent.PRE_TOOL_USE,
            HookEvent.PERMISSION_REQUEST,
        }:
            return HookResult(
                event=ctx.hook_event_name,
                command=command,
                status="blocked",
                behavior=HookPermissionBehavior.DENY,
                reason=message,
                error=message,
            )

        if returncode == 2 and event in {
            HookEvent.PRE_COMPACT,
            HookEvent.STOP,
            HookEvent.SUBAGENT_STOP,
        }:
            return HookResult(
                event=ctx.hook_event_name,
                command=command,
                status="blocked",
                error=message,
                prevent_continuation=True,
                stop_reason=message,
            )

        return HookResult(
            event=ctx.hook_event_name,
            command=command,
            status="error",
            error=message,
        )

    async def _emit_hook_execution_event(
        self,
        *,
        state: HookExecutionState,
        hook_id: str,
        hook_name: str,
        ctx: HookContext,
        stdout: str | None = None,
        stderr: str | None = None,
        output: str | None = None,
        exit_code: int | None = None,
        outcome: str | None = None,
    ) -> None:
        """Emite evento de execução de hook para UI/transcript."""
        await HookEventBroadcaster.get_instance().emit(
            HookExecutionEvent(
                state=state,
                hook_id=hook_id,
                hook_name=hook_name,
                hook_event=str(ctx.hook_event_name),
                session_id=ctx.session_id,
                stdout=stdout,
                stderr=stderr,
                output=output,
                exit_code=exit_code,
                outcome=outcome,
            )
        )
