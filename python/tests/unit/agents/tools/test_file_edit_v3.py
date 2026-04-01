"""Unit tests for FileEditToolV3."""

from __future__ import annotations

import pytest

from mindflow_backend.agents.tools.filesystem.file_edit_v3 import (
    FileEditInput,
    file_edit_execute,
)


class TestFileEditToolV3:
    """Test suite for FileEditToolV3."""

    @pytest.mark.asyncio
    async def test_edit_file_basic(self, test_file, tool_context):
        """Test basic file editing."""
        input_data = FileEditInput(
            file_path=str(test_file),
            old_string="Line 2",
            new_string="Modified Line 2"
        )
        result = await file_edit_execute(input_data, tool_context)

        assert result["success"] is True
        assert result["occurrences_replaced"] == 1
        content = test_file.read_text()
        assert "Modified Line 2" in content
        # Check that the old standalone line is gone (not just substring)
        lines = content.split('\n')
        assert "Line 2" not in lines

    @pytest.mark.asyncio
    async def test_edit_file_multiple_occurrences(self, temp_dir, tool_context):
        """Test editing with multiple occurrences."""
        file_path = temp_dir / "multi.txt"
        file_path.write_text("foo bar foo baz foo")

        # Replace first occurrence only (count=1)
        input_data = FileEditInput(
            file_path=str(file_path),
            old_string="foo",
            new_string="FOO",
            count=1
        )
        result = await file_edit_execute(input_data, tool_context)

        assert result["success"] is True
        assert result["occurrences_replaced"] == 1
        content = file_path.read_text()
        assert content.count("FOO") == 1
        assert content.count("foo") == 2

    @pytest.mark.asyncio
    async def test_edit_file_replace_all(self, temp_dir, tool_context):
        """Test replacing all occurrences."""
        file_path = temp_dir / "multi.txt"
        file_path.write_text("foo bar foo baz foo")

        # Replace all occurrences (count=-1)
        input_data = FileEditInput(
            file_path=str(file_path),
            old_string="foo",
            new_string="FOO",
            count=-1
        )
        result = await file_edit_execute(input_data, tool_context)

        assert result["success"] is True
        assert result["occurrences_replaced"] == 3
        content = file_path.read_text()
        assert content.count("FOO") == 3
        assert "foo" not in content

    @pytest.mark.asyncio
    async def test_edit_file_string_not_found(self, test_file, tool_context):
        """Test editing when old_string is not found."""
        input_data = FileEditInput(
            file_path=str(test_file),
            old_string="NonExistent",
            new_string="Replacement"
        )
        result = await file_edit_execute(input_data, tool_context)

        assert result["success"] is False
        assert result["error_code"] == "STRING_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_edit_file_not_found(self, temp_dir, tool_context):
        """Test editing non-existent file."""
        input_data = FileEditInput(
            file_path=str(temp_dir / "nonexistent.txt"),
            old_string="old",
            new_string="new"
        )
        result = await file_edit_execute(input_data, tool_context)

        assert result["success"] is False
        assert result["error_code"] == "FILE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_edit_device_file_blocked(self, tool_context):
        """Test that device files are blocked."""
        input_data = FileEditInput(
            file_path="/dev/null",
            old_string="old",
            new_string="new"
        )
        result = await file_edit_execute(input_data, tool_context)

        assert result["success"] is False
        assert result["error_code"] == "DEVICE_FILE_BLOCKED"

    @pytest.mark.asyncio
    async def test_edit_system_path_blocked(self, tool_context):
        """Test that system paths are blocked."""
        input_data = FileEditInput(
            file_path="/etc/passwd",
            old_string="old",
            new_string="new"
        )
        result = await file_edit_execute(input_data, tool_context)

        assert result["success"] is False
        assert result["error_code"] == "SYSTEM_PATH_BLOCKED"

    @pytest.mark.asyncio
    async def test_edit_file_with_permission_denied(self, test_file, tool_context_deny_permissions):
        """Test editing with denied permissions."""
        input_data = FileEditInput(
            file_path=str(test_file),
            old_string="Line 1",
            new_string="Modified"
        )
        result = await file_edit_execute(input_data, tool_context_deny_permissions)

        assert result["success"] is False
        assert result["error_code"] == "PERMISSION_DENIED"

    @pytest.mark.asyncio
    async def test_edit_file_multiline_replacement(self, temp_dir, tool_context):
        """Test replacing multiline content."""
        file_path = temp_dir / "multiline.txt"
        file_path.write_text("Line 1\nLine 2\nLine 3")

        input_data = FileEditInput(
            file_path=str(file_path),
            old_string="Line 1\nLine 2",
            new_string="Modified Lines"
        )
        result = await file_edit_execute(input_data, tool_context)

        assert result["success"] is True
        assert result["occurrences_replaced"] == 1
        content = file_path.read_text()
        assert "Modified Lines" in content
        assert "Line 3" in content

    @pytest.mark.asyncio
    async def test_edit_file_size_tracking(self, test_file, tool_context):
        """Test that size changes are tracked."""
        original_size = test_file.stat().st_size

        input_data = FileEditInput(
            file_path=str(test_file),
            old_string="Line 1",
            new_string="Much Longer Replacement Line"
        )
        result = await file_edit_execute(input_data, tool_context)

        assert result["success"] is True
        assert "size_before" in result
        assert "size_after" in result
        assert result["size_before"] == original_size
        assert result["size_after"] > original_size

    @pytest.mark.asyncio
    async def test_edit_file_encoding(self, temp_dir, tool_context):
        """Test editing with specific encoding."""
        file_path = temp_dir / "utf8.txt"
        file_path.write_text("Olá Mundo", encoding="utf-8")

        input_data = FileEditInput(
            file_path=str(file_path),
            old_string="Olá",
            new_string="Hello",
            encoding="utf-8"
        )
        result = await file_edit_execute(input_data, tool_context)

        assert result["success"] is True
        content = file_path.read_text(encoding="utf-8")
        assert "Hello Mundo" in content
