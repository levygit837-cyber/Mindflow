"""FileEditTool v3 - New Tool System Implementation.

Edit file contents by replacing old_string with new_string.
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
            "error": "Cannot edit device files",
            "error_code": "DEVICE_FILE_BLOCKED",
            "file_path": file_path
        }

    # 3. Security validation: system paths
    restricted_paths = ["/etc", "/usr", "/bin", "/sbin", "/boot", "/sys", "/proc"]
    for restricted in restricted_paths:
        if file_path.startswith(restricted):
            return {
                "success": False,
                "error": f"Cannot edit system path: {restricted}",
                "error_code": "SYSTEM_PATH_BLOCKED",
                "file_path": file_path
            }

    # 4. Check permissions (if manager available)
    if context.permission_manager:
        perm_result = await context.check_permission_async(
            tool_name="edit_file",
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

    # 6. Read file content
    try:
        with open(file_path, 'r', encoding=input.encoding) as f:
            content = f.read()
    except UnicodeDecodeError as e:
        return {
            "success": False,
            "error": f"Encoding error reading file: {e}. Try different encoding.",
            "error_code": "ENCODING_ERROR",
            "file_path": file_path,
            "attempted_encoding": input.encoding
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to read file: {e}",
            "error_code": "READ_ERROR",
            "file_path": file_path
        }

    # 7. Check if old_string exists in content
    if input.old_string not in content:
        return {
            "success": False,
            "error": "old_string not found in file",
            "error_code": "STRING_NOT_FOUND",
            "file_path": file_path,
            "old_string": input.old_string[:50] + "..." if len(input.old_string) > 50 else input.old_string
        }

    # 8. Perform replacement
    count_occurrences = content.count(input.old_string)

    if input.count == -1:
        # Replace all occurrences
        new_content = content.replace(input.old_string, input.new_string)
        replacements_made = count_occurrences
    else:
        # Replace specific number of occurrences
        new_content = content.replace(input.old_string, input.new_string, input.count)
        replacements_made = min(input.count, count_occurrences)

    # 9. Write modified content back
    original_size = os.path.getsize(file_path)

    try:
        with open(file_path, 'w', encoding=input.encoding) as f:
            f.write(new_content)

        new_size = os.path.getsize(file_path)

        return {
            "success": True,
            "file_path": file_path,
            "replacements_made": replacements_made,
            "occurrences_replaced": replacements_made,  # Alias for compatibility
            "total_occurrences": count_occurrences,
            "encoding": input.encoding,
            "old_string_length": len(input.old_string),
            "new_string_length": len(input.new_string),
            "size_before": original_size,
            "size_after": new_size,
            "size_change": len(new_content) - len(content)
        }

    except UnicodeEncodeError as e:
        return {
            "success": False,
            "error": f"Encoding error writing file: {e}. Try different encoding.",
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
