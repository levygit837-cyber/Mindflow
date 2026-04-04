"""Filesystem tools - Callable pattern (Phase 2).

All tools in this module use:
- Pydantic input schemas for type safety
- CallableToolResult return type
- ToolContext for runtime state (root_dir, sandbox_mode, permissions)
- Appropriate factories (build_readonly_tool, build_destructive_tool)
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.agents.tools.filesystem._legacy_adapter import (
    build_legacy_tool,
    deny_if_permission_blocked,
    flatten_legacy_result,
)
from mindflow_backend.agents.tools.filesystem.file_operations import (
    DirectoryListTool,
    FileDeleteTool,
    FileEditTool,
    FileReadTool,
    FileWriteTool,
)
from mindflow_backend.agents.tools.filesystem.operations import DirectoryCreateTool
from mindflow_backend.agents.tools.filesystem.search_tools import (
    FileFinderTool,
    GlobSearchTool,
    GrepSearchTool,
)
from mindflow_backend.schemas.tools import (
    CallableToolResult,
    ProgressCallback,
    build_readonly_tool,
    build_callable_tool,
    build_destructive_tool,
)
from mindflow_backend.schemas.tools.context import ToolContext


def _callable_result_from_flattened(
    flattened: dict[str, Any],
    *,
    metadata: dict[str, Any] | None = None,
) -> CallableToolResult[dict[str, Any]]:
    """Convert a flattened legacy result to a callable tool result."""
    if flattened.get("success"):
        data = dict(flattened)
        data.pop("success", None)
        return CallableToolResult(data=data, success=True, metadata=metadata or {})

    result_metadata = dict(metadata or {})
    error_code = flattened.get("error_code")
    if error_code:
        result_metadata.setdefault("error_code", error_code)
    return CallableToolResult(
        data=None,
        success=False,
        error=flattened.get("error") or "Unknown error",
        metadata=result_metadata,
    )


# ---------------------------------------------------------------------------
# FileReadCallable - Priority 1
# ---------------------------------------------------------------------------


class FileReadInput(BaseModel):
    """Input schema for FileReadCallable."""

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


async def file_read_impl(
    input: FileReadInput,
    context: ToolContext,
    on_progress: ProgressCallback | None = None,
) -> CallableToolResult[dict[str, Any]]:
    """Execute file read through the canonical filesystem tool."""
    permission_error = await deny_if_permission_blocked(
        context,
        tool_name="file_read",
        input_data=input.model_dump(),
        tool_content=input.file_path,
        content_key="file_path",
    )
    if permission_error:
        return _callable_result_from_flattened(permission_error)

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
    return _callable_result_from_flattened(flattened)


FileReadCallable = build_readonly_tool(
    name="file_read",
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


# ---------------------------------------------------------------------------
# DirectoryListCallable - Priority 1
# ---------------------------------------------------------------------------


class DirectoryListInput(BaseModel):
    """Input schema for DirectoryListCallable."""

    directory_path: str = Field(
        description="Path to directory to list"
    )
    include_hidden: bool = Field(
        default=False,
        description="Include hidden files (starting with .)"
    )
    include_size: bool = Field(
        default=False,
        description="Include file sizes in results"
    )
    include_type: bool = Field(
        default=True,
        description="Include file type (file/directory)"
    )
    max_items: int = Field(
        default=1000,
        ge=1,
        le=10000,
        description="Maximum number of items to return"
    )


async def directory_list_impl(
    input: DirectoryListInput,
    context: ToolContext,
    on_progress: ProgressCallback | None = None,
) -> CallableToolResult[dict[str, Any]]:
    """List directory contents through the canonical filesystem tool."""
    permission_error = await deny_if_permission_blocked(
        context,
        tool_name="list_dir",
        input_data=input.model_dump(),
        tool_content=input.directory_path,
        content_key="directory_path",
    )
    if permission_error:
        return _callable_result_from_flattened(permission_error)

    tool = build_legacy_tool(DirectoryListTool, context)
    result = await tool.execute(
        directory_path=input.directory_path,
        include_hidden=input.include_hidden,
        include_size=input.include_size,
        include_type=input.include_type,
        max_items=input.max_items,
    )
    flattened = flatten_legacy_result(
        result,
        error_map={
            "restricted path denied: /dev": "DEVICE_PATH_BLOCKED",
            "directory not found": "DIRECTORY_NOT_FOUND",
            "path is not a directory": "NOT_A_DIRECTORY",
            "permission denied": "OS_PERMISSION_ERROR",
            "workspace security error": "PERMISSION_DENIED",
        },
        default_error_code="LIST_ERROR",
    )
    return _callable_result_from_flattened(flattened)


DirectoryListCallable = build_readonly_tool(
    name="list_dir",
    description=(
        "List directory contents with filtering options. "
        "Returns file names, types, and optionally sizes. "
        "Supports hidden file filtering and result limiting. "
        "Concurrent-safe: can list multiple directories in parallel."
    ),
    input_schema=DirectoryListInput,
    call_fn=directory_list_impl,
    is_concurrency_safe=True,  # Safe to list multiple directories in parallel
    interrupt_behavior="cancel",  # Safe to interrupt directory listing
)


# ---------------------------------------------------------------------------
# FileFinderCallable - Priority 1
# ---------------------------------------------------------------------------


class FileFinderInput(BaseModel):
    """Input schema for FileFinderCallable."""

    pattern: str = Field(
        description="File name pattern (glob style, e.g., '*.py', 'test_*.txt')"
    )
    directory: str = Field(
        default=".",
        description="Directory to search in"
    )
    recursive: bool = Field(
        default=True,
        description="Search recursively in subdirectories"
    )
    min_size: int | None = Field(
        default=None,
        ge=0,
        description="Minimum file size in bytes"
    )
    max_size: int | None = Field(
        default=None,
        ge=0,
        description="Maximum file size in bytes"
    )
    min_date: str | None = Field(
        default=None,
        description="Minimum modification date (YYYY-MM-DD)"
    )
    max_date: str | None = Field(
        default=None,
        description="Maximum modification date (YYYY-MM-DD)"
    )
    max_results: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of results to return"
    )


async def file_finder_impl(
    input: FileFinderInput,
    context: ToolContext,
    on_progress: ProgressCallback | None = None,
) -> CallableToolResult[dict[str, Any]]:
    """Find files through the canonical filesystem tool."""
    tool = build_legacy_tool(FileFinderTool, context)
    result = await tool.execute(
        pattern=input.pattern,
        directory=input.directory,
        recursive=input.recursive,
        min_size=input.min_size,
        max_size=input.max_size,
        min_date=input.min_date,
        max_date=input.max_date,
        max_results=input.max_results,
    )
    flattened = flatten_legacy_result(
        result,
        error_map={
            "directory not found": "DIRECTORY_NOT_FOUND",
            "not a directory": "NOT_A_DIRECTORY",
            "does not match format": "INVALID_DATE_FORMAT",
            "time data": "INVALID_DATE_FORMAT",
        },
        default_error_code="SEARCH_ERROR",
    )
    if flattened.get("success"):
        flattened.setdefault("pattern", input.pattern)
    return _callable_result_from_flattened(flattened)


FileFinderCallable = build_readonly_tool(
    name="file_finder",
    description=(
        "Find files by name pattern with optional size and date filters. "
        "Supports recursive search and glob patterns. "
        "Returns file metadata including size and modification date. "
        "Concurrent-safe: can search multiple directories in parallel."
    ),
    input_schema=FileFinderInput,
    call_fn=file_finder_impl,
    is_concurrency_safe=True,  # Safe to search multiple directories in parallel
    interrupt_behavior="cancel",  # Safe to interrupt file search
)


# ---------------------------------------------------------------------------
# GrepSearchCallable - Priority 1
# ---------------------------------------------------------------------------


class GrepSearchInput(BaseModel):
    """Input schema for GrepSearchCallable."""

    pattern: str = Field(
        description="Regex pattern to search for in file contents"
    )
    directory: str = Field(
        default=".",
        description="Directory to search in (absolute or relative to root_dir)"
    )
    file_pattern: str = Field(
        default="*",
        description="Glob pattern to filter files (e.g., '*.py', '*.txt')"
    )
    recursive: bool = Field(
        default=True,
        description="Search recursively in subdirectories"
    )
    case_sensitive: bool = Field(
        default=False,
        description="Case-sensitive pattern matching"
    )
    max_results: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of matches to return"
    )
    include_line_numbers: bool = Field(
        default=True,
        description="Include line numbers in results"
    )


async def grep_search_impl(
    input: GrepSearchInput,
    context: ToolContext,
    on_progress: ProgressCallback | None = None,
) -> CallableToolResult[dict[str, Any]]:
    """Execute grep through the canonical filesystem tool."""
    tool = build_legacy_tool(GrepSearchTool, context)
    result = await tool.execute(
        pattern=input.pattern,
        directory=input.directory,
        file_pattern=input.file_pattern,
        recursive=input.recursive,
        case_sensitive=input.case_sensitive,
        max_results=input.max_results,
        include_line_numbers=input.include_line_numbers,
    )
    flattened = flatten_legacy_result(
        result,
        error_map={
            "directory not found": "DIRECTORY_NOT_FOUND",
            "not a directory": "NOT_A_DIRECTORY",
            "invalid regex pattern": "INVALID_REGEX",
        },
        default_error_code="SEARCH_ERROR",
    )
    if flattened.get("success"):
        flattened.setdefault("pattern", input.pattern)
    return _callable_result_from_flattened(flattened)


GrepSearchCallable = build_readonly_tool(
    name="grep_search",
    description=(
        "Search file contents using regex patterns. "
        "Supports recursive search, file filtering, case-sensitive/insensitive matching, "
        "and returns matches with line numbers and context. "
        "Concurrent-safe: can search multiple directories in parallel."
    ),
    input_schema=GrepSearchInput,
    call_fn=grep_search_impl,
    is_concurrency_safe=True,  # Safe to search multiple directories in parallel
    interrupt_behavior="cancel",  # Safe to interrupt grep search
)


# ---------------------------------------------------------------------------
# GlobSearchCallable - Priority 1
# ---------------------------------------------------------------------------


class GlobSearchInput(BaseModel):
    """Input schema for GlobSearchCallable."""

    pattern: str = Field(
        description="Glob pattern to match files (e.g., '*.py', '**/*.txt', 'src/**/*.js')"
    )
    directory: str = Field(
        default=".",
        description="Base directory to search in (absolute or relative to root_dir)"
    )
    max_results: int = Field(
        default=200,
        ge=1,
        le=2000,
        description="Maximum number of files to return"
    )
    include_dirs: bool = Field(
        default=False,
        description="Include directories in results (default: files only)"
    )
    absolute_paths: bool = Field(
        default=False,
        description="Return absolute paths instead of relative paths"
    )


async def glob_search_impl(
    input: GlobSearchInput,
    context: ToolContext,
    on_progress: ProgressCallback | None = None,
) -> CallableToolResult[dict[str, Any]]:
    """Execute glob search through the canonical filesystem tool."""
    tool = build_legacy_tool(GlobSearchTool, context)
    result = await tool.execute(
        pattern=input.pattern,
        directory=input.directory,
        max_results=input.max_results,
        include_dirs=input.include_dirs,
        absolute_paths=input.absolute_paths,
    )
    flattened = flatten_legacy_result(
        result,
        error_map={
            "directory not found": "DIRECTORY_NOT_FOUND",
            "not a directory": "NOT_A_DIRECTORY",
            "glob search error": "GLOB_ERROR",
        },
        default_error_code="GLOB_ERROR",
    )
    if flattened.get("success"):
        flattened.setdefault("pattern", input.pattern)
    return _callable_result_from_flattened(flattened)


GlobSearchCallable = build_readonly_tool(
    name="glob_search",
    description=(
        "Find files matching glob patterns. "
        "Supports recursive patterns (** wildcard), file/directory filtering, "
        "and returns relative or absolute paths. "
        "Concurrent-safe: can search multiple directories in parallel."
    ),
    input_schema=GlobSearchInput,
    call_fn=glob_search_impl,
    is_concurrency_safe=True,  # Safe to search multiple directories in parallel
    interrupt_behavior="cancel",  # Safe to interrupt glob search
)


# ---------------------------------------------------------------------------
# FileWriteCallable - Priority 2
# ---------------------------------------------------------------------------


class FileWriteInput(BaseModel):
    """Input schema for FileWriteCallable."""

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


async def file_write_impl(
    input: FileWriteInput,
    context: ToolContext,
    on_progress: ProgressCallback | None = None,
) -> CallableToolResult[dict[str, Any]]:
    """Execute file write through the canonical filesystem tool."""
    permission_error = await deny_if_permission_blocked(
        context,
        tool_name="write_file",
        input_data=input.model_dump(),
        tool_content=input.file_path,
        content_key="file_path",
    )
    if permission_error:
        return _callable_result_from_flattened(permission_error)

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
    return _callable_result_from_flattened(flattened)


FileWriteCallable = build_callable_tool(
    name="write_file",
    description=(
        "Write content to a file with security validation and permission checking. "
        "Supports creating parent directories, overwrite control, multiple encodings, "
        "and blocks writes to system/device files. Returns file metadata on success. "
        "NOT concurrent-safe: file writes can conflict."
    ),
    input_schema=FileWriteInput,
    call_fn=file_write_impl,
    is_read_only=False,  # This is a write operation
    is_destructive=True,  # Writing is destructive
    is_concurrency_safe=False,  # File writes are not concurrency-safe
    interrupt_behavior="block",  # Don't interrupt file writes
)


# ---------------------------------------------------------------------------
# FileEditCallable - Priority 2
# ---------------------------------------------------------------------------


class FileEditInput(BaseModel):
    """Input schema for FileEditCallable."""

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


async def file_edit_impl(
    input: FileEditInput,
    context: ToolContext,
    on_progress: ProgressCallback | None = None,
) -> CallableToolResult[dict[str, Any]]:
    """Execute file edit through the canonical filesystem tool."""
    permission_error = await deny_if_permission_blocked(
        context,
        tool_name="edit_file",
        input_data=input.model_dump(),
        tool_content=input.file_path,
        content_key="file_path",
    )
    if permission_error:
        return _callable_result_from_flattened(permission_error)

    tool = build_legacy_tool(FileEditTool, context)
    result = await tool.execute(
        file_path=input.file_path,
        old_string=input.old_string,
        new_string=input.new_string,
        count=input.count,
        encoding=input.encoding,
    )
    flattened = flatten_legacy_result(
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
    return _callable_result_from_flattened(flattened)


FileEditCallable = build_callable_tool(
    name="edit_file",
    description=(
        "Edit a file by replacing old_string with new_string. "
        "Supports single or multiple replacements, encoding options, "
        "and security validation. Blocks edits to system/device files. "
        "NOT concurrent-safe: file edits can conflict."
    ),
    input_schema=FileEditInput,
    call_fn=file_edit_impl,
    is_read_only=False,  # This is a write operation
    is_destructive=True,  # Editing is destructive
    is_concurrency_safe=False,  # File edits are not concurrency-safe
    interrupt_behavior="block",  # Don't interrupt file edits
)


# ---------------------------------------------------------------------------
# FileDeleteCallable - Priority 2
# ---------------------------------------------------------------------------


class FileDeleteInput(BaseModel):
    """Input schema for FileDeleteCallable."""

    file_path: str = Field(
        description="Path to file to delete"
    )
    confirm: bool = Field(
        default=False,
        description="Confirmation flag for destructive operation"
    )


async def file_delete_impl(
    input: FileDeleteInput,
    context: ToolContext,
    on_progress: ProgressCallback | None = None,
) -> CallableToolResult[dict[str, Any]]:
    """Delete a file through the canonical filesystem tool."""
    permission_error = await deny_if_permission_blocked(
        context,
        tool_name="delete_file",
        input_data=input.model_dump(),
        tool_content=input.file_path,
        content_key="file_path",
    )
    if permission_error:
        return _callable_result_from_flattened(permission_error)

    tool = build_legacy_tool(FileDeleteTool, context)
    result = await tool.execute(file_path=input.file_path, confirm=input.confirm)
    flattened = flatten_legacy_result(
        result,
        error_map={
            "restricted path denied: /dev": "DEVICE_FILE_BLOCKED",
            "restricted path denied: /etc": "SYSTEM_PATH_BLOCKED",
            "restricted path denied: /usr": "SYSTEM_PATH_BLOCKED",
            "restricted path denied: /bin": "SYSTEM_PATH_BLOCKED",
            "restricted path denied: /sbin": "SYSTEM_PATH_BLOCKED",
            "restricted path denied: /boot": "SYSTEM_PATH_BLOCKED",
            "restricted path denied: /sys": "SYSTEM_PATH_BLOCKED",
            "restricted path denied: /proc": "SYSTEM_PATH_BLOCKED",
            "path not found": "FILE_NOT_FOUND",
            "path is neither file nor directory": "NOT_A_FILE",
            "permission denied": "OS_PERMISSION_ERROR",
            "workspace security error": "PERMISSION_DENIED",
        },
        default_error_code="DELETE_ERROR",
    )
    return _callable_result_from_flattened(flattened)


FileDeleteCallable = build_destructive_tool(
    name="delete_file",
    description=(
        "Delete a file with security controls. "
        "Blocks deletion of device files and system paths. "
        "Returns file information before deletion. "
        "IRREVERSIBLE operation - use with caution."
    ),
    input_schema=FileDeleteInput,
    call_fn=file_delete_impl,
    # Defaults from build_destructive_tool:
    # is_read_only=False, is_destructive=True, is_concurrency_safe=False, interrupt_behavior="block"
)


# ---------------------------------------------------------------------------
# DirectoryCreateCallable - Priority 2
# ---------------------------------------------------------------------------


class DirectoryCreateInput(BaseModel):
    """Input schema for DirectoryCreateCallable."""

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


async def directory_create_impl(
    input: DirectoryCreateInput,
    context: ToolContext,
    on_progress: ProgressCallback | None = None,
) -> CallableToolResult[dict[str, Any]]:
    """Create a directory through the canonical filesystem tool."""
    permission_error = await deny_if_permission_blocked(
        context,
        tool_name="mkdir",
        input_data=input.model_dump(),
        tool_content=input.directory_path,
        content_key="directory_path",
    )
    if permission_error:
        return _callable_result_from_flattened(permission_error)

    tool = build_legacy_tool(DirectoryCreateTool, context)
    result = await tool.execute(
        directory_path=input.directory_path,
        parents=input.parents,
        exist_ok=input.exist_ok,
    )
    flattened = flatten_legacy_result(
        result,
        error_map={
            "create directory blocked in read-only sandbox mode": "READ_ONLY_MODE",
            "workspace security error": "PERMISSION_DENIED",
            "permission denied": "OS_PERMISSION_ERROR",
            "file exists": "DIRECTORY_EXISTS",
            "not a directory": "NOT_A_DIRECTORY",
        },
        default_error_code="CREATE_ERROR",
    )
    if flattened.get("success"):
        flattened.setdefault("directory_path", input.directory_path)
        flattened.setdefault("created", True)
        flattened.setdefault("parents_created", input.parents)
        flattened.setdefault("mode", oct(input.mode))
    return _callable_result_from_flattened(flattened)


DirectoryCreateCallable = build_callable_tool(
    name="mkdir",
    description=(
        "Create a directory with optional parent creation. "
        "Blocks creation in device and system paths. "
        "Supports custom permissions and exist_ok flag. "
        "NOT concurrent-safe: directory creation can conflict."
    ),
    input_schema=DirectoryCreateInput,
    call_fn=directory_create_impl,
    is_read_only=False,  # This is a write operation
    is_destructive=False,  # Creating directories is not destructive
    is_concurrency_safe=False,  # Directory creation is not concurrency-safe
    interrupt_behavior="block",  # Don't interrupt directory creation
)
