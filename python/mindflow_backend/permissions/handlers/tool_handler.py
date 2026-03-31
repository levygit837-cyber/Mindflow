"""Tool permission handler — generic permission checking for all tool types.

Mirrors Claude Code's tool checkPermissions() integration:
- Extracts relevant content from tool input for pattern matching
- Applies permission rules (deny → ask → allow)
- Returns structured PermissionResult with reason chain

This handler is designed to be composed with tools via the
PermissionCheckProtocol, so each tool can delegate to it or override.
"""

from __future__ import annotations

import logging
from typing import Any

from mindflow_backend.permissions.types import (
    PermissionBehavior,
    PermissionContext,
    PermissionDecisionReason,
    PermissionMode,
    PermissionResult,
    PermissionRule,
    RuleSource,
    parse_rule_string,
)

logger = logging.getLogger(__name__)

# Path keys commonly used in tool inputs to extract content for matching
_COMMON_CONTENT_KEYS = (
    "path",
    "file_path",
    "filepath",
    "command",
    "query",
    "content",
    "input",
    "args",
    "arguments",
)


class ToolPermissionHandler:
    """Extract content from tool input and match against permission rules.

    This is the core of Claude Code's permission flow: each tool's
    checkPermissions() delegates to this handler for rule-based decisions.

    Usage:
        handler = ToolPermissionHandler()
        result = await handler.check(tool_name, tool_input, context)
    """

    def __init__(self) -> None:
        self._content_extractors: dict[str, list[str]] = {}

    def register_content_keys(
        self, tool_name: str, keys: tuple[str, ...]
    ) -> None:
        """Register which input keys contain permission-relevant content.

        If not registered, defaults to _COMMON_CONTENT_KEYS.

        Example:
            handler.register_content_keys("Bash", ("command",))
            handler.register_content_keys("FileRead", ("path", "file_path"))
        """
        self._content_extractors[tool_name] = list(keys)

    def extract_tool_content(self, tool_name: str, input: dict[str, Any]) -> str | None:
        """Extract content string from tool input for rule matching.

        E.g. for Bash: input["command"] = "git commit -m 'fix'"
        E.g. for FileRead: input["path"] = "/etc/passwd"
        """
        keys = self._content_extractors.get(tool_name, list(_COMMON_CONTENT_KEYS))

        for key in keys:
            value = input.get(key)
            if value is not None:
                if isinstance(value, str):
                    return value
                if isinstance(value, (list, dict)):
                    # For complex input, serialize for content matching
                    import json

                    return json.dumps(value, default=str)
        return None

    def check(
        self,
        tool_name: str,
        input: dict[str, Any],
        context: PermissionContext,
    ) -> PermissionResult:
        """Check permissions for a tool invocation using rule matching.

        Implements Claude Code's permission pipeline for tool-specific checks:
        1. Check deny rules that match tool+content
        2. Check ask rules that match tool+content
        3. Check allow rules that match tool+content
        4. Return passthrough if no rule matches (let manager decide)

        Returns:
            PermissionResult with behavior matching a found rule,
            or {behavior: ALLOW} if no rules match (passthrough to manager).
        """
        content = self.extract_tool_content(tool_name, input)

        # -- Step 1: Content-specific deny rules --
        deny_rule = self._find_matching_rule(
            context.always_deny_rules, tool_name, content
        )
        if deny_rule:
            return self._deny(
                f"{tool_name} operation denied by rule: {deny_rule.display_string} ({deny_rule.source_display})",
                deny_rule,
            )

        # -- Step 2: Content-specific ask rules --
        ask_rule = self._find_matching_rule(
            context.always_ask_rules, tool_name, content
        )
        if ask_rule:
            if context.mode == PermissionMode.BYPASS:
                return self._allow()
            return self._ask(
                f"{tool_name} requires approval: {ask_rule.display_string}",
                ask_rule,
            )

        # -- Step 3: Content-specific allow rules --
        allow_rule = self._find_matching_rule(
            context.always_allow_rules, tool_name, content
        )
        if allow_rule:
            return self._allow(allow_rule)

        # No matching rule → passthrough to manager's default behavior
        return PermissionResult(behavior=PermissionBehavior.ALLOW)

    # ------------------------------------------------------------------
    # Rule matching with content awareness
    # ------------------------------------------------------------------

    def _find_matching_rule(
        self,
        rules_by_source: dict[RuleSource, list[str]],
        tool_name: str,
        content: str | None,
    ) -> PermissionRule | None:
        """Find a rule that matches tool+content.

        Priority:
        1. Content-specific rules that match (e.g. "Bash(git *)" matches "git commit")
        2. Tool-wide rules (e.g. "Bash" matches any Bash invocation)
        """
        # First pass: content-specific rules
        if content is not None:
            for source, rule_strings in rules_by_source.items():
                for rule_str in rule_strings:
                    rv = parse_rule_string(rule_str)
                    if rv.tool_name != tool_name:
                        continue
                    if rv.rule_content and rv.matches(tool_name, content):
                        return PermissionRule(
                            source=source,
                            rule_behavior=PermissionBehavior.ALLOW,
                            rule_value=rv,
                        )

        # Second pass: tool-wide rules (no rule_content)
        for source, rule_strings in rules_by_source.items():
            for rule_str in rule_strings:
                rv = parse_rule_string(rule_str)
                if rv.tool_name != tool_name and rv.rule_content is None:
                    continue
                if rv.rule_content is None:
                    return PermissionRule(
                        source=source,
                        rule_behavior=PermissionBehavior.ALLOW,
                        rule_value=rv,
                    )

        return None

    # ------------------------------------------------------------------
    # Result builders
    # ------------------------------------------------------------------

    def _allow(self, rule: PermissionRule | None = None) -> PermissionResult:
        reason = None
        if rule:
            reason = PermissionDecisionReason(
                reason_type="rule",
                rule=rule,
                reason=f"Allowed by {rule.display_string}",
            )
        return PermissionResult(behavior=PermissionBehavior.ALLOW, reason=reason)

    def _deny(self, message: str, rule: PermissionRule) -> PermissionResult:
        reason = PermissionDecisionReason(
            reason_type="rule",
            rule=rule,
            reason=message,
            classifier_approvable=False,
        )
        return PermissionResult(
            behavior=PermissionBehavior.DENY,
            message=message,
            reason=reason,
        )

    def _ask(self, message: str, rule: PermissionRule) -> PermissionResult:
        reason = PermissionDecisionReason(
            reason_type="rule",
            rule=rule,
            reason=message,
            classifier_approvable=True,
        )
        return PermissionResult(
            behavior=PermissionBehavior.ASK,
            message=message,
            reason=reason,
        )