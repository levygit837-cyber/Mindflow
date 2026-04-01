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
    """Events that trigger hooks — Claude Code parity + MindFlow extensions.

    Total: 27 eventos (paridade com Claude Code)
    """

    # === Tool Lifecycle (4) ===
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    POST_TOOL_USE_FAILURE = "PostToolUseFailure"
    PERMISSION_REQUEST = "PermissionRequest"

    # === Session Lifecycle (3) ===
    SESSION_START = "SessionStart"
    SESSION_END = "SessionEnd"          # [NOVO]
    STOP = "Stop"
    STOP_FAILURE = "StopFailure"        # [NOVO]

    # === Agent Lifecycle (2) ===
    AGENT_START = "AgentStart"
    AGENT_STOP = "AgentStop"

    # === Subagent Lifecycle (2) ===
    SUBAGENT_START = "SubagentStart"    # [NOVO]
    SUBAGENT_STOP = "SubagentStop"      # [NOVO]

    # === User Interaction (2) ===
    USER_PROMPT_SUBMIT = "UserPromptSubmit"
    PERMISSION_DENIED = "PermissionDenied"

    # === Compaction (2) ===
    PRE_COMPACT = "PreCompact"          # [NOVO]
    POST_COMPACT = "PostCompact"        # [NOVO]

    # === Notification (1) ===
    NOTIFICATION = "Notification"       # [NOVO]

    # === Task Lifecycle (2) ===
    TASK_CREATED = "TaskCreated"        # [NOVO]
    TASK_COMPLETED = "TaskCompleted"    # [NOVO]

    # === Config/Setup (2) ===
    SETUP = "Setup"                     # [NOVO]
    CONFIG_CHANGE = "ConfigChange"      # [NOVO]

    # === File System (2) ===
    FILE_CHANGED = "FileChanged"        # [NOVO]
    CWD_CHANGED = "CwdChanged"          # [NOVO]

    # === Teammate (1) ===
    TEAMMATE_IDLE = "TeammateIdle"      # [NOVO]

    # === MCP (2) ===
    ELICITATION = "Elicitation"         # [NOVO]
    ELICITATION_RESULT = "ElicitationResult"  # [NOVO]

    # === Worktree (2) ===
    WORKTREE_CREATE = "WorktreeCreate"  # [NOVO]
    WORKTREE_REMOVE = "WorktreeRemove"  # [NOVO]

    # === Instructions (1) ===
    INSTRUCTIONS_LOADED = "InstructionsLoaded"

    # === MindFlow Exclusive (2) ===
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