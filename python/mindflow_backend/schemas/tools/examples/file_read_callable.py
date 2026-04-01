"""Example: FileReadTool using callable pattern.

This is a reference implementation showing how to create a tool using
the new callable pattern. It demonstrates:

- Input schema definition with Pydantic
- Implementation function with proper error handling
- Using build_readonly_tool() for convenience
- Custom validation and permission checking

This tool will replace the legacy file_read tool once migration is complete.
"""

from __future__ import annotations

import aiofiles
from pydantic import BaseModel, Field

from mindflow_backend.schemas.tools.callable import ToolResult
from mindflow_backend.schemas.tools.callable_builder import build_readonly_tool
from mindflow_backend.schemas.tools.context import ToolContext


# ── Input Schema ──


class FileReadInput(BaseModel):
    """Input schema for file read tool."""

    file_path: str = Field(
        ...,
        description="Absolute or relative path to the file to read",
    )
    encoding: str = Field(
        default="utf-8",
        description="File encoding (default: utf-8)",
    )
    max_size_bytes: int | None = Field(
        default=None,
        description="Maximum file size to read in bytes (None = no limit)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "file_path": "/path/to/file.txt",
                "encoding": "utf-8",
                "max_size_bytes": 1048576,  # 1MB
            }
        }


# ── Implementation ──


async def file_read_impl(
    input: FileReadInput,
    context: ToolContext,
    on_progress=None,
) -> ToolResult[str]:
    """Read file contents from filesystem.

    Args:
        input: Validated FileReadInput
        context: Tool execution context
        on_progress: Optional progress callback (not used for file read)

    Returns:
        ToolResult with file contents or error
    """
    try:
        # Check if file exists
        import os

        if not os.path.exists(input.file_path):
            return ToolResult(
                data=None,
                success=False,
                error=f"File not found: {input.file_path}",
                metadata={"error_code": "FILE_NOT_FOUND"},
            )

        # Check file size if limit specified
        if input.max_size_bytes is not None:
            file_size = os.path.getsize(input.file_path)
            if file_size > input.max_size_bytes:
                return ToolResult(
                    data=None,
                    success=False,
                    error=f"File too large: {file_size} bytes (limit: {input.max_size_bytes})",
                    metadata={
                        "error_code": "FILE_TOO_LARGE",
                        "file_size": file_size,
                        "max_size": input.max_size_bytes,
                    },
                )

        # Read file
        async with aiofiles.open(input.file_path, "r", encoding=input.encoding) as f:
            content = await f.read()

        return ToolResult(
            data=content,
            success=True,
            metadata={
                "file_path": input.file_path,
                "encoding": input.encoding,
                "size_bytes": len(content.encode(input.encoding)),
            },
        )

    except FileNotFoundError:
        return ToolResult(
            data=None,
            success=False,
            error=f"File not found: {input.file_path}",
            metadata={"error_code": "FILE_NOT_FOUND"},
        )

    except PermissionError:
        return ToolResult(
            data=None,
            success=False,
            error=f"Permission denied: {input.file_path}",
            metadata={"error_code": "PERMISSION_DENIED"},
        )

    except UnicodeDecodeError as e:
        return ToolResult(
            data=None,
            success=False,
            error=f"Failed to decode file with encoding {input.encoding}: {e}",
            metadata={"error_code": "ENCODING_ERROR"},
        )

    except Exception as e:
        return ToolResult(
            data=None,
            success=False,
            error=f"Failed to read file: {e}",
            metadata={"error_code": "READ_ERROR"},
        )


# ── Custom Validation (optional) ──


async def validate_file_read_input(
    input: FileReadInput,
    context: ToolContext,
) -> tuple[bool, str | None]:
    """Custom validation for file read input.

    This demonstrates how to add validation beyond Pydantic schema.
    """
    import os

    # Check for dangerous paths
    dangerous_patterns = ["/etc/shadow", "/etc/passwd"]
    for pattern in dangerous_patterns:
        if pattern in input.file_path:
            return (False, f"Cannot read sensitive system file: {input.file_path}")

    # Check if path is absolute or relative
    if not os.path.isabs(input.file_path):
        # Relative paths are OK - they'll be resolved relative to cwd
        pass

    return (True, None)


# ── Tool Definition ──


FileReadToolCallable = build_readonly_tool(
    name="file_read_callable",
    description="Read file contents from filesystem (callable pattern)",
    input_schema=FileReadInput,
    call_fn=file_read_impl,
    is_concurrency_safe=True,  # Safe to read multiple files in parallel
    interrupt_behavior="cancel",  # Safe to interrupt file reads
)


# Alternative: Using build_callable_tool with custom validation
# from mindflow_backend.schemas.tools.callable_builder import build_callable_tool
#
# FileReadToolCallable = build_callable_tool(
#     name="file_read_callable",
#     description="Read file contents from filesystem",
#     input_schema=FileReadInput,
#     call_fn=file_read_impl,
#     is_read_only=True,
#     is_concurrency_safe=True,
#     interrupt_behavior="cancel",
#     validate_input_fn=validate_file_read_input,  # Custom validation
# )


# ── Usage Example ──

"""
Example usage:

    from mindflow_backend.schemas.tools.context import ToolContext
    from mindflow_backend.schemas.tools.examples.file_read_callable import (
        FileReadToolCallable,
        FileReadInput,
    )

    # Create context
    context = ToolContext(
        permission_context=None,
        metadata={"user_id": "test"},
    )

    # Create input
    input_data = FileReadInput(
        file_path="/path/to/file.txt",
        encoding="utf-8",
    )

    # Call tool directly (no LangChain wrapper needed!)
    result = await FileReadToolCallable.call(input_data, context)

    if result.success:
        print(f"File contents: {result.data}")
    else:
        print(f"Error: {result.error}")

    # Or use with StreamingToolExecutor for concurrency control
    from mindflow_backend.schemas.tools.callable_executor import StreamingToolExecutor

    executor = StreamingToolExecutor([FileReadToolCallable], context)

    result = await executor.execute_tool_call(
        "file_read_callable",
        {"file_path": "/path/to/file.txt"},
    )
"""
