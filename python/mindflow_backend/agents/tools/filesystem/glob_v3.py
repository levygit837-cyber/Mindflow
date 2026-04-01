"""GlobTool v3 - New Tool System Implementation.

Find files matching glob patterns.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

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

    # 3. Execute glob search
    try:
        base_path = Path(directory)

        # Use glob or rglob based on pattern
        if "**" in input.pattern:
            # Recursive glob
            matches = base_path.glob(input.pattern)
        else:
            # Non-recursive glob
            matches = base_path.glob(input.pattern)

        # 4. Filter and collect results
        files = []
        dirs = []

        for match in matches:
            # Check max results
            if len(files) + len(dirs) >= input.max_results:
                break

            # Determine path format
            if input.absolute_paths:
                path_str = str(match.absolute())
            else:
                try:
                    path_str = str(match.relative_to(base_path))
                except ValueError:
                    path_str = str(match)

            # Categorize
            if match.is_file():
                files.append(path_str)
            elif match.is_dir() and input.include_dirs:
                dirs.append(path_str)

        # 5. Return results
        result = {
            "success": True,
            "files": files,
            "total_files": len(files),
            "pattern": input.pattern,
            "directory": directory,
            "truncated": (len(files) + len(dirs)) >= input.max_results
        }

        if input.include_dirs:
            result["directories"] = dirs
            result["total_directories"] = len(dirs)
            result["total_matches"] = len(files) + len(dirs)
        else:
            result["total_matches"] = len(files)

        return result

    except Exception as e:
        return {
            "success": False,
            "error": f"Glob search error: {e}",
            "error_code": "GLOB_ERROR",
            "pattern": input.pattern
        }


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
