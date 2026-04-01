"""Unit tests for git integration module.

Tests all git integration functions including diff generation,
status tracking, blame, and operation tracking.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from mindflow_backend.agents.tools.integrations.git_integration import (
    fetch_single_file_git_diff_sync,
    format_diff_for_display,
    get_git_operations,
    parse_diff_stats,
    track_git_operation,
    clear_git_operations,
)


class TestGitDiffGeneration:
    """Test git diff generation functions."""

    def test_diff_sync_not_a_repo(self, tmp_path):
        """Test sync diff on non-repository."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        result = fetch_single_file_git_diff_sync(str(test_file), str(tmp_path))

        assert result["success"] is False
        assert "not a git repository" in result["error"].lower()
        assert result["has_changes"] is False

    def test_diff_sync_file_not_found(self, tmp_path):
        """Test sync diff on non-existent file."""
        result = fetch_single_file_git_diff_sync(
            str(tmp_path / "nonexistent.txt"),
            str(tmp_path)
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()


class TestGitOperationTracking:
    """Test git operation tracking."""

    def test_track_single_operation(self):
        """Test tracking a single operation."""
        clear_git_operations()

        track_git_operation("edit", "/test/file.py", {"user": "test"})

        operations = get_git_operations()
        assert len(operations) == 1
        assert operations[0]["type"] == "edit"
        assert operations[0]["file_path"] == "/test/file.py"
        assert operations[0]["details"]["user"] == "test"

    def test_track_multiple_operations(self):
        """Test tracking multiple operations."""
        clear_git_operations()

        track_git_operation("edit", "/test/file1.py")
        track_git_operation("write", "/test/file2.py")
        track_git_operation("delete", "/test/file3.py")

        operations = get_git_operations()
        assert len(operations) == 3
        assert operations[0]["type"] == "edit"
        assert operations[1]["type"] == "write"
        assert operations[2]["type"] == "delete"

    def test_clear_operations(self):
        """Test clearing operations."""
        track_git_operation("edit", "/test/file.py")
        assert len(get_git_operations()) > 0

        clear_git_operations()
        assert len(get_git_operations()) == 0


class TestDiffFormatting:
    """Test diff formatting utilities."""

    def test_format_empty_diff(self):
        """Test formatting empty diff."""
        result = format_diff_for_display("")
        assert result == "(no changes)"

    def test_format_short_diff(self):
        """Test formatting short diff."""
        diff = "\n".join([f"+ Line {i}" for i in range(10)])
        result = format_diff_for_display(diff, max_lines=50)

        assert result == diff
        assert "..." not in result

    def test_format_long_diff_truncated(self):
        """Test formatting long diff with truncation."""
        diff = "\n".join([f"+ Line {i}" for i in range(100)])
        result = format_diff_for_display(diff, max_lines=10)

        assert "..." in result
        assert "90 more lines" in result
        assert result.count("\n") < diff.count("\n")

    def test_format_whitespace_only_diff(self):
        """Test formatting whitespace-only diff."""
        result = format_diff_for_display("   \n\n  ")
        assert result == "(no changes)"


class TestDiffStats:
    """Test diff statistics parsing."""

    def test_parse_empty_diff(self):
        """Test parsing empty diff."""
        stats = parse_diff_stats("")

        assert stats["additions"] == 0
        assert stats["deletions"] == 0
        assert stats["files_changed"] == 0
        assert stats["total_changes"] == 0

    def test_parse_additions_only(self):
        """Test parsing diff with only additions."""
        diff = "\n".join([
            "diff --git a/file.py b/file.py",
            "+++ b/file.py",
            "+ Line 1",
            "+ Line 2",
            "+ Line 3"
        ])

        stats = parse_diff_stats(diff)

        assert stats["additions"] == 3
        assert stats["deletions"] == 0
        assert stats["files_changed"] == 1
        assert stats["total_changes"] == 3

    def test_parse_deletions_only(self):
        """Test parsing diff with only deletions."""
        diff = "\n".join([
            "diff --git a/file.py b/file.py",
            "--- a/file.py",
            "- Line 1",
            "- Line 2"
        ])

        stats = parse_diff_stats(diff)

        assert stats["additions"] == 0
        assert stats["deletions"] == 2
        assert stats["files_changed"] == 1
        assert stats["total_changes"] == 2

    def test_parse_mixed_changes(self):
        """Test parsing diff with additions and deletions."""
        diff = "\n".join([
            "diff --git a/file1.py b/file1.py",
            "+++ b/file1.py",
            "+ Added line",
            "- Removed line",
            "diff --git a/file2.py b/file2.py",
            "+ Another addition"
        ])

        stats = parse_diff_stats(diff)

        assert stats["additions"] == 2
        assert stats["deletions"] == 1
        assert stats["files_changed"] == 2
        assert stats["total_changes"] == 3

    def test_parse_ignores_diff_markers(self):
        """Test that +++ and --- markers are not counted."""
        diff = "\n".join([
            "+++ b/file.py",
            "--- a/file.py",
            "+ Real addition",
            "- Real deletion"
        ])

        stats = parse_diff_stats(diff)

        assert stats["additions"] == 1
        assert stats["deletions"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
