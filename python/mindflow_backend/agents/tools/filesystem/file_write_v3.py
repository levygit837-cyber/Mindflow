"""FileWriteTool v3 - New Tool System Implementation.

Write file contents with security validation and permission checking.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.agents.tools.filesystem._legacy_adapter import (
    build_legacy_tool,
    deny_if_permission_blocked,
    flatten_legacy_result,
)
from mindflow_backend.agents.tools.filesystem.file_operations import FileWriteTool
from mindflow_backend.schemas.tools import build_tool
from mindflow_backend.schemas.tools.context import ToolContext


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
    permission_error = await deny_if_permission_blocked(
        context,
        tool_name="write_file",
        input_data=input.model_dump(),
        tool_content=input.file_path,
        content_key="file_path",
    )
    if permission_error:
        return permission_error

    tool = build_legacy_tool(FileWriteTool, context)
    result = await tool.execute(
        file_path=input.file_path,
        content=input.content,
        encoding=input.encoding,
        create_dirs=input.create_dirs,
        overwrite=input.overwrite,
    )
    flattened = flatten_legacy_result(
        result,
        error_map={
            "cannot write to device file": "DEVICE_FILE_BLOCKED",
            "restricted path denied: /dev": "DEVICE_FILE_BLOCKED",
            "restricted path denied: /etc": "SYSTEM_PATH_BLOCKED",
            "restricted path denied: /usr": "SYSTEM_PATH_BLOCKED",
            "restricted path denied: /bin": "SYSTEM_PATH_BLOCKED",
            "restricted path denied: /sbin": "SYSTEM_PATH_BLOCKED",
            "restricted path denied: /boot": "SYSTEM_PATH_BLOCKED",
            "restricted path denied: /sys": "SYSTEM_PATH_BLOCKED",
            "restricted path denied: /proc": "SYSTEM_PATH_BLOCKED",
            "overwrite=false": "FILE_EXISTS",
            "parent directory does not exist": "DIRECTORY_NOT_FOUND",
            "permission denied": "OS_PERMISSION_ERROR",
            "workspace security error": "PERMISSION_DENIED",
            "encoding error": "ENCODING_ERROR",
        },
        default_error_code="WRITE_ERROR",
    )
    if flattened.get("success") and "file_size" not in flattened and "bytes_written" in flattened:
        flattened["file_size"] = flattened["bytes_written"]
    return flattened


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
