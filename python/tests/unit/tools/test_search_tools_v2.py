"""Unit tests for search tools v2.

Tests GlobTool and GrepTool v2 with full integration of schemas,
validators, and security features.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from mindflow_backend.agents.tools.filesystem.search_tools_v2 import (
    GlobToolV2,
    GrepToolV2,
)


class TestGlobToolV2:
    """Test GlobTool v2."""

    @pytest.mark.asyncio
    async def test_glob_simple_pattern(self, tmp_path):
        """Test simple glob pattern matching."""
        # Create test files
        (tmp_path / "file1.py").write_text("python file 1")
        (tmp_path / "file2.py").write_text("python file 2")
        (tmp_path / "file3.txt").write_text("text file")

        tool = GlobToolV2(root_dir=str(tmp_path))
        result = await tool.execute(
            pattern="*.py",
            path=str(tmp_path)
        )

        assert result["success"] is True
        assert result["total_matches"] == 2
        assert any("file1.py" in m for m in result["matches"])
        assert any("file2.py" in m for m in result["matches"])

    @pytest.mark.asyncio
    async def test_glob_with_exclude_patterns(self, tmp_path):
        """Test glob with exclude patterns."""
        # Create test files
        (tmp_path / "include.py").write_text("include")
        (tmp_path / "exclude.py").write_text("exclude")
        (tmp_path / "test.py").write_text("test")

        tool = GlobToolV2(root_dir=str(tmp_path))
        result = await tool.execute(
            pattern="*.py",
            path=str(tmp_path),
            exclude_patterns=["exclude.py", "test.py"]
        )

        assert result["success"] is True
        assert result["total_matches"] == 1
        assert any("include.py" in m for m in result["matches"])

    @pytest.mark.asyncio
    async def test_glob_with_max_depth(self, tmp_path):
        """Test glob with max depth limit."""
        # Create nested structure
        (tmp_path / "root.py").write_text("root")
        subdir1 = tmp_path / "subdir1"
        subdir1.mkdir()
        (subdir1 / "level1.py").write_text("level1")
        subdir2 = subdir1 / "subdir2"
        subdir2.mkdir()
        (subdir2 / "level2.py").write_text("level2")

        tool = GlobToolV2(root_dir=str(tmp_path))
        result = await tool.execute(
            pattern="*.py",
            path=str(tmp_path),
            max_depth=1
        )

        assert result["success"] is True
        # Should find root.py and level1.py, but not level2.py
        assert result["total_matches"] == 2

    @pytest.mark.asyncio
    async def test_glob_sort_by_mtime(self, tmp_path):
        """Test glob with sort by modification time."""
        import time

        # Create files with different mtimes
        file1 = tmp_path / "old.py"
        file1.write_text("old")
        time.sleep(0.01)

        file2 = tmp_path / "new.py"
        file2.write_text("new")

        tool = GlobToolV2(root_dir=str(tmp_path))
        result = await tool.execute(
            pattern="*.py",
            path=str(tmp_path),
            sort_by_mtime=True
        )

        assert result["success"] is True
        # Most recent should be first
        assert "new.py" in result["matches"][0]

    @pytest.mark.asyncio
    async def test_glob_with_pagination(self, tmp_path):
        """Test glob with pagination."""
        # Create multiple files
        for i in range(10):
            (tmp_path / f"file{i}.py").write_text(f"content {i}")

        tool = GlobToolV2(root_dir=str(tmp_path))
        result = await tool.execute(
            pattern="*.py",
            path=str(tmp_path),
            offset=2,
            head_limit=3
        )

        assert result["success"] is True
        assert result["total_matches"] == 10
        assert result["returned_matches"] == 3
        assert result["offset"] == 2
        assert result["truncated"] is True

    @pytest.mark.asyncio
    async def test_glob_case_insensitive(self, tmp_path):
        """Test case insensitive glob matching."""
        (tmp_path / "File.PY").write_text("uppercase")
        (tmp_path / "file.py").write_text("lowercase")

        tool = GlobToolV2(root_dir=str(tmp_path))
        result = await tool.execute(
            pattern="*.py",
            path=str(tmp_path),
            case_sensitive=False
        )

        assert result["success"] is True
        assert result["total_matches"] == 2

    @pytest.mark.asyncio
    async def test_glob_no_matches(self, tmp_path):
        """Test glob with no matches."""
        (tmp_path / "file.txt").write_text("text")

        tool = GlobToolV2(root_dir=str(tmp_path))
        result = await tool.execute(
            pattern="*.py",
            path=str(tmp_path)
        )

        assert result["success"] is True
        assert result["total_matches"] == 0
        assert result["matches"] == []


class TestGrepToolV2:
    """Test GrepTool v2."""

    @pytest.mark.asyncio
    async def test_grep_simple_search(self, tmp_path):
        """Test simple grep search."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World\nGoodbye World\nHello Universe\n")

        tool = GrepToolV2(root_dir=str(tmp_path))
        result = await tool.execute(
            pattern="Hello",
            path=str(test_file)
        )

        assert result["success"] is True
        assert result["total_results"] == 2
        assert any("Hello World" in r["line"] for r in result["results"])

    @pytest.mark.asyncio
    async def test_grep_with_context_lines(self, tmp_path):
        """Test grep with context lines."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Line 1\nLine 2\nMatch here\nLine 4\nLine 5\n")

        tool = GrepToolV2(root_dir=str(tmp_path))
        result = await tool.execute(
            pattern="Match",
            path=str(test_file),
            context_before=1,
            context_after=1
        )

        assert result["success"] is True
        assert "Line 2" in result["results"][0]["context"]
        assert "Match here" in result["results"][0]["context"]
        assert "Line 4" in result["results"][0]["context"]

    @pytest.mark.asyncio
    async def test_grep_files_mode(self, tmp_path):
        """Test grep in files_with_matches mode."""
        # Create multiple files
        (tmp_path / "match1.txt").write_text("This has a match")
        (tmp_path / "match2.txt").write_text("This also has a match")
        (tmp_path / "nomatch.txt").write_text("This does not")

        tool = GrepToolV2(root_dir=str(tmp_path))
        result = await tool.execute(
            pattern="match",
            path=str(tmp_path),
            output_mode="files_with_matches"
        )

        assert result["success"] is True
        assert result["total_results"] == 2
        assert all("file" in r for r in result["results"])

    @pytest.mark.asyncio
    async def test_grep_count_mode(self, tmp_path):
        """Test grep in count mode."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("foo bar foo baz foo")

        tool = GrepToolV2(root_dir=str(tmp_path))
        result = await tool.execute(
            pattern="foo",
            path=str(test_file),
            output_mode="count"
        )

        assert result["success"] is True
        assert result["results"][0]["count"] == 3

    @pytest.mark.asyncio
    async def test_grep_case_insensitive(self, tmp_path):
        """Test case insensitive grep."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello HELLO hello")

        tool = GrepToolV2(root_dir=str(tmp_path))
        result = await tool.execute(
            pattern="hello",
            path=str(test_file),
            case_sensitive=False,
            output_mode="count"
        )

        assert result["success"] is True
        assert result["results"][0]["count"] == 3

    @pytest.mark.asyncio
    async def test_grep_with_glob_filter(self, tmp_path):
        """Test grep with glob pattern filter."""
        (tmp_path / "file1.py").write_text("python match")
        (tmp_path / "file2.txt").write_text("text match")
        (tmp_path / "file3.py").write_text("python match")

        tool = GrepToolV2(root_dir=str(tmp_path))
        result = await tool.execute(
            pattern="match",
            path=str(tmp_path),
            glob_pattern="*.py",
            output_mode="files_with_matches"
        )

        assert result["success"] is True
        assert result["total_results"] == 2
        assert all(".py" in r["file"] for r in result["results"])

    @pytest.mark.asyncio
    async def test_grep_with_line_numbers(self, tmp_path):
        """Test grep with line numbers."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Line 1\nLine 2\nMatch\nLine 4\n")

        tool = GrepToolV2(root_dir=str(tmp_path))
        result = await tool.execute(
            pattern="Match",
            path=str(test_file),
            show_line_numbers=True
        )

        assert result["success"] is True
        assert result["results"][0]["line_number"] == 3

    @pytest.mark.asyncio
    async def test_grep_multiline(self, tmp_path):
        """Test multiline grep matching."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Start\nMiddle\nEnd")

        tool = GrepToolV2(root_dir=str(tmp_path))
        result = await tool.execute(
            pattern="Start.*End",
            path=str(test_file),
            multiline=True
        )

        assert result["success"] is True
        assert result["total_results"] > 0

    @pytest.mark.asyncio
    async def test_grep_with_pagination(self, tmp_path):
        """Test grep with pagination."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("\n".join([f"match {i}" for i in range(10)]))

        tool = GrepToolV2(root_dir=str(tmp_path))
        result = await tool.execute(
            pattern="match",
            path=str(test_file),
            offset=2,
            head_limit=3
        )

        assert result["success"] is True
        assert result["total_results"] == 10
        assert result["returned_results"] == 3
        assert result["truncated"] is True

    @pytest.mark.asyncio
    async def test_grep_invalid_regex(self, tmp_path):
        """Test grep with invalid regex pattern."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        tool = GrepToolV2(root_dir=str(tmp_path))
        result = await tool.execute(
            pattern="[invalid",  # Unclosed bracket
            path=str(test_file)
        )

        assert result["success"] is False
        assert result["error_code"] == "INVALID_PATTERN"

    @pytest.mark.asyncio
    async def test_grep_no_matches(self, tmp_path):
        """Test grep with no matches."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World")

        tool = GrepToolV2(root_dir=str(tmp_path))
        result = await tool.execute(
            pattern="Nonexistent",
            path=str(test_file)
        )

        assert result["success"] is True
        assert result["total_results"] == 0
        assert result["results"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
