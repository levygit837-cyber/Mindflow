"""FileReadTool - Callable Pattern Implementation.

Migrated from file_operations_v3.py to use the new callable pattern.
This eliminates LangChain dependency and provides direct callable interface.

Features:
- Type-safe input validation (Pydantic)
- Direct callable (no wrapper needed)
- ToolResult return type
- Integrated permission checking
- Device file blocking
- Pagination support (offset/limit)
- Line numbers support
- Multiple encodings
- Concurrent-safe (can read multiple files in parallel)
"""

from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.schemas.tools.callable import CallableToolResult, ProgressCallback
from mindflow_backend.schemas.tools.callable_builder import build_readonly_tool
from mindflow_backend.schemas.tools.context import ToolContext
from mindflow_backend.schemas.tools.permission import PermissionBehavior


# ---------------------------------------------------------------------------
# Input Schema
# ---------------------------------------------------------------------------


class FileReadInput(BaseModel):
    """Input schema for FileReadTool callable."""

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
# Implementation
# ---------------------------------------------------------------------------


async def file_read_impl(
    input: FileReadInput,
    context: ToolContext,
    on_progress: ProgressCallback | None = None,
) -> CallableToolResult[dict[str, Any]]:
    """Execute file read with full validation and security checks.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context (permissions, abort signal, etc.)
        on_progress: Optional progress callback (not used for file read)

    Returns:
        CallableToolResult with file content or error
    """
    # 1. Resolve path (support root_dir from context)
    file_path = input.file_path
    root_dir = context.metadata.get("root_dir")

    if root_dir and not os.path.isabs(file_path):
        file_path = os.path.join(root_dir, file_path)

    file_path = os.path.abspath(file_path)

    # 2. Security validation: device files
    if file_path.startswith("/dev/"):
        return CallableToolResult(
            data=None,
            success=False,
            error="Device files are blocked for security",
            metadata={
                "error_code": "DEVICE_FILE_BLOCKED",
                "file_path": file_path,
            }
        )

    # 3. Check permissions (if manager available)
    if context.permission_manager:
        perm_result = await context.check_permission_async(
            tool_name="file_read",
            input=input.dict(),
            tool_content=file_path
        )

        if perm_result.behavior == PermissionBehavior.DENY:
            return CallableToolResult(
                data=None,
                success=False,
                error=perm_result.reason or "Permission denied",
                metadata={
                    "error_code": "PERMISSION_DENIED",
                    "file_path": file_path,
                }
            )

    # 4. Check file exists
    if not os.path.exists(file_path):
        return CallableToolResult(
            data=None,
            success=False,
            error=f"File not found: {file_path}",
            metadata={
                "error_code": "FILE_NOT_FOUND",
                "file_path": file_path,
            }
        )

    if not os.path.isfile(file_path):
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Not a file: {file_path}",
            metadata={
                "error_code": "NOT_A_FILE",
                "file_path": file_path,
            }
        )

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

        return CallableToolResult(
            data={
                "content": content,
                "file_path": file_path,
                "total_lines": len(lines),
                "lines_returned": len(selected_lines),
                "lines_read": len(selected_lines),  # Alias for compatibility
                "offset": input.offset,
                "limit": input.limit,
                "encoding": input.encoding,
                "has_more": end < len(lines),
                "truncated": end < len(lines),  # Alias for compatibility
            },
            success=True,
            metadata={
                "file_size_bytes": os.path.getsize(file_path),
            }
        )

    except UnicodeDecodeError as e:
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Encoding error: {e}. Try different encoding (latin-1, ascii, etc.)",
            metadata={
                "error_code": "ENCODING_ERROR",
                "file_path": file_path,
                "attempted_encoding": input.encoding,
            }
        )
    except PermissionError as e:
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Permission denied: {e}",
            metadata={
                "error_code": "OS_PERMISSION_ERROR",
                "file_path": file_path,
            }
        )
    except Exception as e:
        return CallableToolResult(
            data=None,
            success=False,
            error=str(e),
            metadata={
                "error_code": "READ_ERROR",
                "file_path": file_path,
            }
        )


# ---------------------------------------------------------------------------
# Tool Definition
# ---------------------------------------------------------------------------


FileReadToolCallable = build_readonly_tool(
    name="file_read_callable",
    description=(
        "Read file contents with pagination, line numbers, and security validation. "
        "Supports offset/limit for large files, multiple encodings, device file blocking, "
        "and permission checking. Returns structured result with metadata. "
        "Concurrent-safe: can read multiple files in parallel."
    ),
    input_schema=FileReadInput,
    call_fn=file_read_impl,
    is_concurrency_safe=True,  # Safe to read multiple files in parallel
    interrupt_behavior="cancel",  # Safe to interrupt file reads
)
