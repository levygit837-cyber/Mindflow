"""DirectoryListTool v3 - New Tool System Implementation.

List directory contents with security controls and filtering.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.agents.tools.filesystem._legacy_adapter import (
    build_legacy_tool,
    deny_if_permission_blocked,
    flatten_legacy_result,
)
from mindflow_backend.agents.tools.filesystem.file_operations import DirectoryListTool
from mindflow_backend.schemas.tools import build_tool
from mindflow_backend.schemas.tools.context import ToolContext


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
    permission_error = await deny_if_permission_blocked(
        context,
        tool_name="list_dir",
        input_data=input.model_dump(),
        tool_content=input.directory_path,
        content_key="directory_path",
    )
    if permission_error:
        return permission_error

    tool = build_legacy_tool(DirectoryListTool, context)
    result = await tool.execute(
        directory_path=input.directory_path,
        include_hidden=input.include_hidden,
        include_size=input.include_size,
        include_type=input.include_type,
        max_items=input.max_items,
    )
    return flatten_legacy_result(
        result,
        error_map={
            "restricted path denied: /dev": "DEVICE_PATH_BLOCKED",
            "directory not found": "DIRECTORY_NOT_FOUND",
            "path is not a directory": "NOT_A_DIRECTORY",
            "permission denied": "OS_PERMISSION_ERROR",
            "workspace security error": "PERMISSION_DENIED",
        },
        default_error_code="LIST_ERROR",
    )


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
