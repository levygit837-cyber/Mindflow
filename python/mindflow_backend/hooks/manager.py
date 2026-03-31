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

from mindflow_backend.hooks.context import HookContext
from mindflow_backend.hooks.registry import HookRegistry
from mindflow_backend.hooks.result import AggregatedHookResult, HookCommand, HookMatcher, HookResult
from mindflow_backend.hooks.types import HookEvent, HookPermissionBehavior
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

# Default timeout for hook commands (seconds)
DEFAULT_HOOK_TIMEOUT = 30


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
                cmd = HookCommand(
                    type=hook_dict.get("type", "command"),
                    command=hook_dict.get("command"),
                    timeout=hook_dict.get("timeout"),
                )
                self._registry.register_plugin_hook(plugin_name, event, matcher, cmd)

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
                cmd = HookCommand(
                    type=hook_dict.get("type", "command"),
                    command=hook_dict.get("command"),
                    timeout=hook_dict.get("timeout"),
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

        Usage:
            async for hook_result in manager.execute(HookEvent.PRE_TOOL_USE, ctx):
                if hook_result.behavior == "block":
                    # Impedir execução
                    pass
        """
        # 1. Buscar hook matchers para o evento
        matchers = self._registry.get_hooks_for_event(
            event,
            session_id=session_id,
            agent_id=agent_id,
        )

        # 2. Executar cada hook command
        for matcher in matchers:
            # Filtrar por matcher (equivalente a matchQuery em getMatchingHooks)
            if match_query and matcher.matcher and matcher.matcher != match_query:
                continue

            for hook_cmd in matcher.hooks:
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
                        status="error",
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

        # 3. Executar function hooks
        for matcher_str, callback in self._registry.get_function_hooks(event):
            if match_query and matcher_str and matcher_str != match_query:
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
            hook_event_name=HookEvent.POST_TOOL_FAILURE,
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
            HookEvent.POST_TOOL_FAILURE,
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
        event = HookEvent.AGENT_STOP if is_subagent else HookEvent.STOP
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

    # ─── Executores Internos ───────────────────────────────────────

    async def _execute_command(
        self,
        cmd: HookCommand,
        ctx: HookContext,
        timeout: float,
    ) -> HookResult:
        """Executa hook como subprocess — equivalente de execCommandHook do TS."""
        import shlex

        proc = await asyncio.create_subprocess_shell(
            cmd.command or "",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Pass context via stdin (equivalente ao TypeScript json input)
        json_input = json.dumps(ctx.to_dict()).encode()
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(input=json_input),
            timeout=timeout,
        )

        if proc.returncode != 0:
            return HookResult(
                event=ctx.hook_event_name,
                command=cmd.command or "",
                status="error",
                error=stderr_bytes.decode() if stderr_bytes else f"Exit code {proc.returncode}",
            )

        stdout_str = stdout_bytes.decode().strip()
        if not stdout_str:
            return HookResult(
                event=ctx.hook_event_name,
                command=cmd.command or "",
                status="success",
            )

        try:
            response = json.loads(stdout_str)
            return HookResult.from_response(ctx.hook_event_name, cmd.command or "", response)
        except json.JSONDecodeError:
            # Hook output is plain text — treat as add_context
            return HookResult(
                event=ctx.hook_event_name,
                command=cmd.command or "",
                status="success",
                raw_output=stdout_str,
                add_context=stdout_str,
            )

    async def _execute_function(
        self,
        callback: Callable[..., Any],
        ctx: HookContext,
        timeout: float,
    ) -> HookResult:
        """Executa function hook — equivalente de function hook execution do TS."""
        try:
            result = await asyncio.wait_for(callback(ctx), timeout=timeout)
            if isinstance(result, HookResult):
                return result
            # Se callback retorna dict, converter
            if isinstance(result, dict):
                return HookResult.from_response(
                    ctx.hook_event_name,
                    "<function>",
                    result,
                )
            return HookResult(
                event=ctx.hook_event_name,
                command="<function>",
                status="success",
            )
        except asyncio.TimeoutError:
            return HookResult(
                event=ctx.hook_event_name,
                command="<function>",
                status="error",
                error=f"Function hook timed out after {timeout}s",
            )