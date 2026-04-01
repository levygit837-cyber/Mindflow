"""Unit tests for DirectoryCreateToolV3."""

import os
from pathlib import Path

import pytest

from mindflow_backend.agents.tools.filesystem.directory_create_v3 import (
    DirectoryCreateInput,
    DirectoryCreateToolV3,
    directory_create_execute,
)
from mindflow_backend.schemas.tools.context import ToolContext


@pytest.mark.asyncio
async def test_directory_create_basic(temp_dir, mock_tool_context):
    """Test basic directory creation."""
    new_dir = Path(temp_dir) / "newdir"

    input_data = DirectoryCreateInput(
        directory_path=str(new_dir)
    )

    result = await directory_create_execute(input_data, mock_tool_context)

    assert result["success"] is True
    assert result["created"] is True
    assert result["directory_path"] == str(new_dir)
    assert new_dir.exists()
    assert new_dir.is_dir()


@pytest.mark.asyncio
async def test_directory_create_with_parents(temp_dir, mock_tool_context):
    """Test directory creation with parent directories."""
    new_dir = Path(temp_dir) / "parent" / "child" / "grandchild"

    input_data = DirectoryCreateInput(
        directory_path=str(new_dir),
        parents=True
    )

    result = await directory_create_execute(input_data, mock_tool_context)

    assert result["success"] is True
    assert result["created"] is True
    assert result["parents_created"] is True
    assert new_dir.exists()


@pytest.mark.asyncio
async def test_directory_create_without_parents(temp_dir, mock_tool_context):
    """Test directory creation without parent directories."""
    new_dir = Path(temp_dir) / "nonexistent" / "child"

    input_data = DirectoryCreateInput(
        directory_path=str(new_dir),
        parents=False
    )

    result = await directory_create_execute(input_data, mock_tool_context)

    assert result["success"] is False
    assert result["error_code"] == "PARENT_NOT_FOUND"


@pytest.mark.asyncio
async def test_directory_create_already_exists(temp_dir, mock_tool_context):
    """Test creating directory that already exists."""
    existing_dir = Path(temp_dir) / "existing"
    existing_dir.mkdir()

    # With exist_ok=True (default)
    input_data = DirectoryCreateInput(
        directory_path=str(existing_dir),
        exist_ok=True
    )

    result = await directory_create_execute(input_data, mock_tool_context)

    assert result["success"] is True
    assert result["created"] is False
    assert result["already_existed"] is True


@pytest.mark.asyncio
async def test_directory_create_already_exists_error(temp_dir, mock_tool_context):
    """Test creating directory that already exists with exist_ok=False."""
    existing_dir = Path(temp_dir) / "existing"
    existing_dir.mkdir()

    input_data = DirectoryCreateInput(
        directory_path=str(existing_dir),
        exist_ok=False
    )

    result = await directory_create_execute(input_data, mock_tool_context)

    assert result["success"] is False
    assert result["error_code"] == "DIRECTORY_EXISTS"


@pytest.mark.asyncio
async def test_directory_create_file_exists(temp_dir, mock_tool_context):
    """Test creating directory where a file exists."""
    file_path = Path(temp_dir) / "file.txt"
    file_path.touch()

    input_data = DirectoryCreateInput(
        directory_path=str(file_path)
    )

    result = await directory_create_execute(input_data, mock_tool_context)

    assert result["success"] is False
    assert result["error_code"] == "NOT_A_DIRECTORY"


@pytest.mark.asyncio
async def test_directory_create_device_path_blocked(mock_tool_context):
    """Test that device paths are blocked."""
    input_data = DirectoryCreateInput(
        directory_path="/dev/testdir"
    )

    result = await directory_create_execute(input_data, mock_tool_context)

    assert result["success"] is False
    assert result["error_code"] == "DEVICE_PATH_BLOCKED"


@pytest.mark.asyncio
async def test_directory_create_system_path_blocked(mock_tool_context):
    """Test that system paths are blocked."""
    input_data = DirectoryCreateInput(
        directory_path="/etc/testdir"
    )

    result = await directory_create_execute(input_data, mock_tool_context)

    assert result["success"] is False
    assert result["error_code"] == "SYSTEM_PATH_BLOCKED"


@pytest.mark.asyncio
async def test_directory_create_custom_mode(temp_dir, mock_tool_context):
    """Test directory creation with custom permissions."""
    new_dir = Path(temp_dir) / "custom_mode"

    input_data = DirectoryCreateInput(
        directory_path=str(new_dir),
        mode=0o700
    )

    result = await directory_create_execute(input_data, mock_tool_context)

    assert result["success"] is True
    assert result["created"] is True
    assert result["mode"] == oct(0o700)
    assert new_dir.exists()


@pytest.mark.asyncio
async def test_directory_create_with_root_dir(temp_dir, mock_tool_context):
    """Test directory creation with root_dir from context."""
    # Set root_dir in context
    mock_tool_context.metadata["root_dir"] = str(temp_dir)

    # Use relative path
    input_data = DirectoryCreateInput(
        directory_path="relative/path"
    )

    result = await directory_create_execute(input_data, mock_tool_context)

    assert result["success"] is True
    assert result["created"] is True
    expected_path = Path(temp_dir) / "relative" / "path"
    assert expected_path.exists()
