"""Core permission types — mirrors Claude Code's src/types/permissions.ts.

Design principles (adapted from Claude Code):
- PermissionMode controls how tool permissions are evaluated
- PermissionRule defines pattern-based allow/deny/ask rules
- PermissionResult is a discriminated union with behavior-specific fields
- PermissionContext aggregates all permission state for a turn

All types use Pydantic BaseModel for automatic validation where applicable.
Pure Python dataclasses/frozen for immutable result types.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PermissionMode(StrEnum):
    """How the system handles tool permissions.

    Mirrors Claude Code's permission mode cycle:
      Shift+Tab: default → acceptEdits → plan → bypassPermissions → dontAsk → default

    Adapted for MindFlow:
    - AUTO: classifier + hooks decide, no user prompt (Claude Code's "auto")
    - PLAN: read-only model decisions, no tool execution (Claude Code's "plan")
    - DEFAULT: user asked per tool or policy-based (Claude Code's "default")
    - ACCEPT_EDITS: allow edits in working directory without asking (Claude Code's "acceptEdits")
    - BYPASS: all tools allowed (Claude Code's "bypassPermissions")
    - DONT_ASK: deny all tools that would prompt (Claude Code's "dontAsk")
    """

    AUTO = "auto"
    PLAN = "plan"
    DEFAULT = "default"
    ACCEPT_EDITS = "accept_edits"
    BYPASS = "bypass"
    DONT_ASK = "dont_ask"


class PermissionBehavior(StrEnum):
    """Action to take for a tool permission request."""

    ALLOW = "allow"  # Proceed with tool execution
    DENY = "deny"  # Block tool execution
    ASK = "ask"  # Prompt user for approval


class RuleSource(StrEnum):
    """Where a permission rule originated from.

    Maps to Claude Code's PermissionRuleSource:
    - USER = userSettings (global ~/.claude settings)
    - PROJECT = projectSettings (.claude/settings.json in project)
    - LOCAL = localSettings (gitignored local settings)
    - POLICY = policySettings (enterprise-managed)
    - CLI = cliArg (--allowed-tools, --disallowed-tools)
    - HOOK = hook-provided override
    - SESSION = in-memory session-only rules
    """

    USER = "user"
    PROJECT = "project"
    LOCAL = "local"
    POLICY = "policy"
    CLI = "cli"
    HOOK = "hook"
    SESSION = "session"


# Alias for backwards compat with existing code
PermissionRuleSource = RuleSource


# ---------------------------------------------------------------------------
# Rule Value
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PermissionRuleValue:
    """The value of a permission rule — specifies which tool and optional content.

    Mirrors Claude Code's PermissionRuleValue:
      toolName: string         — e.g. "Bash", "FileRead", "Write"
      ruleContent?: string     — e.g. "git *", "/tmp/*", "npm:*" (prefix syntax)

    Pattern matching:
    - "Bash" → matches ALL Bash invocations
    - "Bash(git *)" → matches Bash with args starting with "git "
    - "FileRead(/tmp/*)" → matches FileRead with path under /tmp/
    - "Bash(npm:*)" → legacy prefix syntax (matches "npm anything")
    """

    tool_name: str
    rule_content: str | None = None

    def matches(self, actual_tool_name: str, actual_content: str | None = None) -> bool:
        """Check if this rule value matches the actual tool invocation.

        Implements Claude Code's pattern matching:
        - Exact match: "Bash" matches tool "Bash"
        - Wildcard: "Bash(git *)" matches Bash with content "git commit"
        - Legacy prefix: "Bash(npm:*)" matches Bash with content "npm install"
        """
        if self.tool_name != actual_tool_name:
            return False

        if self.rule_content is None:
            return self._is_blank(actual_content)

        if actual_content is None:
            return False

        return _pattern_match(self.rule_content, actual_content)

    @staticmethod
    def _is_blank(value: str | None) -> bool:
        return value is None or value.strip() == ""


# ---------------------------------------------------------------------------
# Permission Rule
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PermissionRule:
    """A permission rule with its source and behavior.

    Mirrors Claude Code's PermissionRule:
      source: PermissionRuleSource
      ruleBehavior: PermissionBehavior
      ruleValue: PermissionRuleValue

    Examples:
    - User added "Bash(git *)" to alwaysAllowRules →
      PermissionRule(source=USER, ruleBehavior=ALLOW,
                     ruleValue=PermissionRuleValue("Bash", "git *"))

    - Policy denies all Write →
      PermissionRule(source=POLICY, ruleBehavior=DENY,
                     ruleValue=PermissionRuleValue("Write"))
    """

    source: RuleSource
    rule_behavior: PermissionBehavior
    rule_value: PermissionRuleValue

    # Display helpers
    @property
    def display_string(self) -> str:
        """Human-readable representation, e.g. 'Bash(git *)'."""
        if self.rule_value.rule_content:
            return f"{self.rule_value.tool_name}({self.rule_value.rule_content})"
        return self.rule_value.tool_name

    @property
    def source_display(self) -> str:
        """Display string for the rule source."""
        source_labels: dict[RuleSource, str] = {
            RuleSource.USER: "user settings",
            RuleSource.PROJECT: "project settings",
            RuleSource.LOCAL: "local settings",
            RuleSource.POLICY: "policy",
            RuleSource.CLI: "CLI argument",
            RuleSource.HOOK: "hook",
            RuleSource.SESSION: "session",
        }
        return source_labels.get(self.source, self.source.value)


# ---------------------------------------------------------------------------
# Permission Decision Reason
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PermissionDecisionReason:
    """Explanation of why a permission decision was made.

    Mirrors Claude Code's PermissionDecisionReason discriminated union.
    """

    reason_type: str  # "rule" | "mode" | "safety_check" | "hook" | "working_dir" | "classifier" | "other"
    reason: str
    rule: PermissionRule | None = None
    mode: PermissionMode | None = None
    classifier_approvable: bool = True  # For safety checks, whether classifier can override


# ---------------------------------------------------------------------------
# Permission Result (discriminated union)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PermissionResult:
    """Result of a tool permission check.

    Mirrors Claude Code's PermissionResult discriminated union:
    - { behavior: 'allow', updatedInput?: {...} }
    - { behavior: 'deny', message: string }
    - { behavior: 'ask', message: string, suggestions?: ... }

    Using Python dataclass with optional fields rather than inheritance so
    callers can handle all variants uniformly.
    """

    behavior: PermissionBehavior
    updated_input: dict[str, Any] | None = None
    message: str | None = None
    reason: PermissionDecisionReason | None = None
    suggestions: list[dict[str, Any]] | None = None
    tool_use_id: str | None = None


# ---------------------------------------------------------------------------
# Permission Context (aggregated state for a turn)
# ---------------------------------------------------------------------------


@dataclass
class PermissionContext:
    """Context needed for permission checking in tools.

    Mirrors Claude Code's ToolPermissionContext:
      mode: current permission mode
      additionalWorkingDirectories: expanded set of allowed directories
      alwaysAllowRules: rules grouped by source
      alwaysDenyRules: rules grouped by source
      alwaysAskRules: rules grouped by source
    """

    mode: PermissionMode
    additional_working_directories: dict[str, str] = field(default_factory=dict)
    # Each is a mapping source -> list of rule strings (e.g. ["Bash(git *)"])
    always_allow_rules: dict[RuleSource, list[str]] = field(default_factory=dict)
    always_deny_rules: dict[RuleSource, list[str]] = field(default_factory=dict)
    always_ask_rules: dict[RuleSource, list[str]] = field(default_factory=dict)
    # Whether bypass mode is available (may be disabled by policy/gate)
    is_bypass_available: bool = True
    # Stripped dangerous rules (for auto mode exit restoration)
    stripped_dangerous_rules: dict[RuleSource, list[str]] | None = None
    # Pre-plan mode snapshot (for exiting plan mode)
    pre_plan_mode: PermissionMode | None = None
    # Auto mode availability (for circuit breaker)
    is_auto_available: bool = False


# ---------------------------------------------------------------------------
# Pattern Matching Utilities
# ---------------------------------------------------------------------------


def _pattern_match(pattern: str, text: str) -> bool:
    """Match text against a permission rule pattern.

    Supports:
    - fnmatch wildcards: "git *", "/tmp/*", "*.py"
    - Legacy prefix syntax: "npm:*" → matches anything starting with "npm "
    - Exact match: "npm install"

    This mirrors Claude Code's shell rule matching in shellRuleMatching.ts.
    """
    # Handle legacy :* prefix syntax (convert to wildcard)
    if pattern.endswith(":*"):
        prefix = pattern[:-2]  # Remove ":*"
        return text.startswith(prefix) or text.startswith(f"{prefix} ")

    # Try fnmatch (Unix shell-style wildcards)
    if fnmatch.fnmatch(text, pattern):
        return True

    # Try prefix match (more lenient)
    if text.startswith(pattern.rstrip("*").rstrip()):
        return True

    return False


def parse_rule_string(rule_string: str) -> PermissionRuleValue:
    """Parse a permission rule string into its components.

    Format: "ToolName" or "ToolName(content)"
    Content may contain escaped parentheses: \\( and \\)

    Mirrors Claude Code's permissionRuleValueFromString().

    Examples:
    - "Bash" → PermissionRuleValue(tool_name="Bash")
    - "Bash(npm install)" → PermissionRuleValue(tool_name="Bash", rule_content="npm install")
    - "Bash(python -c \\"print\\\\(1\\)")" → PermissionRuleValue(tool_name="Bash", rule_content='python -c "print(1)"')
    """

    def _unescape(content: str) -> str:
        return (
            content.replace("\\(", "(").replace("\\)", ")").replace("\\\\", "\\")
        )

    open_paren = _find_unescaped(pattern=rule_string, char="(")
    if open_paren == -1:
        return PermissionRuleValue(tool_name=rule_string)

    close_paren = _find_unescaped(pattern=rule_string, char=")", reverse=True)
    if close_paren == -1 or close_paren <= open_paren:
        return PermissionRuleValue(tool_name=rule_string)

    if close_paren != len(rule_string) - 1:
        return PermissionRuleValue(tool_name=rule_string)

    tool_name = rule_string[:open_paren]
    raw_content = rule_string[open_paren + 1 : close_paren]

    if not tool_name:
        return PermissionRuleValue(tool_name=rule_string)

    # Empty content or standalone wildcard = tool-wide rule
    if raw_content == "" or raw_content == "*":
        return PermissionRuleValue(tool_name=tool_name)

    return PermissionRuleValue(tool_name=tool_name, rule_content=_unescape(raw_content))


def rule_value_to_string(rule_value: PermissionRuleValue) -> str:
    """Convert a rule value back to its string representation.

    Mirrors Claude Code's permissionRuleValueToString().
    """
    if not rule_value.rule_content:
        return rule_value.tool_name

    def _escape(content: str) -> str:
        return (
            content.replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
        )

    return f"{rule_value.tool_name}({_escape(rule_value.rule_content)})"


def _find_unescaped(pattern: str, char: str, reverse: bool = False) -> int:
    """Find the first/last unescaped occurrence of a character.

    A character is escaped if preceded by an odd number of backslashes.
    """
    indices = range(len(pattern) - 1, -1, -1) if reverse else range(len(pattern))
    for i in indices:
        if pattern[i] == char:
            backslash_count = 0
            j = i - 1
            while j >= 0 and pattern[j] == "\\":
                backslash_count += 1
                j -= 1
            if backslash_count % 2 == 0:
                return i
    return -1