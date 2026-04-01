"""Unit tests for FileReadToolV3."""

from __future__ import annotations

import pytest

from mindflow_backend.agents.tools.filesystem.file_operations_v3 import (
    FileReadInput,
    file_read_execute,
)


class TestFileReadToolV3:
    """Test suite for FileReadToolV3."""

    @pytest.mark.asyncio
    async def test_read_file_basic(self, test_file, tool_context):
        """Test basic file reading."""
        input_data = FileReadInput(file_path=str(test_file))
        result = await file_read_execute(input_data, tool_context)

        assert result["success"] is True
        assert "Line 1" in result["content"]
        assert "Line 5" in result["content"]
        assert result["file_path"] == str(test_file)
        assert result["lines_read"] == 5

    @pytest.mark.asyncio
    async def test_read_file_with_line_numbers(self, test_file, tool_context):
        """Test reading with line numbers."""
        input_data = FileReadInput(
            file_path=str(test_file),
            include_line_numbers=True
        )
        result = await file_read_execute(input_data, tool_context)

        assert result["success"] is True
        assert "1\tLine 1" in result["content"]
        assert "5\tLine 5" in result["content"]

    @pytest.mark.asyncio
    async def test_read_file_with_pagination(self, test_file, tool_context):
        """Test reading with offset and limit."""
        input_data = FileReadInput(
            file_path=str(test_file),
            offset=1,
            limit=2
        )
        result = await file_read_execute(input_data, tool_context)

        assert result["success"] is True
        assert "Line 2" in result["content"]
        assert "Line 3" in result["content"]
        assert "Line 1" not in result["content"]
        assert "Line 4" not in result["content"]
        assert result["lines_read"] == 2

    @pytest.mark.asyncio
    async def test_read_file_not_found(self, temp_dir, tool_context):
        """Test reading non-existent file."""
        input_data = FileReadInput(file_path=str(temp_dir / "nonexistent.txt"))
        result = await file_read_execute(input_data, tool_context)

        assert result["success"] is False
        assert result["error_code"] == "FILE_NOT_FOUND"
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_read_device_file_blocked(self, tool_context):
        """Test that device files are blocked."""
        input_data = FileReadInput(file_path="/dev/zero")
        result = await file_read_execute(input_data, tool_context)

        assert result["success"] is False
        assert result["error_code"] == "DEVICE_FILE_BLOCKED"
        assert "device file" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_read_file_with_permission_denied(self, test_file, tool_context_deny_permissions):
        """Test reading with denied permissions."""
        input_data = FileReadInput(file_path=str(test_file))
        result = await file_read_execute(input_data, tool_context_deny_permissions)

        assert result["success"] is False
        assert result["error_code"] == "PERMISSION_DENIED"

    @pytest.mark.asyncio
    async def test_read_file_relative_path(self, temp_dir, tool_context):
        """Test reading with relative path (resolved via root_dir)."""
        # Create file in temp_dir
        file_path = temp_dir / "relative.txt"
        file_path.write_text("Relative content")

        # Use relative path
        input_data = FileReadInput(file_path="relative.txt")
        result = await file_read_execute(input_data, tool_context)

        assert result["success"] is True
        assert "Relative content" in result["content"]

    @pytest.mark.asyncio
    async def test_read_empty_file(self, temp_dir, tool_context):
        """Test reading empty file."""
        empty_file = temp_dir / "empty.txt"
        empty_file.write_text("")

        input_data = FileReadInput(file_path=str(empty_file))
        result = await file_read_execute(input_data, tool_context)

        assert result["success"] is True
        assert result["content"] == ""
        assert result["lines_read"] == 0

    @pytest.mark.asyncio
    async def test_read_file_encoding(self, temp_dir, tool_context):
        """Test reading file with specific encoding."""
        # Create UTF-8 file with special characters
        utf8_file = temp_dir / "utf8.txt"
        utf8_file.write_text("Olá Mundo! 你好世界", encoding="utf-8")

        input_data = FileReadInput(
            file_path=str(utf8_file),
            encoding="utf-8"
        )
        result = await file_read_execute(input_data, tool_context)

        assert result["success"] is True
        assert "Olá Mundo!" in result["content"]
        assert "你好世界" in result["content"]

    @pytest.mark.asyncio
    async def test_read_large_file_truncation(self, temp_dir, tool_context):
        """Test that large files are properly paginated."""
        # Create file with many lines
        large_file = temp_dir / "large.txt"
        lines = [f"Line {i}" for i in range(3000)]
        large_file.write_text("\n".join(lines))

        # Read with default limit (2000)
        input_data = FileReadInput(file_path=str(large_file))
        result = await file_read_execute(input_data, tool_context)

        assert result["success"] is True
        assert result["lines_read"] == 2000
        assert result["total_lines"] == 3000
        assert result["truncated"] is True
