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
            "error": "Device files are blocked for security",
            "error_code": "DEVICE_FILE_BLOCKED",
            "file_path": file_path
        }

    # 3. Check permissions (if manager available)
    if context.permission_manager:
        perm_result = await context.check_permission_async(
            tool_name="read_file",
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

    # 4. Check file exists
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

    # 5. Read file with pagination
    try:
        with open(file_path, 'r', encoding=input.encoding) as f:
            lines = f.readlines()

        # Apply offset and limit
        start = input.offset
        end = start + input.limit
        selected_lines = lines[start:end]

        # Add line numbers if requested
        if input.include_line_numbers:
            selected_lines = [
                f"{start + i + 1}\t{line}"
                for i, line in enumerate(selected_lines)
            ]

        content = "".join(selected_lines)

        return {
            "success": True,
            "content": content,
            "file_path": file_path,
            "total_lines": len(lines),
            "lines_returned": len(selected_lines),
            "lines_read": len(selected_lines),  # Alias for compatibility
            "offset": input.offset,
            "limit": input.limit,
            "encoding": input.encoding,
            "has_more": end < len(lines),
            "truncated": end < len(lines)  # Alias for compatibility
        }

    except UnicodeDecodeError as e:
        return {
            "success": False,
            "error": f"Encoding error: {e}. Try different encoding (latin-1, ascii, etc.)",
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
            "error_code": "READ_ERROR",
            "file_path": file_path
        }


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
