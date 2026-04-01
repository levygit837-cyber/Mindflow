"""Unit tests for FileFinderToolV3."""

import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from mindflow_backend.agents.tools.filesystem.file_finder_v3 import (
    FileFinderInput,
    FileFinderToolV3,
    file_finder_execute,
)
from mindflow_backend.schemas.tools.context import ToolContext


@pytest.mark.asyncio
async def test_file_finder_basic(temp_dir, mock_tool_context):
    """Test basic file finding by pattern."""
    # Create test files
    (Path(temp_dir) / "test1.txt").touch()
    (Path(temp_dir) / "test2.txt").touch()
    (Path(temp_dir) / "other.py").touch()

    input_data = FileFinderInput(
        pattern="*.txt",
        directory=str(temp_dir),
        recursive=False
    )

    result = await file_finder_execute(input_data, mock_tool_context)

    assert result["success"] is True
    assert result["total_count"] == 2
    assert result["pattern"] == "*.txt"
    assert len(result["files"]) == 2


@pytest.mark.asyncio
async def test_file_finder_recursive(temp_dir, mock_tool_context):
    """Test recursive file finding."""
    # Create nested structure
    (Path(temp_dir) / "file1.txt").touch()
    subdir = Path(temp_dir) / "subdir"
    subdir.mkdir()
    (subdir / "file2.txt").touch()
    (subdir / "file3.txt").touch()

    input_data = FileFinderInput(
        pattern="*.txt",
        directory=str(temp_dir),
        recursive=True
    )

    result = await file_finder_execute(input_data, mock_tool_context)

    assert result["success"] is True
    assert result["total_count"] == 3


@pytest.mark.asyncio
async def test_file_finder_non_recursive(temp_dir, mock_tool_context):
    """Test non-recursive file finding."""
    # Create nested structure
    (Path(temp_dir) / "file1.txt").touch()
    subdir = Path(temp_dir) / "subdir"
    subdir.mkdir()
    (subdir / "file2.txt").touch()

    input_data = FileFinderInput(
        pattern="*.txt",
        directory=str(temp_dir),
        recursive=False
    )

    result = await file_finder_execute(input_data, mock_tool_context)

    assert result["success"] is True
    assert result["total_count"] == 1  # Only top-level file


@pytest.mark.asyncio
async def test_file_finder_size_filter(temp_dir, mock_tool_context):
    """Test file finding with size filters."""
    # Create files with different sizes
    small_file = Path(temp_dir) / "small.txt"
    small_file.write_text("x" * 10)  # 10 bytes

    large_file = Path(temp_dir) / "large.txt"
    large_file.write_text("x" * 1000)  # 1000 bytes

    # Find files larger than 100 bytes
    input_data = FileFinderInput(
        pattern="*.txt",
        directory=str(temp_dir),
        min_size=100
    )

    result = await file_finder_execute(input_data, mock_tool_context)

    assert result["success"] is True
    assert result["total_count"] == 1
    assert result["files"][0]["name"] == "large.txt"


@pytest.mark.asyncio
async def test_file_finder_max_size_filter(temp_dir, mock_tool_context):
    """Test file finding with max size filter."""
    # Create files with different sizes
    small_file = Path(temp_dir) / "small.txt"
    small_file.write_text("x" * 10)

    large_file = Path(temp_dir) / "large.txt"
    large_file.write_text("x" * 1000)

    # Find files smaller than 100 bytes
    input_data = FileFinderInput(
        pattern="*.txt",
        directory=str(temp_dir),
        max_size=100
    )

    result = await file_finder_execute(input_data, mock_tool_context)

    assert result["success"] is True
    assert result["total_count"] == 1
    assert result["files"][0]["name"] == "small.txt"


@pytest.mark.asyncio
async def test_file_finder_date_filter(temp_dir, mock_tool_context):
    """Test file finding with date filters."""
    # Create file
    file_path = Path(temp_dir) / "test.txt"
    file_path.touch()

    # Get today's date
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    # Find files modified today or later
    input_data = FileFinderInput(
        pattern="*.txt",
        directory=str(temp_dir),
        min_date=yesterday
    )

    result = await file_finder_execute(input_data, mock_tool_context)

    assert result["success"] is True
    assert result["total_count"] == 1


@pytest.mark.asyncio
async def test_file_finder_max_results(temp_dir, mock_tool_context):
    """Test max results limit."""
    # Create many files
    for i in range(15):
        (Path(temp_dir) / f"file{i}.txt").touch()

    input_data = FileFinderInput(
        pattern="*.txt",
        directory=str(temp_dir),
        max_results=10
    )

    result = await file_finder_execute(input_data, mock_tool_context)

    assert result["success"] is True
    assert result["total_count"] == 10
    assert result["truncated"] is True


@pytest.mark.asyncio
async def test_file_finder_directory_not_found(mock_tool_context):
    """Test finding in non-existent directory."""
    input_data = FileFinderInput(
        pattern="*.txt",
        directory="/nonexistent/path"
    )

    result = await file_finder_execute(input_data, mock_tool_context)

    assert result["success"] is False
    assert result["error_code"] == "DIRECTORY_NOT_FOUND"


@pytest.mark.asyncio
async def test_file_finder_not_a_directory(temp_dir, mock_tool_context):
    """Test finding in a file instead of directory."""
    file_path = Path(temp_dir) / "file.txt"
    file_path.touch()

    input_data = FileFinderInput(
        pattern="*.txt",
        directory=str(file_path)
    )

    result = await file_finder_execute(input_data, mock_tool_context)

    assert result["success"] is False
    assert result["error_code"] == "NOT_A_DIRECTORY"


@pytest.mark.asyncio
async def test_file_finder_no_matches(temp_dir, mock_tool_context):
    """Test finding with no matches."""
    (Path(temp_dir) / "file.txt").touch()

    input_data = FileFinderInput(
        pattern="*.py",
        directory=str(temp_dir)
    )

    result = await file_finder_execute(input_data, mock_tool_context)

    assert result["success"] is True
    assert result["total_count"] == 0
    assert len(result["files"]) == 0


@pytest.mark.asyncio
async def test_file_finder_returns_metadata(temp_dir, mock_tool_context):
    """Test that finder returns file metadata."""
    file_path = Path(temp_dir) / "test.txt"
    file_path.write_text("content")

    input_data = FileFinderInput(
        pattern="*.txt",
        directory=str(temp_dir)
    )

    result = await file_finder_execute(input_data, mock_tool_context)

    assert result["success"] is True
    file_info = result["files"][0]
    assert "path" in file_info
    assert "name" in file_info
    assert "size" in file_info
    assert "modified" in file_info
    assert "modified_date" in file_info


@pytest.mark.asyncio
async def test_file_finder_with_root_dir(temp_dir, mock_tool_context):
    """Test file finding with root_dir from context."""
    # Create test file
    (Path(temp_dir) / "test.txt").touch()

    # Set root_dir in context
    mock_tool_context.metadata["root_dir"] = str(temp_dir)

    # Use relative path
    input_data = FileFinderInput(
        pattern="*.txt",
        directory="."
    )

    result = await file_finder_execute(input_data, mock_tool_context)

    assert result["success"] is True
    assert result["total_count"] == 1


@pytest.mark.asyncio
async def test_file_finder_invalid_date_format(temp_dir, mock_tool_context):
    """Test file finding with invalid date format."""
    (Path(temp_dir) / "test.txt").touch()

    input_data = FileFinderInput(
        pattern="*.txt",
        directory=str(temp_dir),
        min_date="invalid-date"
    )

    result = await file_finder_execute(input_data, mock_tool_context)

    assert result["success"] is False
    assert result["error_code"] == "INVALID_DATE_FORMAT"
