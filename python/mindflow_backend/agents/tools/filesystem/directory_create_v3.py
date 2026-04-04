"""DirectoryCreateTool v3 - New Tool System Implementation.

Create directories with parent creation and security controls.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.agents.tools.filesystem._legacy_adapter import (
    build_legacy_tool,
    deny_if_permission_blocked,
    flatten_legacy_result,
)
from mindflow_backend.agents.tools.filesystem.operations import DirectoryCreateTool
from mindflow_backend.schemas.tools import build_tool
from mindflow_backend.schemas.tools.context import ToolContext


# ---------------------------------------------------------------------------
# Input Schema
# ---------------------------------------------------------------------------


class DirectoryCreateInput(BaseModel):
    """Input schema for DirectoryCreateTool v3."""

    directory_path: str = Field(
        description="Path to directory to create"
    )
    parents: bool = Field(
        default=True,
        description="Create parent directories if they don't exist"
    )
    exist_ok: bool = Field(
        default=True,
        description="Don't raise error if directory already exists"
    )
    mode: int = Field(
        default=0o755,
        description="Directory permissions (octal, e.g., 0o755)"
    )


# ---------------------------------------------------------------------------
# Execute Function
# ---------------------------------------------------------------------------


async def directory_create_execute(input: DirectoryCreateInput, context: ToolContext) -> dict[str, Any]:
    """Create a directory with security controls.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context

    Returns:
        Dictionary with creation result or error
    """
    permission_error = await deny_if_permission_blocked(
        context,
        tool_name="mkdir",
        input_data=input.model_dump(),
        tool_content=input.directory_path,
        content_key="directory_path",
    )
    if permission_error:
        return permission_error

    tool = build_legacy_tool(DirectoryCreateTool, context)
    result = await tool.execute(
        directory_path=input.directory_path,
        parents=input.parents,
        exist_ok=input.exist_ok,
    )
    flattened = flatten_legacy_result(
        result,
        error_map={
            "create directory blocked in read-only sandbox mode": "READ_ONLY_MODE",
            "workspace security error": "PERMISSION_DENIED",
            "permission denied": "OS_PERMISSION_ERROR",
            "file exists": "DIRECTORY_EXISTS",
            "not a directory": "NOT_A_DIRECTORY",
        },
        default_error_code="CREATE_ERROR",
    )
    if flattened.get("success"):
        flattened.setdefault("directory_path", input.directory_path)
        flattened.setdefault("created", True)
        flattened.setdefault("parents_created", input.parents)
        flattened.setdefault("mode", oct(input.mode))
    return flattened


# ---------------------------------------------------------------------------
# Build Tool
# ---------------------------------------------------------------------------


DirectoryCreateToolV3 = build_tool(
    name="mkdir",
    description=(
        "Create a directory with optional parent creation. "
        "Blocks creation in device and system paths. "
        "Supports custom permissions and exist_ok flag."
    ),
    input_schema=DirectoryCreateInput,
    execute=directory_create_execute,
    is_read_only=False,
    is_destructive=False,  # Creating directories is not destructive
    is_concurrency_safe=False,
)
