"""Permission matching system for MindFlow backend.

Implements wildcard pattern matching and rule evaluation for the
permission system, matching Claude Code's granular permission control.
"""

from __future__ import annotations

import fnmatch
import time
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools.tool_permissions import (
    PermissionBehavior,
    PermissionContext,
    PermissionDecision,
    PermissionRule,
    PermissionRuleSet,
    PermissionRuleType,
)

_logger = get_logger(__name__)


# ============================================================================
# Wildcard Pattern Matching
# ============================================================================

def match_wildcard_pattern(pattern: str, text: str, case_sensitive: bool = True) -> bool:
    """Match text against wildcard pattern.

    Supports:
    - * (matches any sequence of characters)
    - ? (matches any single character)
    - [abc] (matches any character in set)
    - [!abc] (matches any character not in set)

    Examples:
        match_wildcard_pattern("git *", "git status") -> True
        match_wildcard_pattern("rm -rf *", "rm -rf /") -> True
        match_wildcard_pattern("*.py", "main.py") -> True
    """
    if not case_sensitive:
        pattern = pattern.lower()
        text = text.lower()

    return fnmatch.fnmatch(text, pattern)


def match_any_pattern(patterns: list[str], text: str, case_sensitive: bool = True) -> bool:
    """Check if text matches any of the patterns."""
    return any(match_wildcard_pattern(p, text, case_sensitive) for p in patterns)


# ============================================================================
# Rule Matching
# ============================================================================

def match_rule(rule: PermissionRule, context: PermissionContext) -> bool:
    """Check if a permission rule matches the given context.

    Args:
        rule: Permission rule to match
        context: Context to match against

    Returns:
        True if rule matches context
    """
    if not rule.enabled:
        return False

    # Match based on rule type
    if rule.rule_type == PermissionRuleType.COMMAND:
        # Match against command
        if context.command:
            return match_wildcard_pattern(rule.pattern, context.command)
        return False

    elif rule.rule_type == PermissionRuleType.PATH:
        # Match against file path
        if context.file_path:
            return match_wildcard_pattern(rule.pattern, context.file_path)
        return False

    elif rule.rule_type == PermissionRuleType.TOOL:
        # Match against tool name
        return match_wildcard_pattern(rule.pattern, context.tool_name)

    elif rule.rule_type == PermissionRuleType.OPERATION:
        # Match against operation type
        if context.operation:
            return match_wildcard_pattern(rule.pattern, context.operation)
        return False

    return False


# ============================================================================
# Rule Evaluation
# ============================================================================

class PermissionEvaluator:
    """Evaluates permission rules against context."""

    def __init__(self, rule_set: PermissionRuleSet):
        """Initialize evaluator with rule set.

        Args:
            rule_set: Permission rule set to use
        """
        self.rule_set = rule_set
        self._cache: dict[str, tuple[PermissionDecision, float]] = {}
        self._cache_ttl = 300  # 5 minutes

    def evaluate(self, context: PermissionContext, use_cache: bool = True) -> PermissionDecision:
        """Evaluate permission rules against context.

        Args:
            context: Context to evaluate
            use_cache: Whether to use cached decisions

        Returns:
            Permission decision
        """
        # Generate cache key
        cache_key = self._generate_cache_key(context)

        # Check cache
        if use_cache and cache_key in self._cache:
            decision, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                _logger.debug(f"Permission cache hit: {cache_key}")
                return decision

        # Evaluate rules
        decision = self._evaluate_rules(context)

        # Cache decision
        if use_cache:
            self._cache[cache_key] = (decision, time.time())

        return decision

    def _evaluate_rules(self, context: PermissionContext) -> PermissionDecision:
        """Evaluate rules against context (no caching)."""
        if not self.rule_set.enabled:
            return PermissionDecision(
                behavior=self.rule_set.default_behavior,
                message="Rule set is disabled"
            )

        # Get sorted rules (by priority, highest first)
        rules = self.rule_set.get_sorted_rules()

        # Evaluate each rule
        for rule in rules:
            if match_rule(rule, context):
                _logger.info(
                    f"Permission rule matched: {rule.rule_id} -> {rule.behavior.value}",
                    extra={
                        "rule_id": rule.rule_id,
                        "behavior": rule.behavior.value,
                        "tool": context.tool_name,
                        "command": context.command[:100] if context.command else None,
                    }
                )

                return PermissionDecision(
                    behavior=rule.behavior,
                    message=rule.reason or f"Matched rule: {rule.rule_id}",
                    reason=rule.reason,
                    matched_rule=rule.rule_id,
                    is_security_check=False
                )

        # No rule matched - use default behavior
        _logger.debug(
            f"No permission rule matched, using default: {self.rule_set.default_behavior.value}",
            extra={"tool": context.tool_name}
        )

        return PermissionDecision(
            behavior=self.rule_set.default_behavior,
            message="No matching rule, using default behavior"
        )

    def _generate_cache_key(self, context: PermissionContext) -> str:
        """Generate cache key from context."""
        parts = [
            context.tool_name,
            context.operation or "",
            context.command or "",
            context.file_path or "",
        ]
        return ":".join(parts)

    def clear_cache(self):
        """Clear permission cache."""
        self._cache.clear()
        _logger.debug("Permission cache cleared")

    def add_rule(self, rule: PermissionRule):
        """Add a rule to the rule set."""
        self.rule_set.add_rule(rule)
        self.clear_cache()  # Clear cache when rules change

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule from the rule set."""
        removed = self.rule_set.remove_rule(rule_id)
        if removed:
            self.clear_cache()  # Clear cache when rules change
        return removed


# ============================================================================
# Combined Permission Check
# ============================================================================

def check_permission(
    context: PermissionContext,
    rule_set: PermissionRuleSet,
    security_validators: list[Any] | None = None,
) -> PermissionDecision:
    """Check permission with both rules and security validators.

    This combines:
    1. Security validators (always run first)
    2. Permission rules (run if validators pass)

    Args:
        context: Permission context
        rule_set: Permission rule set
        security_validators: Optional list of security validator functions

    Returns:
        Permission decision
    """
    # Run security validators first
    if security_validators:
        for validator in security_validators:
            try:
                decision = validator(context)

                # If validator blocks, return immediately
                if decision.behavior in [PermissionBehavior.DENY, PermissionBehavior.ASK]:
                    return decision

            except Exception as e:
                _logger.error(f"Security validator failed: {e}", exc_info=True)
                # Continue to next validator

    # Run permission rules
    evaluator = PermissionEvaluator(rule_set)
    return evaluator.evaluate(context)


# ============================================================================
# Convenience Functions
# ============================================================================

def create_command_rule(
    rule_id: str,
    pattern: str,
    behavior: PermissionBehavior,
    reason: str | None = None,
    priority: int = 0,
) -> PermissionRule:
    """Create a command permission rule."""
    return PermissionRule(
        rule_id=rule_id,
        rule_type=PermissionRuleType.COMMAND,
        pattern=pattern,
        behavior=behavior,
        reason=reason,
        priority=priority
    )


def create_path_rule(
    rule_id: str,
    pattern: str,
    behavior: PermissionBehavior,
    reason: str | None = None,
    priority: int = 0,
) -> PermissionRule:
    """Create a path permission rule."""
    return PermissionRule(
        rule_id=rule_id,
        rule_type=PermissionRuleType.PATH,
        pattern=pattern,
        behavior=behavior,
        reason=reason,
        priority=priority
    )


def create_tool_rule(
    rule_id: str,
    pattern: str,
    behavior: PermissionBehavior,
    reason: str | None = None,
    priority: int = 0,
) -> PermissionRule:
    """Create a tool permission rule."""
    return PermissionRule(
        rule_id=rule_id,
        rule_type=PermissionRuleType.TOOL,
        pattern=pattern,
        behavior=behavior,
        reason=reason,
        priority=priority
    )


# ============================================================================
# Example Usage
# ============================================================================

def create_example_rule_set() -> PermissionRuleSet:
    """Create an example rule set for testing."""
    from mindflow_backend.schemas.tools.tool_permissions import create_default_rule_set

    rule_set = create_default_rule_set()

    # Add custom rules
    rule_set.add_rule(create_command_rule(
        rule_id="allow_pytest",
        pattern="pytest*",
        behavior=PermissionBehavior.ALLOW,
        reason="Allow pytest commands",
        priority=10
    ))

    rule_set.add_rule(create_path_rule(
        rule_id="deny_etc",
        pattern="/etc/*",
        behavior=PermissionBehavior.DENY,
        reason="Cannot access /etc directory",
        priority=100
    ))

    return rule_set


# ============================================================================
# Testing Helpers
# ============================================================================

def test_pattern_matching():
    """Test wildcard pattern matching."""
    test_cases = [
        ("git *", "git status", True),
        ("git *", "ls", False),
        ("rm -rf *", "rm -rf /", True),
        ("*.py", "main.py", True),
        ("*.py", "main.js", False),
        ("/home/*/project", "/home/user/project", True),
        ("/home/*/project", "/home/user/other", False),
    ]

    print("Testing wildcard pattern matching:")
    for pattern, text, expected in test_cases:
        result = match_wildcard_pattern(pattern, text)
        status = "✓" if result == expected else "✗"
        print(f"  {status} match_wildcard_pattern('{pattern}', '{text}') = {result} (expected {expected})")


if __name__ == "__main__":
    test_pattern_matching()
