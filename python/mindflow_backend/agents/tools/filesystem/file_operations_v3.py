"""FileReadTool v3 - New Tool System Implementation.

This is a pilot migration of FileReadTool to the new Tool system using build_tool().

Features:
- Type-safe input validation (Pydantic)
- Integrated permission checking (ToolContext)
- Explicit metadata (is_read_only, is_concurrency_safe)
- Device file blocking
- Symlink validation
- Pagination support (offset/limit)
- Line numbers support
- Multiple encodings
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.agents.tools.filesystem._legacy_adapter import (
    build_legacy_tool,
    deny_if_permission_blocked,
    flatten_legacy_result,
)
from mindflow_backend.agents.tools.filesystem.file_operations import FileReadTool
from mindflow_backend.schemas.tools import build_tool
from mindflow_backend.schemas.tools.context import ToolContext


# ---------------------------------------------------------------------------
# Input Schema
# ---------------------------------------------------------------------------


class FileReadInput(BaseModel):
    """Input schema for FileReadTool v3."""

    file_path: str = Field(
        description="Path to file to read (absolute or relative to root_dir)"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Line number to start reading from (0-indexed)"
    )
    limit: int = Field(
        default=2000,
        ge=1,
        le=10000,
        description="Maximum number of lines to read"
    )
    encoding: str = Field(
        default="utf-8",
        description="File encoding (utf-8, latin-1, ascii, etc.)"
    )
    include_line_numbers: bool = Field(
        default=False,
        description="Prefix each line with line number (format: 'N\\tline')"
    )


# ---------------------------------------------------------------------------
# Execute Function
# ---------------------------------------------------------------------------


async def file_read_execute(input: FileReadInput, context: ToolContext) -> dict[str, Any]:
    """Execute file read with full validation and security checks.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context (permissions, abort signal, etc.)

    Returns:
        Dictionary with success status and file content or error
    """
    permission_error = await deny_if_permission_blocked(
        context,
        tool_name="read_file",
        input_data=input.model_dump(),
        tool_content=input.file_path,
        content_key="file_path",
    )
    if permission_error:
        return permission_error

    tool = build_legacy_tool(FileReadTool, context)
    result = await tool.execute(
        file_path=input.file_path,
        offset=input.offset,
        limit=input.limit,
        encoding=input.encoding,
        include_line_numbers=input.include_line_numbers,
    )
    flattened = flatten_legacy_result(
        result,
        error_map={
            "cannot read from device file": "DEVICE_FILE_BLOCKED",
            "restricted path denied: /dev": "DEVICE_FILE_BLOCKED",
            "file not found": "FILE_NOT_FOUND",
            "path is not a file": "NOT_A_FILE",
            "encoding error": "ENCODING_ERROR",
            "permission denied": "OS_PERMISSION_ERROR",
            "workspace security error": "PERMISSION_DENIED",
        },
        default_error_code="READ_ERROR",
    )
    if flattened.get("success"):
        flattened.setdefault("file_path", input.file_path)
    return flattened


# ---------------------------------------------------------------------------
# Build Tool
# ---------------------------------------------------------------------------


FileReadToolV3 = build_tool(
    name="read_file",
    description=(
        "Read file contents with pagination, line numbers, and security validation. "
        "Supports offset/limit for large files, multiple encodings, device file blocking, "
        "and permission checking. Returns structured result with metadata."
    ),
    input_schema=FileReadInput,
    execute=file_read_execute,
    is_read_only=True,
    is_concurrency_safe=True,
)
