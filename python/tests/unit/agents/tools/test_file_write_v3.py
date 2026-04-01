"""Unit tests for FileWriteToolV3."""

from __future__ import annotations

import pytest

from mindflow_backend.agents.tools.filesystem.file_write_v3 import (
    FileWriteInput,
    file_write_execute,
)


class TestFileWriteToolV3:
    """Test suite for FileWriteToolV3."""

    @pytest.mark.asyncio
    async def test_write_file_basic(self, temp_dir, tool_context):
        """Test basic file writing."""
        file_path = temp_dir / "new.txt"
        input_data = FileWriteInput(
            file_path=str(file_path),
            content="Hello World"
        )
        result = await file_write_execute(input_data, tool_context)

        assert result["success"] is True
        assert file_path.exists()
        assert file_path.read_text() == "Hello World"
        assert result["bytes_written"] == len("Hello World")

    @pytest.mark.asyncio
    async def test_write_file_overwrite(self, test_file, tool_context):
        """Test overwriting existing file."""
        original_content = test_file.read_text()

        input_data = FileWriteInput(
            file_path=str(test_file),
            content="New content",
            overwrite=True
        )
        result = await file_write_execute(input_data, tool_context)

        assert result["success"] is True
        assert test_file.read_text() == "New content"
        assert test_file.read_text() != original_content

    @pytest.mark.asyncio
    async def test_write_file_no_overwrite(self, test_file, tool_context):
        """Test that overwrite=False prevents overwriting."""
        input_data = FileWriteInput(
            file_path=str(test_file),
            content="New content",
            overwrite=False
        )
        result = await file_write_execute(input_data, tool_context)

        assert result["success"] is False
        assert result["error_code"] == "FILE_EXISTS"

    @pytest.mark.asyncio
    async def test_write_file_create_dirs(self, temp_dir, tool_context):
        """Test creating parent directories."""
        file_path = temp_dir / "subdir" / "nested" / "file.txt"

        input_data = FileWriteInput(
            file_path=str(file_path),
            content="Nested content",
            create_dirs=True
        )
        result = await file_write_execute(input_data, tool_context)

        assert result["success"] is True
        assert file_path.exists()
        assert file_path.read_text() == "Nested content"

    @pytest.mark.asyncio
    async def test_write_file_no_create_dirs(self, temp_dir, tool_context):
        """Test that create_dirs=False fails on missing parent."""
        file_path = temp_dir / "missing_dir" / "file.txt"

        input_data = FileWriteInput(
            file_path=str(file_path),
            content="Content",
            create_dirs=False
        )
        result = await file_write_execute(input_data, tool_context)

        assert result["success"] is False
        assert result["error_code"] == "DIRECTORY_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_write_device_file_blocked(self, tool_context):
        """Test that device files are blocked."""
        input_data = FileWriteInput(
            file_path="/dev/null",
            content="Should not write"
        )
        result = await file_write_execute(input_data, tool_context)

        assert result["success"] is False
        assert result["error_code"] == "DEVICE_FILE_BLOCKED"

    @pytest.mark.asyncio
    async def test_write_system_path_blocked(self, tool_context):
        """Test that system paths are blocked."""
        input_data = FileWriteInput(
            file_path="/etc/passwd",
            content="Should not write"
        )
        result = await file_write_execute(input_data, tool_context)

        assert result["success"] is False
        assert result["error_code"] == "SYSTEM_PATH_BLOCKED"

    @pytest.mark.asyncio
    async def test_write_file_with_permission_denied(self, temp_dir, tool_context_deny_permissions):
        """Test writing with denied permissions."""
        file_path = temp_dir / "denied.txt"
        input_data = FileWriteInput(
            file_path=str(file_path),
            content="Content"
        )
        result = await file_write_execute(input_data, tool_context_deny_permissions)

        assert result["success"] is False
        assert result["error_code"] == "PERMISSION_DENIED"

    @pytest.mark.asyncio
    async def test_write_file_encoding(self, temp_dir, tool_context):
        """Test writing with specific encoding."""
        file_path = temp_dir / "utf8.txt"
        content = "Olá Mundo! 你好世界"

        input_data = FileWriteInput(
            file_path=str(file_path),
            content=content,
            encoding="utf-8"
        )
        result = await file_write_execute(input_data, tool_context)

        assert result["success"] is True
        assert file_path.read_text(encoding="utf-8") == content

    @pytest.mark.asyncio
    async def test_write_empty_content(self, temp_dir, tool_context):
        """Test writing empty content."""
        file_path = temp_dir / "empty.txt"

        input_data = FileWriteInput(
            file_path=str(file_path),
            content=""
        )
        result = await file_write_execute(input_data, tool_context)

        assert result["success"] is True
        assert file_path.exists()
        assert file_path.read_text() == ""
        assert result["bytes_written"] == 0

    @pytest.mark.asyncio
    async def test_write_multiline_content(self, temp_dir, tool_context):
        """Test writing multiline content."""
        file_path = temp_dir / "multiline.txt"
        content = "Line 1\nLine 2\nLine 3"

        input_data = FileWriteInput(
            file_path=str(file_path),
            content=content
        )
        result = await file_write_execute(input_data, tool_context)

        assert result["success"] is True
        assert file_path.read_text() == content
        assert file_path.read_text().count("\n") == 2
