"""Permission schemas for MindFlow tool execution.

Mirrors the Claude Code CLI permission system (Tool.ts permission types):
- PermissionMode: auto → plan → default → bypassPermissions
- PermissionResult: discriminated union with behavior + optional metadata
- PermissionRule: pattern-based allow/deny/ask rules

Design principles:
- All permission checks return a PermissionResult
- Rules are evaluated in order: deny → validateInput → mode → tool check → hooks → user
- Pattern matching supports wildcards: "Bash(git *)", "FileRead(/tmp/*)"
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PermissionMode(StrEnum):
    """How the system handles tool permissions.

    Mirrors Claude Code's permission modes:
    - AUTO: classifier + hooks decide, no user prompt
    - PLAN: model decides whether to use the tool
    - DEFAULT: user asked per tool (interactive approval)
    - BYPASS: all allowed (sandbox only)
    """

    AUTO = "auto"
    PLAN = "plan"
    DEFAULT = "default"
    BYPASS = "bypass"


class PermissionBehavior(StrEnum):
    """Action to take for a tool permission request."""

    ALLOW = "allow"   # Proceed with tool execution
    DENY = "deny"     # Block tool execution
    ASK = "ask"       # Prompt user for approval


class RuleSource(StrEnum):
    """Where a permission rule originated."""

    USER = "user"              # User-defined (settings.json, --allowed-tools)
    POLICY = "policy"          # Enterprise/managed policy
    DEFAULT = "default"        # System default deny/allow list
    HOOK = "hook"              # Hook-provided override


# ---------------------------------------------------------------------------
# Rule Schemas
# ---------------------------------------------------------------------------


class PermissionRule(BaseModel):
    """A single permission rule matching a tool pattern.

    Similar to Claude Code's alwaysAllowRules/alwaysDenyRules structure.
    """

    model_config = {"extra": "ignore", "populate_by_name": True}

    # Pattern to match against tool+input.
    # Format: "ToolName(pattern)" or just "ToolName" for all invocations.
    # Examples: "Bash", "Bash(git *)", "FileRead(/tmp/*)", "*" (all tools)
    tool_pattern: str = Field(..., description="Tool pattern to match")

    # Optional rule content (restrictions, modifications).
    # E.g., {"readOnly": true}, {"max_lines": 1000}
    rule_content: dict[str, Any] | None = Field(
        default=None,
        description="Optional rule restrictions",
    )

    # Where this rule came from (for auditing/debugging)
    source: RuleSource = Field(default=RuleSource.USER, description="Rule source")

    # Display-friendly description
    display: str = Field(default="", description="Human-readable rule description")

    @property
    def tool_name(self) -> str:
        """Extract tool name from pattern (before any parenthesis)."""
        idx = self.tool_pattern.find("(")
        if idx > 0:
            return self.tool_pattern[:idx]
        return self.tool_pattern

    @property
    def has_constraint(self) -> bool:
        """Whether this rule has specific constraints (not blanket allow/deny)."""
        idx = self.tool_pattern.find("(")
        return idx > 0 and self.tool_pattern[-1] == ")"


# ---------------------------------------------------------------------------
# Result Schema
# ---------------------------------------------------------------------------


class PermissionResult(BaseModel):
    """Result of a tool permission check.

    Mirrors Claude Code's PermissionResult discriminated union:
    - { behavior: 'allow', updatedInput?: {...} }
    - { behavior: 'deny', reason?: string }
    - { behavior: 'ask', prompt?: string }
    """

    model_config = {"extra": "ignore", "populate_by_name": True}

    behavior: PermissionBehavior = Field(
        ..., description="Whether to allow, deny, or ask"
    )

    # Only when behavior=allow: modified input after permission processing
    updated_input: dict[str, Any] | None = Field(
        default=None,
        description="Modified tool input after permission processing",
    )

    # Only when behavior=deny: why it was denied
    reason: str | None = Field(
        default=None,
        description="Reason for denial",
    )

    # Only when behavior=ask: prompt to show user
    prompt: str | None = Field(
        default=None,
        description="User-facing prompt (when behavior=ask)",
    )

    # Optional structured error for denials
    error: str | None = Field(
        default=None,
        description="Structured error details for denials",
    )

    @model_validator(mode="after")
    def _validate_behavior_specifics(self) -> PermissionResult:
        """Ensure the right fields are set for each behavior."""
        if self.behavior == PermissionBehavior.DENY and not self.reason:
            self.reason = "Tool use denied by permission policy"
        if self.behavior == PermissionBehavior.ALLOW:
            # Clear deny-specific fields when allowed
            self.reason = None
            self.error = None
        return self

    def is_allowed(self) -> bool:
        return self.behavior == PermissionBehavior.ALLOW

    def is_denied(self) -> bool:
        return self.behavior == PermissionBehavior.DENY

    def requires_user_input(self) -> bool:
        return self.behavior == PermissionBehavior.ASK