"""GrepTool v3 - New Tool System Implementation.

Search file contents with regex pattern matching.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

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

    # 3. Compile regex pattern
    try:
        flags = 0 if input.case_sensitive else re.IGNORECASE
        regex = re.compile(input.pattern, flags)
    except re.error as e:
        return {
            "success": False,
            "error": f"Invalid regex pattern: {e}",
            "error_code": "INVALID_REGEX",
            "pattern": input.pattern
        }

    # 4. Search files
    matches = []
    files_searched = 0
    files_with_matches = 0

    search_path = Path(directory)

    # Get files to search
    if input.recursive:
        files = search_path.rglob(input.file_pattern)
    else:
        files = search_path.glob(input.file_pattern)

    # 5. Search in each file
    for file_path in files:
        if not file_path.is_file():
            continue

        files_searched += 1
        file_has_matches = False

        # Search in file
        try:
            with open(file_path, encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    match = regex.search(line)
                    if match:
                        file_has_matches = True
                        match_data = {
                            "file": str(file_path.relative_to(search_path) if file_path.is_relative_to(search_path) else file_path),
                            "line": line.rstrip(),
                            "match": match.group()
                        }

                        if input.include_line_numbers:
                            match_data["line_number"] = line_num

                        matches.append(match_data)

                        # Check max results
                        if len(matches) >= input.max_results:
                            break

        except (UnicodeDecodeError, PermissionError, OSError):
            # Skip files that can't be read
            continue

        if file_has_matches:
            files_with_matches += 1

        # Check if we've reached max results
        if len(matches) >= input.max_results:
            break

    # 6. Return results
    return {
        "success": True,
        "matches": matches,
        "total_matches": len(matches),
        "files_searched": files_searched,
        "files_with_matches": files_with_matches,
        "pattern": input.pattern,
        "directory": directory,
        "truncated": len(matches) >= input.max_results
    }


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
