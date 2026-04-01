"""Unit tests for FileDeleteToolV3."""

import os
from pathlib import Path

import pytest

from mindflow_backend.agents.tools.filesystem.file_delete_v3 import (
    FileDeleteInput,
    FileDeleteToolV3,
    file_delete_execute,
)
from mindflow_backend.schemas.tools.context import ToolContext


@pytest.mark.asyncio
async def test_file_delete_basic(temp_dir, mock_tool_context):
    """Test basic file deletion."""
    file_path = Path(temp_dir) / "test.txt"
    file_path.write_text("test content")

    input_data = FileDeleteInput(
        file_path=str(file_path)
    )

    result = await file_delete_execute(input_data, mock_tool_context)

    assert result["success"] is True
    assert result["deleted"] is True
    assert result["file_name"] == "test.txt"
    assert not file_path.exists()


@pytest.mark.asyncio
async def test_file_delete_with_size(temp_dir, mock_tool_context):
    """Test file deletion returns file size."""
    file_path = Path(temp_dir) / "test.txt"
    content = "test content"
    file_path.write_text(content)

    input_data = FileDeleteInput(
        file_path=str(file_path)
    )

    result = await file_delete_execute(input_data, mock_tool_context)

    assert result["success"] is True
    assert result["file_size"] == len(content.encode())


@pytest.mark.asyncio
async def test_file_delete_not_found(temp_dir, mock_tool_context):
    """Test deleting non-existent file."""
    file_path = Path(temp_dir) / "nonexistent.txt"

    input_data = FileDeleteInput(
        file_path=str(file_path)
    )

    result = await file_delete_execute(input_data, mock_tool_context)

    assert result["success"] is False
    assert result["error_code"] == "FILE_NOT_FOUND"


@pytest.mark.asyncio
async def test_file_delete_directory(temp_dir, mock_tool_context):
    """Test deleting a directory (should fail)."""
    dir_path = Path(temp_dir) / "testdir"
    dir_path.mkdir()

    input_data = FileDeleteInput(
        file_path=str(dir_path)
    )

    result = await file_delete_execute(input_data, mock_tool_context)

    assert result["success"] is False
    assert result["error_code"] == "NOT_A_FILE"


@pytest.mark.asyncio
async def test_file_delete_device_file_blocked(mock_tool_context):
    """Test that device files are blocked."""
    input_data = FileDeleteInput(
        file_path="/dev/null"
    )

    result = await file_delete_execute(input_data, mock_tool_context)

    assert result["success"] is False
    assert result["error_code"] == "DEVICE_FILE_BLOCKED"


@pytest.mark.asyncio
async def test_file_delete_system_path_blocked(mock_tool_context):
    """Test that system paths are blocked."""
    input_data = FileDeleteInput(
        file_path="/etc/passwd"
    )

    result = await file_delete_execute(input_data, mock_tool_context)

    assert result["success"] is False
    assert result["error_code"] == "SYSTEM_PATH_BLOCKED"


@pytest.mark.asyncio
async def test_file_delete_with_confirm(temp_dir, mock_tool_context):
    """Test file deletion with confirmation flag."""
    file_path = Path(temp_dir) / "test.txt"
    file_path.write_text("test content")

    input_data = FileDeleteInput(
        file_path=str(file_path),
        confirm=True
    )

    result = await file_delete_execute(input_data, mock_tool_context)

    assert result["success"] is True
    assert result["deleted"] is True
    assert not file_path.exists()


@pytest.mark.asyncio
async def test_file_delete_with_root_dir(temp_dir, mock_tool_context):
    """Test file deletion with root_dir from context."""
    file_path = Path(temp_dir) / "test.txt"
    file_path.write_text("test content")

    # Set root_dir in context
    mock_tool_context.metadata["root_dir"] = str(temp_dir)

    # Use relative path
    input_data = FileDeleteInput(
        file_path="test.txt"
    )

    result = await file_delete_execute(input_data, mock_tool_context)

    assert result["success"] is True
    assert result["deleted"] is True
    assert not file_path.exists()


@pytest.mark.asyncio
async def test_file_delete_returns_file_info(temp_dir, mock_tool_context):
    """Test that deletion returns file information."""
    file_path = Path(temp_dir) / "info.txt"
    file_path.write_text("content")

    input_data = FileDeleteInput(
        file_path=str(file_path)
    )

    result = await file_delete_execute(input_data, mock_tool_context)

    assert result["success"] is True
    assert "file_name" in result
    assert "file_size" in result
    assert "file_path" in result
    assert result["file_name"] == "info.txt"
