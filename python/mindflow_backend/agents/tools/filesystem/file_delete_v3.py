"""FileDeleteTool v3 - New Tool System Implementation.

Delete files with security controls and validation.
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
    # 1. Resolve file path (support root_dir from context)
    file_path = input.file_path
    root_dir = context.metadata.get("root_dir")

    if root_dir and not os.path.isabs(file_path):
        file_path = os.path.join(root_dir, file_path)

    file_path = os.path.abspath(file_path)

    # 2. Security validation: block device files
    if file_path.startswith("/dev/"):
        return {
            "success": False,
            "error": "Device files cannot be deleted",
            "error_code": "DEVICE_FILE_BLOCKED",
            "file_path": file_path
        }

    # 3. Security validation: block system paths
    system_paths = ["/etc", "/usr", "/bin", "/sbin", "/boot", "/sys", "/proc"]
    if any(file_path.startswith(path) for path in system_paths):
        return {
            "success": False,
            "error": f"System paths cannot be deleted: {file_path}",
            "error_code": "SYSTEM_PATH_BLOCKED",
            "file_path": file_path
        }

    # 4. Check permissions (if manager available)
    if context.permission_manager:
        perm_result = await context.check_permission_async(
            tool_name="delete_file",
            input=input.model_dump(),
            tool_content=file_path
        )

        if perm_result.behavior == PermissionBehavior.DENY:
            return {
                "success": False,
                "error": perm_result.message or "Permission denied",
                "error_code": "PERMISSION_DENIED",
                "file_path": file_path
            }

    # 5. Check file exists
    if not os.path.exists(file_path):
        return {
            "success": False,
            "error": f"File not found: {file_path}",
            "error_code": "FILE_NOT_FOUND",
            "file_path": file_path
        }

    if not os.path.isfile(file_path):
        return {
            "success": False,
            "error": f"Not a file: {file_path}",
            "error_code": "NOT_A_FILE",
            "file_path": file_path
        }

    # 6. Get file info before deletion
    try:
        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get file info: {e}",
            "error_code": "STAT_ERROR",
            "file_path": file_path
        }

    # 7. Delete file
    try:
        os.unlink(file_path)

        return {
            "success": True,
            "file_path": file_path,
            "file_name": file_name,
            "file_size": file_size,
            "deleted": True
        }

    except PermissionError as e:
        return {
            "success": False,
            "error": f"Permission denied: {e}",
            "error_code": "OS_PERMISSION_ERROR",
            "file_path": file_path
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to delete file: {e}",
            "error_code": "DELETE_ERROR",
            "file_path": file_path
        }


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
