"""FileFinderTool v3 - New Tool System Implementation.

Find files by name pattern with size and date filters.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.schemas.tools import build_tool
from mindflow_backend.schemas.tools.context import ToolContext


# ---------------------------------------------------------------------------
# Input Schema
# ---------------------------------------------------------------------------


class FileFinderInput(BaseModel):
    """Input schema for FileFinderTool v3."""

    pattern: str = Field(
        description="File name pattern (glob style, e.g., '*.py', 'test_*.txt')"
    )
    directory: str = Field(
        default=".",
        description="Directory to search in"
    )
    recursive: bool = Field(
        default=True,
        description="Search recursively in subdirectories"
    )
    min_size: int | None = Field(
        default=None,
        ge=0,
        description="Minimum file size in bytes"
    )
    max_size: int | None = Field(
        default=None,
        ge=0,
        description="Maximum file size in bytes"
    )
    min_date: str | None = Field(
        default=None,
        description="Minimum modification date (YYYY-MM-DD)"
    )
    max_date: str | None = Field(
        default=None,
        description="Maximum modification date (YYYY-MM-DD)"
    )
    max_results: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of results to return"
    )


# ---------------------------------------------------------------------------
# Execute Function
# ---------------------------------------------------------------------------


async def file_finder_execute(input: FileFinderInput, context: ToolContext) -> dict[str, Any]:
    """Find files matching pattern with optional filters.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context

    Returns:
        Dictionary with found files or error
    """
    # 1. Resolve directory (support root_dir from context)
    directory = input.directory
    root_dir = context.metadata.get("root_dir")

    if root_dir and not os.path.isabs(directory):
        directory = os.path.join(root_dir, directory)

    directory = os.path.abspath(directory)

    # 2. Check directory exists
    if not os.path.exists(directory):
        return {
            "success": False,
            "error": f"Directory not found: {directory}",
            "error_code": "DIRECTORY_NOT_FOUND"
        }

    if not os.path.isdir(directory):
        return {
            "success": False,
            "error": f"Not a directory: {directory}",
            "error_code": "NOT_A_DIRECTORY"
        }

    # 3. Parse date filters
    min_timestamp = None
    max_timestamp = None

    if input.min_date:
        try:
            min_timestamp = datetime.strptime(input.min_date, "%Y-%m-%d").timestamp()
        except ValueError as e:
            return {
                "success": False,
                "error": f"Invalid min_date format: {e}. Use YYYY-MM-DD",
                "error_code": "INVALID_DATE_FORMAT"
            }

    if input.max_date:
        try:
            max_timestamp = datetime.strptime(input.max_date, "%Y-%m-%d").timestamp()
        except ValueError as e:
            return {
                "success": False,
                "error": f"Invalid max_date format: {e}. Use YYYY-MM-DD",
                "error_code": "INVALID_DATE_FORMAT"
            }

    # 4. Search for files
    try:
        files = []
        search_path = Path(directory)

        # Use rglob for recursive, glob for non-recursive
        if input.recursive:
            matches = search_path.rglob(input.pattern)
        else:
            matches = search_path.glob(input.pattern)

        for file_path in matches:
            # Only include files, not directories
            if not file_path.is_file():
                continue

            try:
                stat = file_path.stat()

                # Apply size filters
                if input.min_size is not None and stat.st_size < input.min_size:
                    continue

                if input.max_size is not None and stat.st_size > input.max_size:
                    continue

                # Apply date filters
                if min_timestamp is not None and stat.st_mtime < min_timestamp:
                    continue

                if max_timestamp is not None and stat.st_mtime > max_timestamp:
                    continue

                # Add to results
                files.append({
                    "path": str(file_path),
                    "name": file_path.name,
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "modified_date": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })

            except (OSError, PermissionError):
                # Skip files we can't access
                continue

            # Check max results limit
            if len(files) >= input.max_results:
                break

        return {
            "success": True,
            "files": files,
            "total_count": len(files),
            "truncated": len(files) >= input.max_results,
            "pattern": input.pattern,
            "directory": directory
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"File finder error: {e}",
            "error_code": "SEARCH_ERROR",
            "pattern": input.pattern
        }


# ---------------------------------------------------------------------------
# Build Tool
# ---------------------------------------------------------------------------


FileFinderToolV3 = build_tool(
    name="file_finder",
    description=(
        "Find files by name pattern with optional size and date filters. "
        "Supports recursive search and glob patterns. "
        "Returns file metadata including size and modification date."
    ),
    input_schema=FileFinderInput,
    execute=file_finder_execute,
    is_read_only=True,
    is_concurrency_safe=True,
    is_destructive=False,
)

# Compatibility alias
FindFilesToolV3 = FileFinderToolV3
