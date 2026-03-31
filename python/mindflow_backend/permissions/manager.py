"""PermissionManager — central permission checking with circuit breaker.

Mirrors Claude Code's permission pipeline (src/utils/permissions/permissions.ts):
  1. Check tool-wide deny rules
  2. Check tool-wide ask rules
  3. Check mode-based decisions (bypass, don'tAsk, auto)
  4. Check tool-specific permissions (via tool.check_permissions)
  5. Check allow rules
  6. Default to asking user

The circuit breaker (from mindflow_backend.infra.resilience) prevents
cascading failures if the permission system itself becomes unhealthy.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from mindflow_backend.infra.resilience.circuit_breaker import CircuitBreaker

from mindflow_backend.permissions.types import (
    PermissionBehavior,
    PermissionContext,
    PermissionDecisionReason,
    PermissionMode,
    PermissionResult,
    PermissionRule,
    PermissionRuleValue,
    RuleSource,
    parse_rule_string,
    rule_value_to_string,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool Permission Check Protocol
# ---------------------------------------------------------------------------


class PermissionCheckProtocol:
    """Protocol for tools that implement custom permission checking.

    Similar to Claude Code's tool.checkPermissions(). Tools can implement
    this to provide input-aware permission decisions (e.g. Bash checking
    specific commands, FileRead checking specific paths).

    Usage:
      class MyTool(PermissionCheckProtocol):
          async def check_permissions(self, input, context) -> PermissionResult:
              if input.get("path", "").startswith("/etc/"):
                  return PermissionResult(
                      behavior=PermissionBehavior.ASK,
                      message="Reading /etc/ requires approval",
                  )
              return PermissionResult(behavior=PermissionBehavior.ALLOW)
    """

    async def check_permissions(
        self, input: dict[str, Any], context: Any
    ) -> PermissionResult:
        """Check permissions for a specific tool invocation.

        Args:
            input: Validated tool input
            context: Tool execution context

        Returns:
            PermissionResult with behavior-specific fields
        """
        # Default: passthrough to standard permission checking
        return PermissionResult(behavior=PermissionBehavior.ALLOW)


# ---------------------------------------------------------------------------
# Permission Manager
# ---------------------------------------------------------------------------


@dataclass
class PermissionManagerConfig:
    """Configuration for PermissionManager."""

    # Whether to use the circuit breaker for permission checks
    use_circuit_breaker: bool = True
    # Circuit breaker failure threshold before opening
    circuit_breaker_failure_threshold: int = 5
    # Circuit breaker recovery timeout (seconds)
    circuit_breaker_recovery_timeout: float = 60.0
    # Whether to log permission decisions
    log_decisions: bool = True
    # Default mode when context doesn't specify
    default_mode: PermissionMode = PermissionMode.DEFAULT


class PermissionManager:
    """Central permission checking with circuit breaker.

    Mirrors Claude Code's hasPermissionsToUseTool() from permissions.ts.

    Evaluation order (fail-fast):
      1. Tool-wide DENY rules → immediate deny
      2. Tool-wide ASK rules → immediate ask (unless bypass mode)
      3. Mode-based decisions:
         - BYPASS: allow all (except safety checks from tool)
         - DONT_ASK: deny all that would prompt
         - ACCEPT_EDITS: allow in working directory
         - AUTO: use classifier (future)
      4. Tool.check_permissions() → tool-specific logic
      5. Tool-wide ALLOW rules → allow
      6. Default: ask for approval

    Thread-safe: Uses circuit breaker for resilience.
    """

    def __init__(self, config: PermissionManagerConfig | None = None) -> None:
        self._config = config or PermissionManagerConfig()
        self._circuit_breaker: CircuitBreaker | None = None

        if self._config.use_circuit_breaker:
            self._circuit_breaker = CircuitBreaker(
                name="permission-manager",
                failure_threshold=self._config.circuit_breaker_failure_threshold,
                recovery_timeout=self._config.circuit_breaker_recovery_timeout,
            )

    async def check_permission(
        self,
        tool_name: str,
        input: dict[str, Any],
        context: PermissionContext,
        tool_proto: PermissionCheckProtocol | None = None,
        tool_use_id: str | None = None,
        tool_content: str | None = None,
    ) -> PermissionResult:
        """Check if a tool invocation is permitted.

        Args:
            tool_name: Name of the tool being invoked
            input: Validated tool input
            context: Current permission context
            tool_proto: Optional tool implementing check_permissions()
            tool_use_id: Unique ID for this tool use (for audit logging)
            tool_content: Extracted content/args for pattern matching
                          (e.g. "git commit" for Bash, "/etc/passwd" for FileRead)

        Returns:
            PermissionResult indicating allow, deny, or ask
        """
        if self._circuit_breaker:
            return await self._circuit_breaker.execute_async(
                lambda: self._check_permission_inner(
                    tool_name, input, context, tool_proto, tool_use_id, tool_content
                )
            )
        return await self._check_permission_inner(
            tool_name, input, context, tool_proto, tool_use_id, tool_content
        )

    async def _check_permission_inner(
        self,
        tool_name: str,
        input: dict[str, Any],
        context: PermissionContext,
        tool_proto: PermissionCheckProtocol | None = None,
        tool_use_id: str | None = None,
        tool_content: str | None = None,
    ) -> PermissionResult:
        """Inner permission check — executed within circuit breaker."""
        mode = context.mode

        # -- Step 1: Tool-wide deny rules --
        deny_rule = self._find_rule_for_tool(
            context.always_deny_rules, tool_name, tool_content
        )
        if deny_rule:
            return self._deny(
                f"Permission to use {tool_name} has been denied by {deny_rule.display_string} ({deny_rule.source_display}).",
                reason_type="rule",
                rule=deny_rule,
                tool_use_id=tool_use_id,
            )

        # -- Step 2: Tool-wide ask rules --
        ask_rule = self._find_rule_for_tool(
            context.always_ask_rules, tool_name, tool_content
        )
        if ask_rule:
            # In bypass mode, skip ask rules
            if mode == PermissionMode.BYPASS:
                return self._allow(input, reason_type="mode", mode=mode)
            return self._ask(
                f"{tool_name} requires approval per policy: {ask_rule.display_string} ({ask_rule.source_display}).",
                reason_type="rule",
                rule=ask_rule,
                tool_use_id=tool_use_id,
            )

        # -- Step 3: Mode-based decisions --
        if mode == PermissionMode.BYPASS:
            return self._allow(
                input, reason_type="mode", mode=mode, tool_use_id=tool_use_id
            )

        if mode == PermissionMode.DONT_ASK:
            return self._deny(
                f"Tool {tool_name} denied — mode is 'dont_ask'.",
                reason_type="mode",
                mode=mode,
                tool_use_id=tool_use_id,
            )

        # -- Step 4: Tool-specific permission check --
        if tool_proto is not None:
            tool_result = await tool_proto.check_permissions(input, context)
            if tool_result.behavior == PermissionBehavior.DENY:
                return tool_result
            # If tool returned ask with safety_check reason, respect it
            if tool_result.behavior == PermissionBehavior.ASK and tool_result.reason:
                if tool_result.reason.reason_type == "safety_check":
                    return tool_result

        # -- Step 5: Bypass for ACCEPT_EDITS in working directory --
        if mode == PermissionMode.ACCEPT_EDITS:
            # Allow if input is within working directory
            # (Working directory check delegated to tool.check_permissions)
            # If tool allowed it, fall-through to allow rules
            pass

        # -- Step 6: Tool-wide allow rules --
        allow_rule = self._find_rule_for_tool(
            context.always_allow_rules, tool_name, tool_content
        )
        if allow_rule:
            return self._allow(
                input,
                reason_type="rule",
                rule=allow_rule,
                updated_input=input,
                tool_use_id=tool_use_id,
            )

        # -- Step 7: Default to asking --
        return self._ask(
            f"{tool_name} requires approval. Current mode: {mode.value}.",
            reason_type="mode",
            mode=mode,
            tool_use_id=tool_use_id,
        )

    # ------------------------------------------------------------------
    # Rule matching (adapted from Claude Code's getRuleByContentsForTool)
    # ------------------------------------------------------------------

    def _find_rule_for_tool(
        self,
        rules_by_source: dict[RuleSource, list[str]],
        tool_name: str,
        tool_content: str | None = None,
    ) -> PermissionRule | None:
        """Find a matching rule for the given tool+content across all sources.

        Checks both:
        - Tool-wide rules (e.g. "Bash" with no content → matches ALL Bash)
        - Content-specific rules (e.g. "Bash(git *)" → matches Bash with "git commit")
        """
        for source, rule_strings in rules_by_source.items():
            for rule_str in rule_strings:
                rv = parse_rule_string(rule_str)
                if rv.tool_name != tool_name:
                    continue

                # Tool-wide rule: matches regardless of content
                if rv.rule_content is None:
                    return PermissionRule(
                        source=source,
                        rule_behavior=PermissionBehavior.ALLOW,  # caller sets via collection
                        rule_value=rv,
                    )

                # Content-specific rule: check if it matches actual tool content
                if tool_content is not None:
                    if rv.matches(tool_name, tool_content):
                        return PermissionRule(
                            source=source,
                            rule_behavior=PermissionBehavior.ALLOW,
                            rule_value=rv,
                        )
        return None

    # ------------------------------------------------------------------
    # Result builders
    # ------------------------------------------------------------------

    def _allow(
        self,
        updated_input: dict[str, Any],
        reason_type: str = "mode",
        rule: PermissionRule | None = None,
        mode: PermissionMode | None = None,
        tool_use_id: str | None = None,
    ) -> PermissionResult:
        reason = PermissionDecisionReason(
            reason_type=reason_type,
            rule=rule,
            reason="Allowed by permission policy",
            mode=mode,
        )
        return PermissionResult(
            behavior=PermissionBehavior.ALLOW,
            updated_input=updated_input,
            reason=reason,
            tool_use_id=tool_use_id,
        )

    def _deny(
        self,
        message: str,
        reason_type: str = "rule",
        rule: PermissionRule | None = None,
        mode: PermissionMode | None = None,
        tool_use_id: str | None = None,
    ) -> PermissionResult:
        reason = PermissionDecisionReason(
            reason_type=reason_type,
            rule=rule,
            reason=message,
            mode=mode,
        )
        return PermissionResult(
            behavior=PermissionBehavior.DENY,
            message=message,
            reason=reason,
            tool_use_id=tool_use_id,
        )

    def _ask(
        self,
        message: str,
        reason_type: str = "mode",
        rule: PermissionRule | None = None,
        mode: PermissionMode | None = None,
        suggestions: list[dict[str, Any]] | None = None,
        tool_use_id: str | None = None,
    ) -> PermissionResult:
        reason = PermissionDecisionReason(
            reason_type=reason_type,
            rule=rule,
            reason=message,
            mode=mode,
        )
        return PermissionResult(
            behavior=PermissionBehavior.ASK,
            message=message,
            reason=reason,
            suggestions=suggestions,
            tool_use_id=tool_use_id,
        )