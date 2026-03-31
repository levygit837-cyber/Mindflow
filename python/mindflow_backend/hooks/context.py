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

    def to_dict(self) -> dict[str, Any]:
        """Serializa para JSON — passado via stdin ao hook command."""
        result: dict[str, Any] = {}
        for key, value in self.__dict__.items():
            if value is not None:
                result[key] = value
        return result