"""Tests for HookMatcher pattern matching."""

from __future__ import annotations

import pytest

from mindflow_backend.hooks.matcher import HookMatcher


class TestHookMatcher:
    """Tests for HookMatcher.matches()."""

    def test_match_all_with_none(self) -> None:
        """None pattern matches everything."""
        assert HookMatcher.matches("Write", None)
        assert HookMatcher.matches("Edit", None)
        assert HookMatcher.matches("Bash", None)
        assert HookMatcher.matches("read_file", None)

    def test_match_all_with_wildcard(self) -> None:
        """Wildcard * matches everything."""
        assert HookMatcher.matches("Write", "*")
        assert HookMatcher.matches("Edit", "*")
        assert HookMatcher.matches("Bash", "*")

    def test_exact_match(self) -> None:
        """Exact string match."""
        assert HookMatcher.matches("Write", "Write")
        assert HookMatcher.matches("Edit", "Edit")
        assert HookMatcher.matches("Bash", "Bash")
        assert HookMatcher.matches("read_file", "read_file")

    def test_exact_match_fails(self) -> None:
        """Exact match fails for different strings."""
        assert not HookMatcher.matches("Write", "Edit")
        assert not HookMatcher.matches("Bash", "Write")
        assert not HookMatcher.matches("read_file", "write_file")

    def test_pipe_separated_match(self) -> None:
        """Pipe-separated OR matches any of the options."""
        pattern = "Write|Edit|Read"
        assert HookMatcher.matches("Write", pattern)
        assert HookMatcher.matches("Edit", pattern)
        assert HookMatcher.matches("Read", pattern)

    def test_pipe_separated_no_match(self) -> None:
        """Pipe-separated OR doesn't match other strings."""
        pattern = "Write|Edit|Read"
        assert not HookMatcher.matches("Bash", pattern)
        assert not HookMatcher.matches("Delete", pattern)
        assert not HookMatcher.matches("read_file", pattern)

    def test_pipe_separated_with_spaces(self) -> None:
        """Pipe-separated with spaces around pipes."""
        pattern = "Write | Edit | Read"
        # Should NOT match because spaces make it not match the simple pattern regex
        # It will fall through to regex matching, which won't match
        assert not HookMatcher.matches("Write", pattern)

    def test_regex_pattern_prefix(self) -> None:
        """Regex pattern with prefix match."""
        assert HookMatcher.matches("Bash", "^Bash.*")
        assert HookMatcher.matches("BashCommand", "^Bash.*")
        assert HookMatcher.matches("BashTool", "^Bash.*")
        assert not HookMatcher.matches("Write", "^Bash.*")

    def test_regex_pattern_suffix(self) -> None:
        """Regex pattern with suffix match."""
        assert HookMatcher.matches("read_file", ".*file$")
        assert HookMatcher.matches("write_file", ".*file$")
        assert not HookMatcher.matches("file_reader", ".*file$")

    def test_regex_pattern_contains(self) -> None:
        """Regex pattern with contains match."""
        assert HookMatcher.matches("read_file", ".*file.*")
        assert HookMatcher.matches("file_reader", ".*file.*")
        assert HookMatcher.matches("my_file_tool", ".*file.*")
        assert not HookMatcher.matches("reader", ".*file.*")

    def test_regex_pattern_complex(self) -> None:
        """Complex regex patterns."""
        # Match Write or Edit
        assert HookMatcher.matches("Write", "^(Write|Edit)$")
        assert HookMatcher.matches("Edit", "^(Write|Edit)$")
        assert not HookMatcher.matches("Read", "^(Write|Edit)$")

        # Match any tool ending with _file
        assert HookMatcher.matches("read_file", "^[a-z]+_file$")
        assert HookMatcher.matches("write_file", "^[a-z]+_file$")
        assert not HookMatcher.matches("ReadFile", "^[a-z]+_file$")

    def test_invalid_regex_returns_false(self) -> None:
        """Invalid regex pattern returns False and logs error."""
        # Invalid regex patterns
        assert not HookMatcher.matches("Write", "[invalid(")
        assert not HookMatcher.matches("Write", "(?P<incomplete")
        assert not HookMatcher.matches("Write", "*invalid")

    def test_normalize_tool_name_pascal_case(self) -> None:
        """PascalCase names remain unchanged."""
        assert HookMatcher.normalize_tool_name("Write") == "Write"
        assert HookMatcher.normalize_tool_name("Edit") == "Edit"
        assert HookMatcher.normalize_tool_name("BashCommand") == "BashCommand"

    def test_normalize_tool_name_snake_case(self) -> None:
        """snake_case names convert to PascalCase."""
        assert HookMatcher.normalize_tool_name("read_file") == "ReadFile"
        assert HookMatcher.normalize_tool_name("write_file") == "WriteFile"
        assert HookMatcher.normalize_tool_name("grep_search") == "GrepSearch"

    def test_normalize_tool_name_single_word(self) -> None:
        """Single word lowercase converts to capitalized."""
        assert HookMatcher.normalize_tool_name("bash") == "Bash"
        assert HookMatcher.normalize_tool_name("write") == "Write"

    def test_compile_pattern_valid(self) -> None:
        """Valid patterns compile successfully."""
        pattern = HookMatcher.compile_pattern("^Bash.*")
        assert pattern is not None
        assert pattern.match("Bash")
        assert pattern.match("BashCommand")

    def test_compile_pattern_invalid(self) -> None:
        """Invalid patterns return None."""
        assert HookMatcher.compile_pattern("[invalid(") is None
        assert HookMatcher.compile_pattern("(?P<incomplete") is None


class TestHookMatcherEdgeCases:
    """Edge case tests for HookMatcher."""

    def test_empty_query(self) -> None:
        """Empty query string."""
        assert HookMatcher.matches("", "")
        assert not HookMatcher.matches("", "Write")

    def test_empty_pattern(self) -> None:
        """Empty pattern string (should match all)."""
        # Empty string is falsy, so it matches all
        assert HookMatcher.matches("Write", "")

    def test_case_sensitive_matching(self) -> None:
        """Matching is case-sensitive."""
        assert HookMatcher.matches("Write", "Write")
        assert not HookMatcher.matches("write", "Write")
        assert not HookMatcher.matches("WRITE", "Write")

    def test_special_chars_in_tool_name(self) -> None:
        """Tool names with special characters."""
        # These should fall through to regex matching
        assert HookMatcher.matches("tool-name", "tool-name")
        assert HookMatcher.matches("tool.name", "tool\\.name")

    def test_unicode_in_patterns(self) -> None:
        """Unicode characters in patterns."""
        assert HookMatcher.matches("café", "café")
        assert HookMatcher.matches("café", "caf.*")
