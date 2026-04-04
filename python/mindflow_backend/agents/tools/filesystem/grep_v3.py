"""GrepTool v3 - New Tool System Implementation.

Search file contents with regex pattern matching.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.agents.tools.filesystem._legacy_adapter import (
    build_legacy_tool,
    flatten_legacy_result,
)
from mindflow_backend.agents.tools.filesystem.search_tools import GrepSearchTool
from mindflow_backend.schemas.tools import build_tool
from mindflow_backend.schemas.tools.context import ToolContext


# ---------------------------------------------------------------------------
# Input Schema
# ---------------------------------------------------------------------------


class GrepInput(BaseModel):
    """Input schema for GrepTool v3."""

    pattern: str = Field(
        description="Regex pattern to search for in file contents"
    )
    directory: str = Field(
        default=".",
        description="Directory to search in (absolute or relative to root_dir)"
    )
    file_pattern: str = Field(
        default="*",
        description="Glob pattern to filter files (e.g., '*.py', '*.txt')"
    )
    recursive: bool = Field(
        default=True,
        description="Search recursively in subdirectories"
    )
    case_sensitive: bool = Field(
        default=False,
        description="Case-sensitive pattern matching"
    )
    max_results: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of matches to return"
    )
    include_line_numbers: bool = Field(
        default=True,
        description="Include line numbers in results"
    )


# ---------------------------------------------------------------------------
# Execute Function
# ---------------------------------------------------------------------------


async def grep_execute(input: GrepInput, context: ToolContext) -> dict[str, Any]:
    """Execute grep search with regex pattern matching.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context

    Returns:
        Dictionary with search results or error
    """
    tool = build_legacy_tool(GrepSearchTool, context)
    result = await tool.execute(
        pattern=input.pattern,
        directory=input.directory,
        file_pattern=input.file_pattern,
        recursive=input.recursive,
        case_sensitive=input.case_sensitive,
        max_results=input.max_results,
        include_line_numbers=input.include_line_numbers,
    )
    flattened = flatten_legacy_result(
        result,
        error_map={
            "directory not found": "DIRECTORY_NOT_FOUND",
            "not a directory": "NOT_A_DIRECTORY",
            "invalid regex pattern": "INVALID_REGEX",
        },
        default_error_code="SEARCH_ERROR",
    )
    if flattened.get("success"):
        flattened.setdefault("pattern", input.pattern)
    return flattened


# ---------------------------------------------------------------------------
# Build Tool
# ---------------------------------------------------------------------------


GrepToolV3 = build_tool(
    name="grep_search",
    description=(
        "Search file contents using regex patterns. "
        "Supports recursive search, file filtering, case-sensitive/insensitive matching, "
        "and returns matches with line numbers and context."
    ),
    input_schema=GrepInput,
    execute=grep_execute,
    is_read_only=True,
    is_concurrency_safe=True,
    is_destructive=False,
)
