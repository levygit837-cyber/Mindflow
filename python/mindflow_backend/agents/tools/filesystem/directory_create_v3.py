"""DirectoryCreateTool v3 - New Tool System Implementation.

Create directories with parent creation and security controls.
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
    # 1. Resolve directory path (support root_dir from context)
    directory_path = input.directory_path
    root_dir = context.metadata.get("root_dir")

    if root_dir and not os.path.isabs(directory_path):
        directory_path = os.path.join(root_dir, directory_path)

    directory_path = os.path.abspath(directory_path)

    # 2. Security validation: block device paths
    if directory_path.startswith("/dev/"):
        return {
            "success": False,
            "error": "Cannot create directories in /dev",
            "error_code": "DEVICE_PATH_BLOCKED",
            "directory_path": directory_path
        }

    # 3. Security validation: block system paths
    system_paths = ["/etc", "/usr", "/bin", "/sbin", "/boot", "/sys", "/proc"]
    if any(directory_path.startswith(path) for path in system_paths):
        return {
            "success": False,
            "error": f"Cannot create directories in system paths: {directory_path}",
            "error_code": "SYSTEM_PATH_BLOCKED",
            "directory_path": directory_path
        }

    # 4. Check permissions (if manager available)
    if context.permission_manager:
        perm_result = await context.check_permission_async(
            tool_name="mkdir",
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

    # 5. Check if directory already exists
    if os.path.exists(directory_path):
        if not input.exist_ok:
            return {
                "success": False,
                "error": f"Directory already exists: {directory_path}",
                "error_code": "DIRECTORY_EXISTS",
                "directory_path": directory_path
            }

        if not os.path.isdir(directory_path):
            return {
                "success": False,
                "error": f"Path exists but is not a directory: {directory_path}",
                "error_code": "NOT_A_DIRECTORY",
                "directory_path": directory_path
            }

        return {
            "success": True,
            "directory_path": directory_path,
            "created": False,
            "already_existed": True
        }

    # 6. Create directory
    try:
        path_obj = Path(directory_path)
        path_obj.mkdir(parents=input.parents, exist_ok=input.exist_ok, mode=input.mode)

        return {
            "success": True,
            "directory_path": directory_path,
            "created": True,
            "parents_created": input.parents,
            "mode": oct(input.mode)
        }

    except FileNotFoundError as e:
        return {
            "success": False,
            "error": f"Parent directory not found: {e}",
            "error_code": "PARENT_NOT_FOUND",
            "directory_path": directory_path
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
            "error": f"Failed to create directory: {e}",
            "error_code": "CREATE_ERROR",
            "directory_path": directory_path
        }


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
