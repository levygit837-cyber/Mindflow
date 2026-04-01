"""Unit tests for DirectoryListToolV3."""

import os
import tempfile
from pathlib import Path

import pytest

from mindflow_backend.agents.tools.filesystem.directory_list_v3 import (
    DirectoryListInput,
    DirectoryListToolV3,
    directory_list_execute,
)
from mindflow_backend.schemas.tools.context import ToolContext


@pytest.mark.asyncio
async def test_directory_list_basic(temp_dir, mock_tool_context):
    """Test basic directory listing."""
    # Create test files
    (Path(temp_dir) / "file1.txt").touch()
    (Path(temp_dir) / "file2.py").touch()
    (Path(temp_dir) / "subdir").mkdir()

    input_data = DirectoryListInput(
        directory_path=str(temp_dir),
        include_hidden=False,
        include_size=True,
        include_type=True
    )

    result = await directory_list_execute(input_data, mock_tool_context)

    assert result["success"] is True
    assert result["directory_path"] == str(temp_dir)
    assert result["total_count"] == 3
    assert len(result["entries"]) == 3

    # Check entries have expected fields
    for entry in result["entries"]:
        assert "name" in entry
        assert "path" in entry
        assert "type" in entry
        assert "size" in entry


@pytest.mark.asyncio
async def test_directory_list_hidden_files(temp_dir, mock_tool_context):
    """Test listing with hidden files."""
    # Create test files including hidden
    (Path(temp_dir) / "visible.txt").touch()
    (Path(temp_dir) / ".hidden").touch()

    # Without hidden files
    input_data = DirectoryListInput(
        directory_path=str(temp_dir),
        include_hidden=False
    )
    result = await directory_list_execute(input_data, mock_tool_context)
    assert result["success"] is True
    assert result["total_count"] == 1

    # With hidden files
    input_data = DirectoryListInput(
        directory_path=str(temp_dir),
        include_hidden=True
    )
    result = await directory_list_execute(input_data, mock_tool_context)
    assert result["success"] is True
    assert result["total_count"] == 2


@pytest.mark.asyncio
async def test_directory_list_types(temp_dir, mock_tool_context):
    """Test file type detection."""
    # Create different types
    (Path(temp_dir) / "file.txt").touch()
    (Path(temp_dir) / "dir").mkdir()

    input_data = DirectoryListInput(
        directory_path=str(temp_dir),
        include_type=True
    )

    result = await directory_list_execute(input_data, mock_tool_context)

    assert result["success"] is True
    entries_by_name = {e["name"]: e for e in result["entries"]}
    assert entries_by_name["file.txt"]["type"] == "file"
    assert entries_by_name["dir"]["type"] == "directory"


@pytest.mark.asyncio
async def test_directory_list_max_items(temp_dir, mock_tool_context):
    """Test max items limit."""
    # Create many files
    for i in range(15):
        (Path(temp_dir) / f"file{i}.txt").touch()

    input_data = DirectoryListInput(
        directory_path=str(temp_dir),
        max_items=10
    )

    result = await directory_list_execute(input_data, mock_tool_context)

    assert result["success"] is True
    assert result["total_count"] == 10
    assert result["truncated"] is True


@pytest.mark.asyncio
async def test_directory_list_not_found(mock_tool_context):
    """Test listing non-existent directory."""
    input_data = DirectoryListInput(
        directory_path="/nonexistent/path"
    )

    result = await directory_list_execute(input_data, mock_tool_context)

    assert result["success"] is False
    assert result["error_code"] == "DIRECTORY_NOT_FOUND"
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_directory_list_not_a_directory(temp_dir, mock_tool_context):
    """Test listing a file instead of directory."""
    file_path = Path(temp_dir) / "file.txt"
    file_path.touch()

    input_data = DirectoryListInput(
        directory_path=str(file_path)
    )

    result = await directory_list_execute(input_data, mock_tool_context)

    assert result["success"] is False
    assert result["error_code"] == "NOT_A_DIRECTORY"


@pytest.mark.asyncio
async def test_directory_list_device_path_blocked(mock_tool_context):
    """Test that device paths are blocked."""
    input_data = DirectoryListInput(
        directory_path="/dev/null"
    )

    result = await directory_list_execute(input_data, mock_tool_context)

    assert result["success"] is False
    assert result["error_code"] == "DEVICE_PATH_BLOCKED"


@pytest.mark.asyncio
async def test_directory_list_without_size(temp_dir, mock_tool_context):
    """Test listing without size information."""
    (Path(temp_dir) / "file.txt").touch()

    input_data = DirectoryListInput(
        directory_path=str(temp_dir),
        include_size=False
    )

    result = await directory_list_execute(input_data, mock_tool_context)

    assert result["success"] is True
    for entry in result["entries"]:
        assert "size" not in entry


@pytest.mark.asyncio
async def test_directory_list_without_type(temp_dir, mock_tool_context):
    """Test listing without type information."""
    (Path(temp_dir) / "file.txt").touch()

    input_data = DirectoryListInput(
        directory_path=str(temp_dir),
        include_type=False
    )

    result = await directory_list_execute(input_data, mock_tool_context)

    assert result["success"] is True
    for entry in result["entries"]:
        assert "type" not in entry


@pytest.mark.asyncio
async def test_directory_list_empty_directory(temp_dir, mock_tool_context):
    """Test listing empty directory."""
    input_data = DirectoryListInput(
        directory_path=str(temp_dir)
    )

    result = await directory_list_execute(input_data, mock_tool_context)

    assert result["success"] is True
    assert result["total_count"] == 0
    assert len(result["entries"]) == 0


@pytest.mark.asyncio
async def test_directory_list_with_root_dir(temp_dir, mock_tool_context):
    """Test listing with root_dir from context."""
    # Create subdirectory
    subdir = Path(temp_dir) / "subdir"
    subdir.mkdir()
    (subdir / "file.txt").touch()

    # Set root_dir in context
    mock_tool_context.metadata["root_dir"] = str(temp_dir)

    # Use relative path
    input_data = DirectoryListInput(
        directory_path="subdir"
    )

    result = await directory_list_execute(input_data, mock_tool_context)

    assert result["success"] is True
    assert result["total_count"] == 1
