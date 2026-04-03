"""Hook Helpers — Funções auxiliares para o sistema de hooks.

Adaptado de src/utils/hooks/hookHelpers.ts do Claude Code.
"""

from __future__ import annotations

import json
import os
from typing import Any

from mindflow_backend.hooks.types import HookEvent
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


def is_hook_event(value: str) -> bool:
    """Verifica se uma string é um HookEvent válido."""
    try:
        HookEvent(value)
        return True
    except ValueError:
        return False


def create_hook_input(
    event: HookEvent,
    session_id: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Cria um dicionário de input para hook — equivalente de createBaseHookInput() do TS."""
    result: dict[str, Any] = {
        "hook_event_name": event.value,
        "session_id": session_id,
    }

    # Adicionar cwd se disponível
    try:
        result["cwd"] = os.getcwd()
    except OSError:
        pass

    # Adicionar campos extras
    for key, value in kwargs.items():
        if value is not None:
            result[key] = value

    return result


def serialize_hook_input(context_dict: dict[str, Any]) -> str:
    """Serializa hook input para JSON — passado via stdin ao hook command."""
    return json.dumps(context_dict, default=str)


def parse_hook_response(stdout: str) -> dict[str, Any]:
    """Parseia resposta JSON de um hook command.

    Equivalente de HookResult.from_response() — usado quando o caller
    precisa do dict bruto antes de criar HookResult.
    """
    if not stdout or not stdout.strip():
        return {"ok": True}

    try:
        return json.loads(stdout.strip())
    except json.JSONDecodeError:
        return {
            "ok": False,
            "error": f"Invalid JSON output from hook: {stdout[:200]}",
        }


def validate_hook_config(hooks_config: dict[str, list[dict[str, Any]]]) -> list[str]:
    """Valida configuração de hooks.

    Retorna lista de erros de validação (vazio = válido).
    """
    errors: list[str] = []

    for event_str, hook_list in hooks_config.items():
        if not is_hook_event(event_str):
            errors.append(f"Unknown hook event: {event_str}")
            continue

        if not isinstance(hook_list, list):
            errors.append(f"Hooks for '{event_str}' must be a list")
            continue

        for i, hook in enumerate(hook_list):
            if not isinstance(hook, dict):
                errors.append(f"Hook {i} in '{event_str}' must be a dict")
                continue

            hook_type = hook.get("type", "command")
            if hook_type == "command" and not hook.get("command"):
                errors.append(
                    f"Command hook {i} in '{event_str}' requires 'command' field"
                )

            if hook.get("timeout") is not None:
                timeout = hook["timeout"]
                if not isinstance(timeout, (int, float)) or timeout <= 0:
                    errors.append(
                        f"Hook {i} in '{event_str}': timeout must be a positive number"
                    )

    return errors


def get_match_query_for_event(
    event: HookEvent,
    context: dict[str, Any],
) -> str | None:
    """Extrai match query do contexto do evento.

    Equivalente da lógica de matchQuery em getMatchingHooks do TS.
    """
    if event == HookEvent.PRE_TOOL_USE:
        return context.get("tool_name")
    if event == HookEvent.POST_TOOL_USE:
        return context.get("tool_name")
    if event == HookEvent.POST_TOOL_USE_FAILURE:
        return context.get("tool_name")
    if event == HookEvent.PERMISSION_DENIED:
        return context.get("tool_name")
    if event == HookEvent.PERMISSION_REQUEST:
        return context.get("tool_name")
    if event == HookEvent.SESSION_START:
        return context.get("source", "startup")
    if event == HookEvent.AGENT_START:
        return context.get("agent_type")
    if event == HookEvent.AGENT_STOP:
        return context.get("agent_type")
    if event == HookEvent.MISSION_START:
        return context.get("mission_name")
    if event == HookEvent.MISSION_STOP:
        return context.get("mission_name")
    if event == HookEvent.SESSION_END:
        return context.get("reason")
    if event == HookEvent.STOP_FAILURE:
        return context.get("stop_error")
    if event == HookEvent.PRE_COMPACT:
        return context.get("trigger")
    if event == HookEvent.POST_COMPACT:
        return context.get("trigger")
    if event == HookEvent.NOTIFICATION:
        return context.get("notification_type")
    if event == HookEvent.TASK_CREATED:
        return context.get("task_name")
    if event == HookEvent.TASK_COMPLETED:
        return context.get("task_name")
    if event == HookEvent.SETUP:
        return context.get("setup_trigger")
    if event == HookEvent.CONFIG_CHANGE:
        return context.get("config_key")
    if event == HookEvent.FILE_CHANGED:
        return context.get("file_path")
    if event == HookEvent.CWD_CHANGED:
        return context.get("new_cwd")
    if event == HookEvent.SUBAGENT_START:
        return context.get("subagent_type")
    if event == HookEvent.SUBAGENT_STOP:
        return context.get("subagent_type")
    if event == HookEvent.ELICITATION:
        return context.get("mcp_server_name")
    if event == HookEvent.ELICITATION_RESULT:
        return context.get("mcp_server_name")
    if event == HookEvent.WORKTREE_CREATE:
        return context.get("worktree_path")
    if event == HookEvent.WORKTREE_REMOVE:
        return context.get("worktree_path")
    if event == HookEvent.TEAMMATE_IDLE:
        return context.get("agent_id")
    return None
