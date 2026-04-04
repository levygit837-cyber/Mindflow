"""FileDeleteTool v3 - New Tool System Implementation.

Delete files with security controls and validation.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.agents.tools.filesystem._legacy_adapter import (
    build_legacy_tool,
    deny_if_permission_blocked,
    flatten_legacy_result,
)
from mindflow_backend.agents.tools.filesystem.file_operations import FileDeleteTool
from mindflow_backend.schemas.tools import build_tool
from mindflow_backend.schemas.tools.context import ToolContext


# ---------------------------------------------------------------------------
# Input Schema
# ---------------------------------------------------------------------------


class FileDeleteInput(BaseModel):
    """Input schema for FileDeleteTool v3."""

    file_path: str = Field(
        description="Path to file to delete"
    )
    confirm: bool = Field(
        default=False,
        description="Confirmation flag for destructive operation"
    )


# ---------------------------------------------------------------------------
# Execute Function
# ---------------------------------------------------------------------------


async def file_delete_execute(input: FileDeleteInput, context: ToolContext) -> dict[str, Any]:
    """Delete a file with security controls.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context

    Returns:
        Dictionary with deletion result or error
    """
    permission_error = await deny_if_permission_blocked(
        context,
        tool_name="delete_file",
        input_data=input.model_dump(),
        tool_content=input.file_path,
        content_key="file_path",
    )
    if permission_error:
        return permission_error

    tool = build_legacy_tool(FileDeleteTool, context)
    result = await tool.execute(file_path=input.file_path, confirm=input.confirm)
    return flatten_legacy_result(
        result,
        error_map={
            "restricted path denied: /dev": "DEVICE_FILE_BLOCKED",
            "restricted path denied: /etc": "SYSTEM_PATH_BLOCKED",
            "restricted path denied: /usr": "SYSTEM_PATH_BLOCKED",
            "restricted path denied: /bin": "SYSTEM_PATH_BLOCKED",
            "restricted path denied: /sbin": "SYSTEM_PATH_BLOCKED",
            "restricted path denied: /boot": "SYSTEM_PATH_BLOCKED",
            "restricted path denied: /sys": "SYSTEM_PATH_BLOCKED",
            "restricted path denied: /proc": "SYSTEM_PATH_BLOCKED",
            "path not found": "FILE_NOT_FOUND",
            "path is neither file nor directory": "NOT_A_FILE",
            "permission denied": "OS_PERMISSION_ERROR",
            "workspace security error": "PERMISSION_DENIED",
        },
        default_error_code="DELETE_ERROR",
    )


# ---------------------------------------------------------------------------
# Build Tool
# ---------------------------------------------------------------------------


FileDeleteToolV3 = build_tool(
    name="delete_file",
    description=(
        "Delete a file with security controls. "
        "Blocks deletion of device files and system paths. "
        "Returns file information before deletion."
    ),
    input_schema=FileDeleteInput,
    execute=file_delete_execute,
    is_read_only=False,
    is_destructive=True,  # Irreversible operation
    is_concurrency_safe=False,
)
