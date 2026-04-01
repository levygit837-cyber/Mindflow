"""Unit tests for permission matching system.

Tests wildcard pattern matching, rule evaluation, and permission decisions.
"""

from __future__ import annotations

import pytest

from mindflow_backend.agents.tools.security.permission_matcher import (
    PermissionEvaluator,
    check_permission,
    create_command_rule,
    create_example_rule_set,
    create_path_rule,
    create_tool_rule,
    match_any_pattern,
    match_rule,
    match_wildcard_pattern,
)
from mindflow_backend.schemas.tools.tool_permissions import (
    PermissionBehavior,
    PermissionContext,
    PermissionRule,
    PermissionRuleSet,
    PermissionRuleType,
    create_default_rule_set,
)


class TestWildcardMatching:
    """Test wildcard pattern matching."""

    def test_exact_match(self):
        """Exact matches should work."""
        assert match_wildcard_pattern("git status", "git status") is True
        assert match_wildcard_pattern("git status", "git diff") is False

    def test_star_wildcard(self):
        """* should match any sequence."""
        assert match_wildcard_pattern("git *", "git status") is True
        assert match_wildcard_pattern("git *", "git diff --cached") is True
        assert match_wildcard_pattern("git *", "ls") is False

    def test_question_wildcard(self):
        """? should match single character."""
        assert match_wildcard_pattern("file?.txt", "file1.txt") is True
        assert match_wildcard_pattern("file?.txt", "file12.txt") is False

    def test_character_set(self):
        """[abc] should match characters in set."""
        assert match_wildcard_pattern("file[123].txt", "file1.txt") is True
        assert match_wildcard_pattern("file[123].txt", "file4.txt") is False

    def test_negated_character_set(self):
        """[!abc] should match characters not in set."""
        assert match_wildcard_pattern("file[!123].txt", "file4.txt") is True
        assert match_wildcard_pattern("file[!123].txt", "file1.txt") is False

    def test_case_sensitive(self):
        """Case sensitive matching should work."""
        assert match_wildcard_pattern("Git", "Git", case_sensitive=True) is True
        assert match_wildcard_pattern("Git", "git", case_sensitive=True) is False

    def test_case_insensitive(self):
        """Case insensitive matching should work."""
        assert match_wildcard_pattern("Git", "git", case_sensitive=False) is True
        assert match_wildcard_pattern("GIT", "git", case_sensitive=False) is True

    def test_path_patterns(self):
        """Path patterns should work."""
        assert match_wildcard_pattern("/home/*/project", "/home/user/project") is True
        assert match_wildcard_pattern("/home/*/project", "/home/user/other") is False
        assert match_wildcard_pattern("*.py", "main.py") is True
        assert match_wildcard_pattern("*.py", "main.js") is False

    def test_match_any_pattern(self):
        """match_any_pattern should work."""
        patterns = ["git *", "ls *", "cat *"]
        assert match_any_pattern(patterns, "git status") is True
        assert match_any_pattern(patterns, "ls -la") is True
        assert match_any_pattern(patterns, "rm file") is False


class TestRuleMatching:
    """Test permission rule matching."""

    def test_command_rule_match(self):
        """Command rules should match commands."""
        rule = PermissionRule(
            rule_id="test",
            rule_type=PermissionRuleType.COMMAND,
            pattern="git *",
            behavior=PermissionBehavior.ALLOW
        )

        context = PermissionContext(
            tool_name="shell_execute",
            command="git status"
        )

        assert match_rule(rule, context) is True

    def test_command_rule_no_match(self):
        """Command rules should not match non-matching commands."""
        rule = PermissionRule(
            rule_id="test",
            rule_type=PermissionRuleType.COMMAND,
            pattern="git *",
            behavior=PermissionBehavior.ALLOW
        )

        context = PermissionContext(
            tool_name="shell_execute",
            command="ls -la"
        )

        assert match_rule(rule, context) is False

    def test_path_rule_match(self):
        """Path rules should match paths."""
        rule = PermissionRule(
            rule_id="test",
            rule_type=PermissionRuleType.PATH,
            pattern="/home/*",
            behavior=PermissionBehavior.ALLOW
        )

        context = PermissionContext(
            tool_name="read_file",
            file_path="/home/user/file.txt"
        )

        assert match_rule(rule, context) is True

    def test_tool_rule_match(self):
        """Tool rules should match tool names."""
        rule = PermissionRule(
            rule_id="test",
            rule_type=PermissionRuleType.TOOL,
            pattern="*_file",
            behavior=PermissionBehavior.ALLOW
        )

        context = PermissionContext(
            tool_name="read_file"
        )

        assert match_rule(rule, context) is True

    def test_operation_rule_match(self):
        """Operation rules should match operations."""
        rule = PermissionRule(
            rule_id="test",
            rule_type=PermissionRuleType.OPERATION,
            pattern="read",
            behavior=PermissionBehavior.ALLOW
        )

        context = PermissionContext(
            tool_name="read_file",
            operation="read"
        )

        assert match_rule(rule, context) is True

    def test_disabled_rule(self):
        """Disabled rules should not match."""
        rule = PermissionRule(
            rule_id="test",
            rule_type=PermissionRuleType.COMMAND,
            pattern="git *",
            behavior=PermissionBehavior.ALLOW,
            enabled=False
        )

        context = PermissionContext(
            tool_name="shell_execute",
            command="git status"
        )

        assert match_rule(rule, context) is False


class TestPermissionEvaluator:
    """Test permission evaluator."""

    def test_allow_rule(self):
        """Allow rules should allow."""
        rule_set = PermissionRuleSet(
            name="test",
            rules=[
                create_command_rule(
                    "allow_git",
                    "git *",
                    PermissionBehavior.ALLOW,
                    priority=10
                )
            ]
        )

        evaluator = PermissionEvaluator(rule_set)
        context = PermissionContext(
            tool_name="shell_execute",
            command="git status"
        )

        decision = evaluator.evaluate(context)
        assert decision.behavior == PermissionBehavior.ALLOW
        assert decision.matched_rule == "allow_git"

    def test_deny_rule(self):
        """Deny rules should deny."""
        rule_set = PermissionRuleSet(
            name="test",
            rules=[
                create_command_rule(
                    "deny_rm",
                    "rm -rf *",
                    PermissionBehavior.DENY,
                    priority=100
                )
            ]
        )

        evaluator = PermissionEvaluator(rule_set)
        context = PermissionContext(
            tool_name="shell_execute",
            command="rm -rf /"
        )

        decision = evaluator.evaluate(context)
        assert decision.behavior == PermissionBehavior.DENY
        assert decision.matched_rule == "deny_rm"

    def test_ask_rule(self):
        """Ask rules should ask."""
        rule_set = PermissionRuleSet(
            name="test",
            rules=[
                create_command_rule(
                    "ask_sudo",
                    "sudo *",
                    PermissionBehavior.ASK,
                    priority=50
                )
            ]
        )

        evaluator = PermissionEvaluator(rule_set)
        context = PermissionContext(
            tool_name="shell_execute",
            command="sudo apt install"
        )

        decision = evaluator.evaluate(context)
        assert decision.behavior == PermissionBehavior.ASK
        assert decision.matched_rule == "ask_sudo"

    def test_priority_ordering(self):
        """Higher priority rules should be evaluated first."""
        rule_set = PermissionRuleSet(
            name="test",
            rules=[
                create_command_rule(
                    "low_priority",
                    "git *",
                    PermissionBehavior.DENY,
                    priority=1
                ),
                create_command_rule(
                    "high_priority",
                    "git status",
                    PermissionBehavior.ALLOW,
                    priority=100
                )
            ]
        )

        evaluator = PermissionEvaluator(rule_set)
        context = PermissionContext(
            tool_name="shell_execute",
            command="git status"
        )

        decision = evaluator.evaluate(context)
        # High priority rule should match first
        assert decision.behavior == PermissionBehavior.ALLOW
        assert decision.matched_rule == "high_priority"

    def test_default_behavior(self):
        """Default behavior should be used when no rule matches."""
        rule_set = PermissionRuleSet(
            name="test",
            rules=[],
            default_behavior=PermissionBehavior.ASK
        )

        evaluator = PermissionEvaluator(rule_set)
        context = PermissionContext(
            tool_name="shell_execute",
            command="unknown command"
        )

        decision = evaluator.evaluate(context)
        assert decision.behavior == PermissionBehavior.ASK

    def test_caching(self):
        """Permission decisions should be cached."""
        rule_set = PermissionRuleSet(
            name="test",
            rules=[
                create_command_rule(
                    "allow_git",
                    "git *",
                    PermissionBehavior.ALLOW
                )
            ]
        )

        evaluator = PermissionEvaluator(rule_set)
        context = PermissionContext(
            tool_name="shell_execute",
            command="git status"
        )

        # First evaluation
        decision1 = evaluator.evaluate(context, use_cache=True)

        # Second evaluation (should use cache)
        decision2 = evaluator.evaluate(context, use_cache=True)

        assert decision1.behavior == decision2.behavior
        assert decision1.matched_rule == decision2.matched_rule

    def test_cache_clearing(self):
        """Cache should be clearable."""
        rule_set = PermissionRuleSet(
            name="test",
            rules=[
                create_command_rule(
                    "allow_git",
                    "git *",
                    PermissionBehavior.ALLOW
                )
            ]
        )

        evaluator = PermissionEvaluator(rule_set)
        context = PermissionContext(
            tool_name="shell_execute",
            command="git status"
        )

        # Evaluate and cache
        evaluator.evaluate(context, use_cache=True)

        # Clear cache
        evaluator.clear_cache()

        # Cache should be empty
        assert len(evaluator._cache) == 0


class TestDefaultRuleSet:
    """Test default rule set."""

    def test_default_rules_exist(self):
        """Default rule set should have rules."""
        rule_set = create_default_rule_set()
        assert len(rule_set.rules) > 0

    def test_deny_rm_rf_root(self):
        """Default rules should deny rm -rf /."""
        rule_set = create_default_rule_set()
        evaluator = PermissionEvaluator(rule_set)

        context = PermissionContext(
            tool_name="shell_execute",
            command="rm -rf /"
        )

        decision = evaluator.evaluate(context)
        assert decision.behavior == PermissionBehavior.DENY

    def test_allow_git_status(self):
        """Default rules should allow git status."""
        rule_set = create_default_rule_set()
        evaluator = PermissionEvaluator(rule_set)

        context = PermissionContext(
            tool_name="shell_execute",
            command="git status"
        )

        decision = evaluator.evaluate(context)
        assert decision.behavior == PermissionBehavior.ALLOW

    def test_ask_sudo(self):
        """Default rules should ask for sudo."""
        rule_set = create_default_rule_set()
        evaluator = PermissionEvaluator(rule_set)

        context = PermissionContext(
            tool_name="shell_execute",
            command="sudo apt install"
        )

        decision = evaluator.evaluate(context)
        assert decision.behavior == PermissionBehavior.ASK


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_create_command_rule(self):
        """create_command_rule should work."""
        rule = create_command_rule(
            "test",
            "git *",
            PermissionBehavior.ALLOW,
            "Allow git commands",
            10
        )

        assert rule.rule_id == "test"
        assert rule.rule_type == PermissionRuleType.COMMAND
        assert rule.pattern == "git *"
        assert rule.behavior == PermissionBehavior.ALLOW
        assert rule.reason == "Allow git commands"
        assert rule.priority == 10

    def test_create_path_rule(self):
        """create_path_rule should work."""
        rule = create_path_rule(
            "test",
            "/home/*",
            PermissionBehavior.ALLOW
        )

        assert rule.rule_type == PermissionRuleType.PATH

    def test_create_tool_rule(self):
        """create_tool_rule should work."""
        rule = create_tool_rule(
            "test",
            "*_file",
            PermissionBehavior.ALLOW
        )

        assert rule.rule_type == PermissionRuleType.TOOL


class TestRealWorldScenarios:
    """Test real-world permission scenarios."""

    def test_git_workflow(self):
        """Test typical git workflow permissions."""
        rule_set = create_default_rule_set()
        evaluator = PermissionEvaluator(rule_set)

        # Read-only git commands should be allowed
        for command in ["git status", "git diff", "git log"]:
            context = PermissionContext(
                tool_name="shell_execute",
                command=command
            )
            decision = evaluator.evaluate(context)
            assert decision.behavior == PermissionBehavior.ALLOW

        # git push should ask
        context = PermissionContext(
            tool_name="shell_execute",
            command="git push origin main"
        )
        decision = evaluator.evaluate(context)
        assert decision.behavior == PermissionBehavior.ASK

    def test_file_operations(self):
        """Test file operation permissions."""
        rule_set = PermissionRuleSet(
            name="test",
            rules=[
                create_path_rule(
                    "allow_workspace",
                    "/home/user/workspace/*",
                    PermissionBehavior.ALLOW,
                    priority=10
                ),
                create_path_rule(
                    "deny_etc",
                    "/etc/*",
                    PermissionBehavior.DENY,
                    priority=100
                )
            ]
        )

        evaluator = PermissionEvaluator(rule_set)

        # Workspace files should be allowed
        context = PermissionContext(
            tool_name="read_file",
            file_path="/home/user/workspace/file.txt"
        )
        decision = evaluator.evaluate(context)
        assert decision.behavior == PermissionBehavior.ALLOW

        # /etc files should be denied
        context = PermissionContext(
            tool_name="read_file",
            file_path="/etc/passwd"
        )
        decision = evaluator.evaluate(context)
        assert decision.behavior == PermissionBehavior.DENY


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
