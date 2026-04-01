"""FileWriteTool v3 - New Tool System Implementation.

Write file contents with security validation and permission checking.
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


class FileWriteInput(BaseModel):
    """Input schema for FileWriteTool v3."""

    file_path: str = Field(
        description="Path to file to write (absolute or relative to root_dir)"
    )
    content: str = Field(
        description="Content to write to the file"
    )
    encoding: str = Field(
        default="utf-8",
        description="File encoding (utf-8, latin-1, ascii, etc.)"
    )
    create_dirs: bool = Field(
        default=True,
        description="Create parent directories if they don't exist"
    )
    overwrite: bool = Field(
        default=True,
        description="Overwrite file if it exists (if False, will fail if file exists)"
    )


# ---------------------------------------------------------------------------
# Execute Function
# ---------------------------------------------------------------------------


async def file_write_execute(input: FileWriteInput, context: ToolContext) -> dict[str, Any]:
    """Execute file write with full validation and security checks.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context (permissions, abort signal, etc.)

    Returns:
        Dictionary with success status and file metadata or error
    """
    # 1. Resolve path (support root_dir from context)
    file_path = input.file_path
    root_dir = context.metadata.get("root_dir")

    if root_dir and not os.path.isabs(file_path):
        file_path = os.path.join(root_dir, file_path)

    file_path = os.path.abspath(file_path)

    # 2. Security validation: device files
    if file_path.startswith("/dev/"):
        return {
            "success": False,
            "error": "Cannot write to device files",
            "error_code": "DEVICE_FILE_BLOCKED",
            "file_path": file_path
        }

    # 3. Security validation: system paths
    restricted_paths = ["/etc", "/usr", "/bin", "/sbin", "/boot", "/sys", "/proc"]
    for restricted in restricted_paths:
        if file_path.startswith(restricted):
            return {
                "success": False,
                "error": f"Cannot write to system path: {restricted}",
                "error_code": "SYSTEM_PATH_BLOCKED",
                "file_path": file_path
            }

    # 4. Check permissions (if manager available)
    if context.permission_manager:
        perm_result = await context.check_permission_async(
            tool_name="write_file",
            input=input.dict(),
            tool_content=file_path
        )

        if perm_result.behavior == PermissionBehavior.DENY:
            return {
                "success": False,
                "error": perm_result.reason or "Permission denied",
                "error_code": "PERMISSION_DENIED",
                "file_path": file_path
            }

    # 5. Check if file exists and overwrite flag
    file_exists = os.path.exists(file_path)
    if file_exists and not input.overwrite:
        return {
            "success": False,
            "error": f"File already exists and overwrite=False: {file_path}",
            "error_code": "FILE_EXISTS",
            "file_path": file_path
        }

    # 6. Create parent directories if needed
    if input.create_dirs:
        parent_dir = os.path.dirname(file_path)
        if parent_dir and not os.path.exists(parent_dir):
            try:
                os.makedirs(parent_dir, exist_ok=True)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to create parent directories: {e}",
                    "error_code": "MKDIR_ERROR",
                    "file_path": file_path
                }

    # 7. Write file
    try:
        # Check if parent directory exists when create_dirs=False
        if not input.create_dirs:
            parent_dir = os.path.dirname(file_path)
            if parent_dir and not os.path.exists(parent_dir):
                return {
                    "success": False,
                    "error": f"Parent directory does not exist: {parent_dir}",
                    "error_code": "DIRECTORY_NOT_FOUND",
                    "file_path": file_path
                }

        with open(file_path, 'w', encoding=input.encoding) as f:
            f.write(input.content)

        # Get file stats
        file_size = os.path.getsize(file_path)
        line_count = input.content.count('\n') + 1 if input.content else 0

        return {
            "success": True,
            "file_path": file_path,
            "file_size": file_size,
            "bytes_written": file_size,  # Alias for compatibility
            "line_count": line_count,
            "encoding": input.encoding,
            "created": not file_exists,
            "overwritten": file_exists
        }

    except UnicodeEncodeError as e:
        return {
            "success": False,
            "error": f"Encoding error: {e}. Try different encoding.",
            "error_code": "ENCODING_ERROR",
            "file_path": file_path,
            "attempted_encoding": input.encoding
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
            "error": str(e),
            "error_code": "WRITE_ERROR",
            "file_path": file_path
        }


# ---------------------------------------------------------------------------
# Build Tool
# ---------------------------------------------------------------------------


FileWriteToolV3 = build_tool(
    name="write_file",
    description=(
        "Write content to a file with security validation and permission checking. "
        "Supports creating parent directories, overwrite control, multiple encodings, "
        "and blocks writes to system/device files. Returns file metadata on success."
    ),
    input_schema=FileWriteInput,
    execute=file_write_execute,
    is_read_only=False,
    is_destructive=True,  # Writing is destructive
    is_concurrency_safe=False,  # File writes are not concurrency-safe
)
