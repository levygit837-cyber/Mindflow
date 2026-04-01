"""DirectoryListTool v3 - New Tool System Implementation.

List directory contents with security controls and filtering.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.schemas.tools import build_tool
from mindflow_backend.schemas.tools.context import ToolContext
from mindflow_backend.schemas.tools.permission import PermissionBehavior


# ---------------------------------------------------------------------------
# Input Schema
# ---------------------------------------------------------------------------


class DirectoryListInput(BaseModel):
    """Input schema for DirectoryListTool v3."""

    directory_path: str = Field(
        description="Path to directory to list"
    )
    include_hidden: bool = Field(
        default=False,
        description="Include hidden files (starting with .)"
    )
    include_size: bool = Field(
        default=False,
        description="Include file sizes in results"
    )
    include_type: bool = Field(
        default=True,
        description="Include file type (file/directory)"
    )
    max_items: int = Field(
        default=1000,
        ge=1,
        le=10000,
        description="Maximum number of items to return"
    )


# ---------------------------------------------------------------------------
# Execute Function
# ---------------------------------------------------------------------------


async def directory_list_execute(input: DirectoryListInput, context: ToolContext) -> dict[str, Any]:
    """List directory contents with security controls.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context

    Returns:
        Dictionary with directory listing or error
    """
    # 1. Resolve directory path (support root_dir from context)
    directory_path = input.directory_path
    root_dir = context.metadata.get("root_dir")

    if root_dir and not os.path.isabs(directory_path):
        directory_path = os.path.join(root_dir, directory_path)

    directory_path = os.path.abspath(directory_path)

    # 2. Security validation: block device files
    if directory_path.startswith("/dev/"):
        return {
            "success": False,
            "error": "Device paths are not allowed",
            "error_code": "DEVICE_PATH_BLOCKED",
            "directory_path": directory_path
        }

    # 3. Check permissions (if manager available)
    if context.permission_manager:
        perm_result = await context.check_permission_async(
            tool_name="list_dir",
            input=input.model_dump(),
            tool_content=directory_path
        )

        if perm_result.behavior == PermissionBehavior.DENY:
            return {
                "success": False,
                "error": perm_result.message or "Permission denied",
                "error_code": "PERMISSION_DENIED",
                "directory_path": directory_path
            }

    # 4. Check directory exists
    if not os.path.exists(directory_path):
        return {
            "success": False,
            "error": f"Directory not found: {directory_path}",
            "error_code": "DIRECTORY_NOT_FOUND",
            "directory_path": directory_path
        }

    if not os.path.isdir(directory_path):
        return {
            "success": False,
            "error": f"Not a directory: {directory_path}",
            "error_code": "NOT_A_DIRECTORY",
            "directory_path": directory_path
        }

    # 5. List directory contents
    try:
        entries = []
        path_obj = Path(directory_path)

        for item in path_obj.iterdir():
            # Skip hidden files if not requested
            if not input.include_hidden and item.name.startswith('.'):
                continue

            # Check max items limit
            if len(entries) >= input.max_items:
                break

            entry = {
                "name": item.name,
                "path": str(item)
            }

            # Add type information
            if input.include_type:
                if item.is_file():
                    entry["type"] = "file"
                elif item.is_dir():
                    entry["type"] = "directory"
                elif item.is_symlink():
                    entry["type"] = "symlink"
                else:
                    entry["type"] = "other"

            # Add size information
            if input.include_size:
                try:
                    if item.is_file():
                        entry["size"] = item.stat().st_size
                    elif item.is_dir():
                        entry["size"] = 0  # Directories don't have meaningful size
                except (OSError, PermissionError):
                    entry["size"] = None

            entries.append(entry)

        return {
            "success": True,
            "directory_path": directory_path,
            "entries": entries,
            "total_count": len(entries),
            "truncated": len(entries) >= input.max_items
        }

    except PermissionError as e:
        return {
            "success": False,
            "error": f"Permission denied: {e}",
            "error_code": "OS_PERMISSION_ERROR",
            "directory_path": directory_path
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to list directory: {e}",
            "error_code": "LIST_ERROR",
            "directory_path": directory_path
        }


# ---------------------------------------------------------------------------
# Build Tool
# ---------------------------------------------------------------------------


DirectoryListToolV3 = build_tool(
    name="list_dir",
    description=(
        "List directory contents with filtering options. "
        "Returns file names, types, and optionally sizes. "
        "Supports hidden file filtering and result limiting."
    ),
    input_schema=DirectoryListInput,
    execute=directory_list_execute,
    is_read_only=True,
    is_concurrency_safe=True,
    is_destructive=False,
)
