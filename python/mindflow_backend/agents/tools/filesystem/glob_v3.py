"""GlobTool v3 - New Tool System Implementation.

Find files matching glob patterns.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.agents.tools.filesystem._legacy_adapter import (
    build_legacy_tool,
    flatten_legacy_result,
)
from mindflow_backend.agents.tools.filesystem.search_tools import GlobSearchTool
from mindflow_backend.schemas.tools import build_tool
from mindflow_backend.schemas.tools.context import ToolContext


# ---------------------------------------------------------------------------
# Input Schema
# ---------------------------------------------------------------------------


class GlobInput(BaseModel):
    """Input schema for GlobTool v3."""

    pattern: str = Field(
        description="Glob pattern to match files (e.g., '*.py', '**/*.txt', 'src/**/*.js')"
    )
    directory: str = Field(
        default=".",
        description="Base directory to search in (absolute or relative to root_dir)"
    )
    max_results: int = Field(
        default=200,
        ge=1,
        le=2000,
        description="Maximum number of files to return"
    )
    include_dirs: bool = Field(
        default=False,
        description="Include directories in results (default: files only)"
    )
    absolute_paths: bool = Field(
        default=False,
        description="Return absolute paths instead of relative paths"
    )


# ---------------------------------------------------------------------------
# Execute Function
# ---------------------------------------------------------------------------


async def glob_execute(input: GlobInput, context: ToolContext) -> dict[str, Any]:
    """Execute glob search to find files matching pattern.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context

    Returns:
        Dictionary with matched files or error
    """
    tool = build_legacy_tool(GlobSearchTool, context)
    result = await tool.execute(
        pattern=input.pattern,
        directory=input.directory,
        max_results=input.max_results,
        include_dirs=input.include_dirs,
        absolute_paths=input.absolute_paths,
    )
    flattened = flatten_legacy_result(
        result,
        error_map={
            "directory not found": "DIRECTORY_NOT_FOUND",
            "not a directory": "NOT_A_DIRECTORY",
            "glob search error": "GLOB_ERROR",
        },
        default_error_code="GLOB_ERROR",
    )
    if flattened.get("success"):
        flattened.setdefault("pattern", input.pattern)
    return flattened


# ---------------------------------------------------------------------------
# Build Tool
# ---------------------------------------------------------------------------


GlobToolV3 = build_tool(
    name="glob_search",
    description=(
        "Find files matching glob patterns. "
        "Supports recursive patterns (** wildcard), file/directory filtering, "
        "and returns relative or absolute paths."
    ),
    input_schema=GlobInput,
    execute=glob_execute,
    is_read_only=True,
    is_concurrency_safe=True,
    is_destructive=False,
)
