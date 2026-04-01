"""Unit tests for GrepToolV3."""

from __future__ import annotations

import pytest

from mindflow_backend.agents.tools.filesystem.grep_v3 import (
    GrepInput,
    grep_execute,
)


class TestGrepToolV3:
    """Test suite for GrepToolV3."""

    @pytest.mark.asyncio
    async def test_grep_basic(self, temp_dir, tool_context):
        """Test basic grep search."""
        # Create test files
        (temp_dir / "file1.txt").write_text("Hello World\nFoo Bar")
        (temp_dir / "file2.txt").write_text("Hello Python\nBaz Qux")

        input_data = GrepInput(
            pattern="Hello",
            directory=str(temp_dir)
        )
        result = await grep_execute(input_data, tool_context)

        assert result["success"] is True
        assert result["total_matches"] == 2
        assert len(result["matches"]) == 2

    @pytest.mark.asyncio
    async def test_grep_case_sensitive(self, temp_dir, tool_context):
        """Test case-sensitive search."""
        # Create file with words on separate lines for accurate counting
        (temp_dir / "test.txt").write_text("Hello\nhello\nHELLO")

        # Case-insensitive (default)
        input_data = GrepInput(
            pattern="hello",
            directory=str(temp_dir),
            case_sensitive=False
        )
        result = await grep_execute(input_data, tool_context)
        assert result["total_matches"] == 3

        # Case-sensitive
        input_data = GrepInput(
            pattern="hello",
            directory=str(temp_dir),
            case_sensitive=True
        )
        result = await grep_execute(input_data, tool_context)
        assert result["total_matches"] == 1

    @pytest.mark.asyncio
    async def test_grep_regex_pattern(self, temp_dir, tool_context):
        """Test regex pattern matching."""
        (temp_dir / "test.txt").write_text("test123\ntest456\nabc789")

        input_data = GrepInput(
            pattern=r"test\d+",
            directory=str(temp_dir)
        )
        result = await grep_execute(input_data, tool_context)

        assert result["success"] is True
        assert result["total_matches"] == 2

    @pytest.mark.asyncio
    async def test_grep_file_pattern_filter(self, temp_dir, tool_context):
        """Test filtering by file pattern."""
        (temp_dir / "test.py").write_text("import os")
        (temp_dir / "test.txt").write_text("import os")
        (temp_dir / "test.md").write_text("import os")

        # Only search .py files
        input_data = GrepInput(
            pattern="import",
            directory=str(temp_dir),
            file_pattern="*.py"
        )
        result = await grep_execute(input_data, tool_context)

        assert result["success"] is True
        assert result["total_matches"] == 1
        assert "test.py" in result["matches"][0]["file"]

    @pytest.mark.asyncio
    async def test_grep_recursive(self, temp_dir, tool_context):
        """Test recursive search."""
        # Create nested structure
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        (temp_dir / "root.txt").write_text("pattern")
        (subdir / "nested.txt").write_text("pattern")

        # Recursive search
        input_data = GrepInput(
            pattern="pattern",
            directory=str(temp_dir),
            recursive=True
        )
        result = await grep_execute(input_data, tool_context)

        assert result["success"] is True
        assert result["total_matches"] == 2

        # Non-recursive search
        input_data = GrepInput(
            pattern="pattern",
            directory=str(temp_dir),
            recursive=False
        )
        result = await grep_execute(input_data, tool_context)

        assert result["success"] is True
        assert result["total_matches"] == 1

    @pytest.mark.asyncio
    async def test_grep_max_results(self, temp_dir, tool_context):
        """Test max results limit."""
        # Create many matching files
        for i in range(20):
            (temp_dir / f"file{i}.txt").write_text("match")

        input_data = GrepInput(
            pattern="match",
            directory=str(temp_dir),
            max_results=5
        )
        result = await grep_execute(input_data, tool_context)

        assert result["success"] is True
        assert len(result["matches"]) == 5
        assert result["truncated"] is True

    @pytest.mark.asyncio
    async def test_grep_no_matches(self, temp_dir, tool_context):
        """Test when no matches are found."""
        (temp_dir / "test.txt").write_text("Hello World")

        input_data = GrepInput(
            pattern="NonExistent",
            directory=str(temp_dir)
        )
        result = await grep_execute(input_data, tool_context)

        assert result["success"] is True
        assert result["total_matches"] == 0
        assert len(result["matches"]) == 0

    @pytest.mark.asyncio
    async def test_grep_directory_not_found(self, temp_dir, tool_context):
        """Test searching in non-existent directory."""
        input_data = GrepInput(
            pattern="test",
            directory=str(temp_dir / "nonexistent")
        )
        result = await grep_execute(input_data, tool_context)

        assert result["success"] is False
        assert result["error_code"] == "DIRECTORY_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_grep_with_line_numbers(self, temp_dir, tool_context):
        """Test that line numbers are included."""
        (temp_dir / "test.txt").write_text("Line 1\nMatch here\nLine 3")

        input_data = GrepInput(
            pattern="Match",
            directory=str(temp_dir),
            include_line_numbers=True
        )
        result = await grep_execute(input_data, tool_context)

        assert result["success"] is True
        assert result["total_matches"] == 1
        match = result["matches"][0]
        assert "line_number" in match
        assert match["line_number"] == 2

    @pytest.mark.asyncio
    async def test_grep_multiline_content(self, temp_dir, tool_context):
        """Test searching multiline content."""
        (temp_dir / "test.txt").write_text("First\nSecond\nThird")

        input_data = GrepInput(
            pattern="Second",
            directory=str(temp_dir)
        )
        result = await grep_execute(input_data, tool_context)

        assert result["success"] is True
        assert result["total_matches"] == 1
        assert "Second" in result["matches"][0]["line"]
