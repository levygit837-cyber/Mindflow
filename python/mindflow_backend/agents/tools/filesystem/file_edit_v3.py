"""FileEditTool v3 - New Tool System Implementation.

Edit file contents by replacing old_string with new_string.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.agents.tools.filesystem._legacy_adapter import (
    build_legacy_tool,
    deny_if_permission_blocked,
    flatten_legacy_result,
)
from mindflow_backend.agents.tools.filesystem.file_operations import FileEditTool
from mindflow_backend.schemas.tools import build_tool
from mindflow_backend.schemas.tools.context import ToolContext


# ---------------------------------------------------------------------------
# Input Schema
# ---------------------------------------------------------------------------


class FileEditInput(BaseModel):
    """Input schema for FileEditTool v3."""

    file_path: str = Field(
        description="Path to file to edit (absolute or relative to root_dir)"
    )
    old_string: str = Field(
        description="String to find and replace in the file"
    )
    new_string: str = Field(
        description="String to replace old_string with"
    )
    count: int = Field(
        default=1,
        ge=-1,
        description="Number of replacements (-1 for all occurrences, default 1)"
    )
    encoding: str = Field(
        default="utf-8",
        description="File encoding (utf-8, latin-1, ascii, etc.)"
    )


# ---------------------------------------------------------------------------
# Execute Function
# ---------------------------------------------------------------------------


async def file_edit_execute(input: FileEditInput, context: ToolContext) -> dict[str, Any]:
    """Execute file edit with full validation and security checks.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context (permissions, abort signal, etc.)

    Returns:
        Dictionary with success status and replacement count or error
    """
    permission_error = await deny_if_permission_blocked(
        context,
        tool_name="edit_file",
        input_data=input.model_dump(),
        tool_content=input.file_path,
        content_key="file_path",
    )
    if permission_error:
        return permission_error

    tool = build_legacy_tool(FileEditTool, context)
    result = await tool.execute(
        file_path=input.file_path,
        old_string=input.old_string,
        new_string=input.new_string,
        count=input.count,
        encoding=input.encoding,
    )
    return flatten_legacy_result(
        result,
        error_map={
            "cannot edit device file": "DEVICE_FILE_BLOCKED",
            "restricted path denied: /dev": "DEVICE_FILE_BLOCKED",
            "restricted path denied: /etc": "SYSTEM_PATH_BLOCKED",
            "restricted path denied: /usr": "SYSTEM_PATH_BLOCKED",
            "restricted path denied: /bin": "SYSTEM_PATH_BLOCKED",
            "restricted path denied: /sbin": "SYSTEM_PATH_BLOCKED",
            "restricted path denied: /boot": "SYSTEM_PATH_BLOCKED",
            "restricted path denied: /sys": "SYSTEM_PATH_BLOCKED",
            "restricted path denied: /proc": "SYSTEM_PATH_BLOCKED",
            "file not found": "FILE_NOT_FOUND",
            "path is not a file": "NOT_A_FILE",
            "old_string not found": "STRING_NOT_FOUND",
            "permission denied": "OS_PERMISSION_ERROR",
            "workspace security error": "PERMISSION_DENIED",
            "encoding error": "ENCODING_ERROR",
        },
        default_error_code="WRITE_ERROR",
    )


# ---------------------------------------------------------------------------
# Build Tool
# ---------------------------------------------------------------------------


FileEditToolV3 = build_tool(
    name="edit_file",
    description=(
        "Edit a file by replacing old_string with new_string. "
        "Supports single or multiple replacements, encoding options, "
        "and security validation. Blocks edits to system/device files."
    ),
    input_schema=FileEditInput,
    execute=file_edit_execute,
    is_read_only=False,
    is_destructive=True,  # Editing is destructive
    is_concurrency_safe=False,  # File edits are not concurrency-safe
)
