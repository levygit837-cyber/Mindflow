"""FileFinderTool v3 - New Tool System Implementation.

Find files by name pattern with size and date filters.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.agents.tools.filesystem._legacy_adapter import (
    build_legacy_tool,
    flatten_legacy_result,
)
from mindflow_backend.agents.tools.filesystem.search_tools import FileFinderTool
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
    tool = build_legacy_tool(FileFinderTool, context)
    result = await tool.execute(
        pattern=input.pattern,
        directory=input.directory,
        recursive=input.recursive,
        min_size=input.min_size,
        max_size=input.max_size,
        min_date=input.min_date,
        max_date=input.max_date,
        max_results=input.max_results,
    )
    flattened = flatten_legacy_result(
        result,
        error_map={
            "directory not found": "DIRECTORY_NOT_FOUND",
            "not a directory": "NOT_A_DIRECTORY",
            "does not match format": "INVALID_DATE_FORMAT",
            "time data": "INVALID_DATE_FORMAT",
        },
        default_error_code="SEARCH_ERROR",
    )
    if flattened.get("success"):
        flattened.setdefault("pattern", input.pattern)
    return flattened


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
