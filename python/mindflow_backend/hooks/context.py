"""HookContext — Input for all hooks.

Adapted from Claude Code's HookInput and createBaseHookInput().
Every hook receives a HookContext with the event-specific fields populated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mindflow_backend.hooks.types import HookEvent


@dataclass
class HookContext:
    """Contexto passado para todos os hooks.

    Equivalente de HookInput + createBaseHookInput() do src/utils/hooks.ts.
    Todos os campos são opcionais porque diferentes eventos preenchem
    diferentes subconjuntos de campos.
    """

    # ── Identificador do evento ──
    hook_event_name: str  # HookEvent.value

    # ── Sessão ──
    session_id: str
    transcript_path: str | None = None
    cwd: str | None = None

    # ── Tool-specific (PreToolUse, PostToolUse, PostToolUseFailure) ──
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    tool_use_id: str | None = None
    tool_response: Any = None  # PostToolUse only
    error: str | None = None  # PostToolUseFailure only
    is_interrupt: bool | None = None  # PostToolUseFailure

    # ── Permission mode ──
    permission_mode: str | None = None  # "default" | "plan" | "auto" | "bypassPermissions"

    # ── Agent-specific (AgentStart/AgentStop) ──
    agent_id: str | None = None
    agent_type: str | None = None

    # ── Mission-specific (MindFlow exclusive) ──
    mission_id: str | None = None
    mission_name: str | None = None

    # ── Permission request specific ──
    description: str | None = None
    permission_suggestions: list[dict[str, Any]] | None = None

    # ── SessionEnd specific ──
    reason: str | None = None  # "clear" | "resume" | "logout" | "other"

    # ── PreCompact / PostCompact specific ──
    trigger: str | None = None  # "manual" | "auto"
    summary: str | None = None  # PostCompact only

    # ── Notification specific ──
    notification_type: str | None = None

    # ── Task lifecycle specific ──
    task_id: str | None = None
    task_name: str | None = None

    # ── ConfigChange specific ──
    config_key: str | None = None
    old_value: Any = None
    new_value: Any = None

    # ── FileChanged / CwdChanged specific ──
    file_path: str | None = None
    old_cwd: str | None = None
    new_cwd: str | None = None

    # ── StopFailure specific ──
    stop_error: str | None = None

    # ── Subagent specific ──
    subagent_id: str | None = None
    subagent_type: str | None = None

    # ── Setup specific ──
    setup_trigger: str | None = None

    # ── MCP Elicitation specific ──
    mcp_server_name: str | None = None

    # ── Worktree specific ──
    worktree_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serializa para JSON — passado via stdin ao hook command."""
        result: dict[str, Any] = {}
        for key, value in self.__dict__.items():
            if value is not None:
                result[key] = value
        return result
