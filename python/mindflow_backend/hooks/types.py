"""Hook Types — Core types and schemas for the MindFlow hook system.

Adapted from Claude Code's src/types/hooks.ts with MindFlow-specific extensions.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


# ─── Hook Events ─────────────────────────────────────────────────────

class HookEvent(StrEnum):
    """Events that trigger hooks — adapted from Claude Code HookEvent."""

    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    PRE_TOOL_USE_FAILURE = "PreToolUseFailure"
    POST_TOOL_USE_FAILURE = "PostToolUseFailure"
    POST_TOOL_FAILURE = "PostToolUseFailure"
    STOP = "Stop"
    AGENT_START = "AgentStart"
    AGENT_STOP = "AgentStop"
    USER_PROMPT_SUBMIT = "UserPromptSubmit"
    SESSION_START = "SessionStart"
    PERMISSION_REQUEST = "PermissionRequest"
    PERMISSION_DENIED = "PermissionDenied"
    # MindFlow-specific mission hooks
    MISSION_START = "MissionStart"
    MISSION_STOP = "MissionStop"


# ─── Permission Behaviors ────────────────────────────────────────────

class HookPermissionBehavior(StrEnum):
    """Permission decision from a hook — adapted from Claude Code permissionBehavior."""
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"
    PASSTHROUGH = "passthrough"


# ─── Hook Command Types ──────────────────────────────────────────────

class HookCommandType(StrEnum):
    """Types of hook commands — adapted from Claude Code HookCommand."""
    COMMAND = "command"
    PROMPT = "prompt"
    AGENT = "agent"
    HTTP = "http"


# ─── Session Start Sources ───────────────────────────────────────────

class SessionStartSource(StrEnum):
    """Sources for SessionStart hooks — adapted from Claude Code."""
    STARTUP = "startup"
    RESUME = "resume"
    CLEAR = "clear"
    COMPACT = "compact"


# ─── Permission Mode ─────────────────────────────────────────────────

class PermissionMode(StrEnum):
    """Permission modes — adapted from Claude Code permissionMode."""
    DEFAULT = "default"
    PLAN = "plan"
    AUTO = "auto"
    BYPASS_PERMISSIONS = "bypassPermissions"