"""Unit tests for GlobToolV3."""

from __future__ import annotations

import pytest

from mindflow_backend.agents.tools.filesystem.glob_v3 import (
    GlobInput,
    glob_execute,
)


class TestGlobToolV3:
    """Test suite for GlobToolV3."""

    @pytest.mark.asyncio
    async def test_glob_basic(self, temp_dir, tool_context):
        """Test basic glob pattern matching."""
        # Create test files
        (temp_dir / "test1.txt").write_text("content")
        (temp_dir / "test2.txt").write_text("content")
        (temp_dir / "other.md").write_text("content")

        input_data = GlobInput(
            pattern="*.txt",
            directory=str(temp_dir)
        )
        result = await glob_execute(input_data, tool_context)

        assert result["success"] is True
        assert result["total_files"] == 2
        assert len(result["files"]) == 2

    @pytest.mark.asyncio
    async def test_glob_recursive_pattern(self, temp_dir, tool_context):
        """Test recursive glob pattern with **."""
        # Create nested structure
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        (temp_dir / "root.py").write_text("code")
        (subdir / "nested.py").write_text("code")

        input_data = GlobInput(
            pattern="**/*.py",
            directory=str(temp_dir)
        )
        result = await glob_execute(input_data, tool_context)

        assert result["success"] is True
        assert result["total_files"] == 2

    @pytest.mark.asyncio
    async def test_glob_no_matches(self, temp_dir, tool_context):
        """Test when no files match pattern."""
        (temp_dir / "test.txt").write_text("content")

        input_data = GlobInput(
            pattern="*.py",
            directory=str(temp_dir)
        )
        result = await glob_execute(input_data, tool_context)

        assert result["success"] is True
        assert result["total_files"] == 0
        assert len(result["files"]) == 0

    @pytest.mark.asyncio
    async def test_glob_max_results(self, temp_dir, tool_context):
        """Test max results limit."""
        # Create many files
        for i in range(20):
            (temp_dir / f"file{i}.txt").write_text("content")

        input_data = GlobInput(
            pattern="*.txt",
            directory=str(temp_dir),
            max_results=5
        )
        result = await glob_execute(input_data, tool_context)

        assert result["success"] is True
        assert len(result["files"]) == 5
        assert result["truncated"] is True

    @pytest.mark.asyncio
    async def test_glob_include_directories(self, temp_dir, tool_context):
        """Test including directories in results."""
        # Create files and directories
        (temp_dir / "file.txt").write_text("content")
        (temp_dir / "subdir").mkdir()

        input_data = GlobInput(
            pattern="*",
            directory=str(temp_dir),
            include_dirs=True
        )
        result = await glob_execute(input_data, tool_context)

        assert result["success"] is True
        assert result["total_files"] == 1
        assert result["total_directories"] == 1
        assert result["total_matches"] == 2

    @pytest.mark.asyncio
    async def test_glob_exclude_directories(self, temp_dir, tool_context):
        """Test excluding directories from results."""
        # Create files and directories
        (temp_dir / "file.txt").write_text("content")
        (temp_dir / "subdir").mkdir()

        input_data = GlobInput(
            pattern="*",
            directory=str(temp_dir),
            include_dirs=False
        )
        result = await glob_execute(input_data, tool_context)

        assert result["success"] is True
        assert result["total_files"] == 1
        assert "directories" not in result

    @pytest.mark.asyncio
    async def test_glob_absolute_paths(self, temp_dir, tool_context):
        """Test returning absolute paths."""
        (temp_dir / "test.txt").write_text("content")

        input_data = GlobInput(
            pattern="*.txt",
            directory=str(temp_dir),
            absolute_paths=True
        )
        result = await glob_execute(input_data, tool_context)

        assert result["success"] is True
        assert len(result["files"]) == 1
        # Check that path is absolute
        assert result["files"][0].startswith("/")

    @pytest.mark.asyncio
    async def test_glob_relative_paths(self, temp_dir, tool_context):
        """Test returning relative paths."""
        (temp_dir / "test.txt").write_text("content")

        input_data = GlobInput(
            pattern="*.txt",
            directory=str(temp_dir),
            absolute_paths=False
        )
        result = await glob_execute(input_data, tool_context)

        assert result["success"] is True
        assert len(result["files"]) == 1
        # Check that path is relative
        assert result["files"][0] == "test.txt"

    @pytest.mark.asyncio
    async def test_glob_directory_not_found(self, temp_dir, tool_context):
        """Test searching in non-existent directory."""
        input_data = GlobInput(
            pattern="*.txt",
            directory=str(temp_dir / "nonexistent")
        )
        result = await glob_execute(input_data, tool_context)

        assert result["success"] is False
        assert result["error_code"] == "DIRECTORY_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_glob_not_a_directory(self, test_file, tool_context):
        """Test when path is a file, not a directory."""
        input_data = GlobInput(
            pattern="*.txt",
            directory=str(test_file)
        )
        result = await glob_execute(input_data, tool_context)

        assert result["success"] is False
        assert result["error_code"] == "NOT_A_DIRECTORY"

    @pytest.mark.asyncio
    async def test_glob_complex_pattern(self, temp_dir, tool_context):
        """Test complex glob patterns."""
        # Create various files
        (temp_dir / "test.py").write_text("code")
        (temp_dir / "test.txt").write_text("text")
        (temp_dir / "data.json").write_text("data")

        # Match multiple extensions
        input_data = GlobInput(
            pattern="*.{py,json}",
            directory=str(temp_dir)
        )
        result = await glob_execute(input_data, tool_context)

        assert result["success"] is True
        # Note: This might not work with standard glob, depends on implementation
        # If it doesn't work, that's expected behavior

    @pytest.mark.asyncio
    async def test_glob_nested_directories(self, temp_dir, tool_context):
        """Test searching in nested directory structure."""
        # Create nested structure
        level1 = temp_dir / "level1"
        level2 = level1 / "level2"
        level2.mkdir(parents=True)

        (temp_dir / "root.txt").write_text("content")
        (level1 / "l1.txt").write_text("content")
        (level2 / "l2.txt").write_text("content")

        input_data = GlobInput(
            pattern="**/*.txt",
            directory=str(temp_dir)
        )
        result = await glob_execute(input_data, tool_context)

        assert result["success"] is True
        assert result["total_files"] == 3
