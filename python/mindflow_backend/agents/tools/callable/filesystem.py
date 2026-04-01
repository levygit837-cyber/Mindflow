"""Filesystem tools - Callable pattern (Phase 2).

All tools in this module use:
- Pydantic input schemas for type safety
- CallableToolResult return type
- ToolContext for runtime state (root_dir, sandbox_mode, permissions)
- Appropriate factories (build_readonly_tool, build_destructive_tool)
"""

from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.schemas.tools.callable import CallableToolResult, ProgressCallback
from mindflow_backend.schemas.tools.callable_builder import (
    build_readonly_tool,
    build_callable_tool,
    build_destructive_tool,
)
from mindflow_backend.schemas.tools.context import ToolContext
from mindflow_backend.schemas.tools.permission import PermissionBehavior


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
    root_dir = context.root_dir or context.metadata.get("root_dir")

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
    """List directory contents with security controls.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context
        on_progress: Optional progress callback

    Returns:
        CallableToolResult with directory listing or error
    """
    from pathlib import Path

    # 1. Resolve directory path (support root_dir from context)
    directory_path = input.directory_path
    root_dir = context.root_dir or context.metadata.get("root_dir")

    if root_dir and not os.path.isabs(directory_path):
        directory_path = os.path.join(root_dir, directory_path)

    directory_path = os.path.abspath(directory_path)

    # 2. Security validation: block device files
    if directory_path.startswith("/dev/"):
        return CallableToolResult(
            data=None,
            success=False,
            error="Device paths are not allowed",
            metadata={
                "error_code": "DEVICE_PATH_BLOCKED",
                "directory_path": directory_path,
            }
        )

    # 3. Check permissions (if manager available)
    if context.permission_manager:
        perm_result = await context.check_permission_async(
            tool_name="list_dir",
            input=input.model_dump(),
            tool_content=directory_path
        )

        if perm_result.behavior == PermissionBehavior.DENY:
            return CallableToolResult(
                data=None,
                success=False,
                error=perm_result.reason or "Permission denied",
                metadata={
                    "error_code": "PERMISSION_DENIED",
                    "directory_path": directory_path,
                }
            )

    # 4. Check directory exists
    if not os.path.exists(directory_path):
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Directory not found: {directory_path}",
            metadata={
                "error_code": "DIRECTORY_NOT_FOUND",
                "directory_path": directory_path,
            }
        )

    if not os.path.isdir(directory_path):
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Not a directory: {directory_path}",
            metadata={
                "error_code": "NOT_A_DIRECTORY",
                "directory_path": directory_path,
            }
        )

    # 5. List directory contents
    try:
        entries = []
        path_obj = Path(directory_path)

        for item in path_obj.iterdir():
            # Skip hidden files if not requested
            if not input.include_hidden and item.name.startswith('.'):
                continue

            # Check max items limit
            if len(entries) >= input.max_items:
                break

            entry = {
                "name": item.name,
                "path": str(item)
            }

            # Add type information
            if input.include_type:
                if item.is_file():
                    entry["type"] = "file"
                elif item.is_dir():
                    entry["type"] = "directory"
                elif item.is_symlink():
                    entry["type"] = "symlink"
                else:
                    entry["type"] = "other"

            # Add size information
            if input.include_size:
                try:
                    if item.is_file():
                        entry["size"] = item.stat().st_size
                    elif item.is_dir():
                        entry["size"] = 0  # Directories don't have meaningful size
                except (OSError, PermissionError):
                    entry["size"] = None

            entries.append(entry)

        return CallableToolResult(
            data={
                "directory_path": directory_path,
                "entries": entries,
                "total_count": len(entries),
                "truncated": len(entries) >= input.max_items,
            },
            success=True,
            metadata={
                "items_returned": len(entries),
            }
        )

    except PermissionError as e:
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Permission denied: {e}",
            metadata={
                "error_code": "OS_PERMISSION_ERROR",
                "directory_path": directory_path,
            }
        )
    except Exception as e:
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Failed to list directory: {e}",
            metadata={
                "error_code": "LIST_ERROR",
                "directory_path": directory_path,
            }
        )


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
    """Find files matching pattern with optional filters.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context
        on_progress: Optional progress callback

    Returns:
        CallableToolResult with found files or error
    """
    from datetime import datetime
    from pathlib import Path

    # 1. Resolve directory (support root_dir from context)
    directory = input.directory
    root_dir = context.root_dir or context.metadata.get("root_dir")

    if root_dir and not os.path.isabs(directory):
        directory = os.path.join(root_dir, directory)

    directory = os.path.abspath(directory)

    # 2. Check directory exists
    if not os.path.exists(directory):
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Directory not found: {directory}",
            metadata={
                "error_code": "DIRECTORY_NOT_FOUND",
                "directory": directory,
            }
        )

    if not os.path.isdir(directory):
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Not a directory: {directory}",
            metadata={
                "error_code": "NOT_A_DIRECTORY",
                "directory": directory,
            }
        )

    # 3. Parse date filters
    min_timestamp = None
    max_timestamp = None

    if input.min_date:
        try:
            min_timestamp = datetime.strptime(input.min_date, "%Y-%m-%d").timestamp()
        except ValueError as e:
            return CallableToolResult(
                data=None,
                success=False,
                error=f"Invalid min_date format: {e}. Use YYYY-MM-DD",
                metadata={"error_code": "INVALID_DATE_FORMAT"}
            )

    if input.max_date:
        try:
            max_timestamp = datetime.strptime(input.max_date, "%Y-%m-%d").timestamp()
        except ValueError as e:
            return CallableToolResult(
                data=None,
                success=False,
                error=f"Invalid max_date format: {e}. Use YYYY-MM-DD",
                metadata={"error_code": "INVALID_DATE_FORMAT"}
            )

    # 4. Search for files
    try:
        files = []
        search_path = Path(directory)

        # Use rglob for recursive, glob for non-recursive
        if input.recursive:
            matches = search_path.rglob(input.pattern)
        else:
            matches = search_path.glob(input.pattern)

        for file_path in matches:
            # Only include files, not directories
            if not file_path.is_file():
                continue

            try:
                stat = file_path.stat()

                # Apply size filters
                if input.min_size is not None and stat.st_size < input.min_size:
                    continue

                if input.max_size is not None and stat.st_size > input.max_size:
                    continue

                # Apply date filters
                if min_timestamp is not None and stat.st_mtime < min_timestamp:
                    continue

                if max_timestamp is not None and stat.st_mtime > max_timestamp:
                    continue

                # Add to results
                files.append({
                    "path": str(file_path),
                    "name": file_path.name,
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "modified_date": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })

            except (OSError, PermissionError):
                # Skip files we can't access
                continue

            # Check max results limit
            if len(files) >= input.max_results:
                break

        return CallableToolResult(
            data={
                "files": files,
                "total_count": len(files),
                "truncated": len(files) >= input.max_results,
                "pattern": input.pattern,
                "directory": directory,
            },
            success=True,
            metadata={
                "files_found": len(files),
            }
        )

    except Exception as e:
        return CallableToolResult(
            data=None,
            success=False,
            error=f"File finder error: {e}",
            metadata={
                "error_code": "SEARCH_ERROR",
                "pattern": input.pattern,
            }
        )


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
    """Execute grep search with regex pattern matching.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context
        on_progress: Optional progress callback

    Returns:
        CallableToolResult with search results or error
    """
    import re
    from pathlib import Path

    # 1. Resolve directory (support root_dir from context)
    directory = input.directory
    root_dir = context.root_dir or context.metadata.get("root_dir")

    if root_dir and not os.path.isabs(directory):
        directory = os.path.join(root_dir, directory)

    directory = os.path.abspath(directory)

    # 2. Check directory exists
    if not os.path.exists(directory):
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Directory not found: {directory}",
            metadata={
                "error_code": "DIRECTORY_NOT_FOUND",
                "directory": directory,
            }
        )

    if not os.path.isdir(directory):
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Not a directory: {directory}",
            metadata={
                "error_code": "NOT_A_DIRECTORY",
                "directory": directory,
            }
        )

    # 3. Compile regex pattern
    try:
        flags = 0 if input.case_sensitive else re.IGNORECASE
        regex = re.compile(input.pattern, flags)
    except re.error as e:
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Invalid regex pattern: {e}",
            metadata={
                "error_code": "INVALID_REGEX",
                "pattern": input.pattern,
            }
        )

    # 4. Search files
    matches = []
    files_searched = 0
    files_with_matches = 0

    search_path = Path(directory)

    # Get files to search
    if input.recursive:
        files = search_path.rglob(input.file_pattern)
    else:
        files = search_path.glob(input.file_pattern)

    # 5. Search in each file
    for file_path in files:
        if not file_path.is_file():
            continue

        files_searched += 1
        file_has_matches = False

        # Search in file
        try:
            with open(file_path, encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    match = regex.search(line)
                    if match:
                        file_has_matches = True
                        match_data = {
                            "file": str(file_path.relative_to(search_path) if file_path.is_relative_to(search_path) else file_path),
                            "line": line.rstrip(),
                            "match": match.group()
                        }

                        if input.include_line_numbers:
                            match_data["line_number"] = line_num

                        matches.append(match_data)

                        # Check max results
                        if len(matches) >= input.max_results:
                            break

        except (UnicodeDecodeError, PermissionError, OSError):
            # Skip files that can't be read
            continue

        if file_has_matches:
            files_with_matches += 1

        # Check if we've reached max results
        if len(matches) >= input.max_results:
            break

    # 6. Return results
    return CallableToolResult(
        data={
            "matches": matches,
            "total_matches": len(matches),
            "files_searched": files_searched,
            "files_with_matches": files_with_matches,
            "pattern": input.pattern,
            "directory": directory,
            "truncated": len(matches) >= input.max_results,
        },
        success=True,
        metadata={
            "matches_found": len(matches),
        }
    )


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
    """Execute glob search to find files matching pattern.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context
        on_progress: Optional progress callback

    Returns:
        CallableToolResult with matched files or error
    """
    from pathlib import Path

    # 1. Resolve directory (support root_dir from context)
    directory = input.directory
    root_dir = context.root_dir or context.metadata.get("root_dir")

    if root_dir and not os.path.isabs(directory):
        directory = os.path.join(root_dir, directory)

    directory = os.path.abspath(directory)

    # 2. Check directory exists
    if not os.path.exists(directory):
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Directory not found: {directory}",
            metadata={
                "error_code": "DIRECTORY_NOT_FOUND",
                "directory": directory,
            }
        )

    if not os.path.isdir(directory):
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Not a directory: {directory}",
            metadata={
                "error_code": "NOT_A_DIRECTORY",
                "directory": directory,
            }
        )

    # 3. Execute glob search
    try:
        base_path = Path(directory)

        # Use glob (handles both recursive and non-recursive patterns)
        matches = base_path.glob(input.pattern)

        # 4. Filter and collect results
        files = []
        dirs = []

        for match in matches:
            # Check max results
            if len(files) + len(dirs) >= input.max_results:
                break

            # Determine path format
            if input.absolute_paths:
                path_str = str(match.absolute())
            else:
                try:
                    path_str = str(match.relative_to(base_path))
                except ValueError:
                    path_str = str(match)

            # Categorize
            if match.is_file():
                files.append(path_str)
            elif match.is_dir() and input.include_dirs:
                dirs.append(path_str)

        # 5. Build result data
        result_data = {
            "files": files,
            "total_files": len(files),
            "pattern": input.pattern,
            "directory": directory,
            "truncated": (len(files) + len(dirs)) >= input.max_results,
        }

        if input.include_dirs:
            result_data["directories"] = dirs
            result_data["total_directories"] = len(dirs)
            result_data["total_matches"] = len(files) + len(dirs)
        else:
            result_data["total_matches"] = len(files)

        return CallableToolResult(
            data=result_data,
            success=True,
            metadata={
                "matches_found": len(files) + (len(dirs) if input.include_dirs else 0),
            }
        )

    except Exception as e:
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Glob search error: {e}",
            metadata={
                "error_code": "GLOB_ERROR",
                "pattern": input.pattern,
            }
        )


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
    """Execute file write with full validation and security checks.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context (permissions, abort signal, etc.)
        on_progress: Optional progress callback

    Returns:
        CallableToolResult with file metadata or error
    """
    # 1. Check sandbox mode for read-only enforcement
    if context.sandbox_mode and hasattr(context.sandbox_mode, 'value'):
        if context.sandbox_mode.value == "READ_ONLY":
            return CallableToolResult(
                data=None,
                success=False,
                error="Write operation blocked in read-only mode",
                metadata={
                    "error_code": "READ_ONLY_MODE",
                    "file_path": input.file_path,
                }
            )

    # 2. Resolve path (support root_dir from context)
    file_path = input.file_path
    root_dir = context.root_dir or context.metadata.get("root_dir")

    if root_dir and not os.path.isabs(file_path):
        file_path = os.path.join(root_dir, file_path)

    file_path = os.path.abspath(file_path)

    # 3. Security validation: device files
    if file_path.startswith("/dev/"):
        return CallableToolResult(
            data=None,
            success=False,
            error="Cannot write to device files",
            metadata={
                "error_code": "DEVICE_FILE_BLOCKED",
                "file_path": file_path,
            }
        )

    # 4. Security validation: system paths
    restricted_paths = ["/etc", "/usr", "/bin", "/sbin", "/boot", "/sys", "/proc"]
    for restricted in restricted_paths:
        if file_path.startswith(restricted):
            return CallableToolResult(
                data=None,
                success=False,
                error=f"Cannot write to system path: {restricted}",
                metadata={
                    "error_code": "SYSTEM_PATH_BLOCKED",
                    "file_path": file_path,
                }
            )

    # 5. Check permissions (if manager available)
    if context.permission_manager:
        perm_result = await context.check_permission_async(
            tool_name="write_file",
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

    # 6. Check if file exists and overwrite flag
    file_exists = os.path.exists(file_path)
    if file_exists and not input.overwrite:
        return CallableToolResult(
            data=None,
            success=False,
            error=f"File already exists and overwrite=False: {file_path}",
            metadata={
                "error_code": "FILE_EXISTS",
                "file_path": file_path,
            }
        )

    # 7. Create parent directories if needed
    if input.create_dirs:
        parent_dir = os.path.dirname(file_path)
        if parent_dir and not os.path.exists(parent_dir):
            try:
                os.makedirs(parent_dir, exist_ok=True)
            except Exception as e:
                return CallableToolResult(
                    data=None,
                    success=False,
                    error=f"Failed to create parent directories: {e}",
                    metadata={
                        "error_code": "MKDIR_ERROR",
                        "file_path": file_path,
                    }
                )

    # 8. Write file
    try:
        # Check if parent directory exists when create_dirs=False
        if not input.create_dirs:
            parent_dir = os.path.dirname(file_path)
            if parent_dir and not os.path.exists(parent_dir):
                return CallableToolResult(
                    data=None,
                    success=False,
                    error=f"Parent directory does not exist: {parent_dir}",
                    metadata={
                        "error_code": "DIRECTORY_NOT_FOUND",
                        "file_path": file_path,
                    }
                )

        with open(file_path, 'w', encoding=input.encoding) as f:
            f.write(input.content)

        # Get file stats
        file_size = os.path.getsize(file_path)
        line_count = input.content.count('\n') + 1 if input.content else 0

        return CallableToolResult(
            data={
                "file_path": file_path,
                "file_size": file_size,
                "bytes_written": file_size,  # Alias for compatibility
                "line_count": line_count,
                "encoding": input.encoding,
                "created": not file_exists,
                "overwritten": file_exists,
            },
            success=True,
            metadata={
                "operation": "create" if not file_exists else "overwrite",
            }
        )

    except UnicodeEncodeError as e:
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Encoding error: {e}. Try different encoding.",
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
                "error_code": "WRITE_ERROR",
                "file_path": file_path,
            }
        )


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
    """Execute file edit with full validation and security checks.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context (permissions, abort signal, etc.)
        on_progress: Optional progress callback

    Returns:
        CallableToolResult with replacement count or error
    """
    # 1. Check sandbox mode for read-only enforcement
    if context.sandbox_mode and hasattr(context.sandbox_mode, 'value'):
        if context.sandbox_mode.value == "READ_ONLY":
            return CallableToolResult(
                data=None,
                success=False,
                error="Edit operation blocked in read-only mode",
                metadata={
                    "error_code": "READ_ONLY_MODE",
                    "file_path": input.file_path,
                }
            )

    # 2. Resolve path (support root_dir from context)
    file_path = input.file_path
    root_dir = context.root_dir or context.metadata.get("root_dir")

    if root_dir and not os.path.isabs(file_path):
        file_path = os.path.join(root_dir, file_path)

    file_path = os.path.abspath(file_path)

    # 3. Security validation: device files
    if file_path.startswith("/dev/"):
        return CallableToolResult(
            data=None,
            success=False,
            error="Cannot edit device files",
            metadata={
                "error_code": "DEVICE_FILE_BLOCKED",
                "file_path": file_path,
            }
        )

    # 4. Security validation: system paths
    restricted_paths = ["/etc", "/usr", "/bin", "/sbin", "/boot", "/sys", "/proc"]
    for restricted in restricted_paths:
        if file_path.startswith(restricted):
            return CallableToolResult(
                data=None,
                success=False,
                error=f"Cannot edit system path: {restricted}",
                metadata={
                    "error_code": "SYSTEM_PATH_BLOCKED",
                    "file_path": file_path,
                }
            )

    # 5. Check permissions (if manager available)
    if context.permission_manager:
        perm_result = await context.check_permission_async(
            tool_name="edit_file",
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

    # 6. Check file exists
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

    # 7. Read file content
    try:
        with open(file_path, 'r', encoding=input.encoding) as f:
            content = f.read()
    except UnicodeDecodeError as e:
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Encoding error reading file: {e}. Try different encoding.",
            metadata={
                "error_code": "ENCODING_ERROR",
                "file_path": file_path,
                "attempted_encoding": input.encoding,
            }
        )
    except Exception as e:
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Failed to read file: {e}",
            metadata={
                "error_code": "READ_ERROR",
                "file_path": file_path,
            }
        )

    # 8. Check if old_string exists in content
    if input.old_string not in content:
        return CallableToolResult(
            data=None,
            success=False,
            error="old_string not found in file",
            metadata={
                "error_code": "STRING_NOT_FOUND",
                "file_path": file_path,
                "old_string": input.old_string[:50] + "..." if len(input.old_string) > 50 else input.old_string,
            }
        )

    # 9. Perform replacement
    count_occurrences = content.count(input.old_string)

    if input.count == -1:
        # Replace all occurrences
        new_content = content.replace(input.old_string, input.new_string)
        replacements_made = count_occurrences
    else:
        # Replace specific number of occurrences
        new_content = content.replace(input.old_string, input.new_string, input.count)
        replacements_made = min(input.count, count_occurrences)

    # 10. Write modified content back
    original_size = os.path.getsize(file_path)

    try:
        with open(file_path, 'w', encoding=input.encoding) as f:
            f.write(new_content)

        new_size = os.path.getsize(file_path)

        return CallableToolResult(
            data={
                "file_path": file_path,
                "replacements_made": replacements_made,
                "occurrences_replaced": replacements_made,  # Alias for compatibility
                "total_occurrences": count_occurrences,
                "encoding": input.encoding,
                "old_string_length": len(input.old_string),
                "new_string_length": len(input.new_string),
                "size_before": original_size,
                "size_after": new_size,
                "size_change": len(new_content) - len(content),
            },
            success=True,
            metadata={
                "operation": "edit",
            }
        )

    except UnicodeEncodeError as e:
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Encoding error writing file: {e}. Try different encoding.",
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
                "error_code": "WRITE_ERROR",
                "file_path": file_path,
            }
        )


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
    """Delete a file with security controls.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context
        on_progress: Optional progress callback

    Returns:
        CallableToolResult with deletion result or error
    """
    # 1. Check sandbox mode for read-only enforcement
    if context.sandbox_mode and hasattr(context.sandbox_mode, 'value'):
        if context.sandbox_mode.value == "READ_ONLY":
            return CallableToolResult(
                data=None,
                success=False,
                error="Delete operation blocked in read-only mode",
                metadata={
                    "error_code": "READ_ONLY_MODE",
                    "file_path": input.file_path,
                }
            )

    # 2. Resolve file path (support root_dir from context)
    file_path = input.file_path
    root_dir = context.root_dir or context.metadata.get("root_dir")

    if root_dir and not os.path.isabs(file_path):
        file_path = os.path.join(root_dir, file_path)

    file_path = os.path.abspath(file_path)

    # 3. Security validation: block device files
    if file_path.startswith("/dev/"):
        return CallableToolResult(
            data=None,
            success=False,
            error="Device files cannot be deleted",
            metadata={
                "error_code": "DEVICE_FILE_BLOCKED",
                "file_path": file_path,
            }
        )

    # 4. Security validation: block system paths
    system_paths = ["/etc", "/usr", "/bin", "/sbin", "/boot", "/sys", "/proc"]
    if any(file_path.startswith(path) for path in system_paths):
        return CallableToolResult(
            data=None,
            success=False,
            error=f"System paths cannot be deleted: {file_path}",
            metadata={
                "error_code": "SYSTEM_PATH_BLOCKED",
                "file_path": file_path,
            }
        )

    # 5. Check permissions (if manager available)
    if context.permission_manager:
        perm_result = await context.check_permission_async(
            tool_name="delete_file",
            input=input.model_dump(),
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

    # 6. Check file exists
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

    # 7. Get file info before deletion
    try:
        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)
    except Exception as e:
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Failed to get file info: {e}",
            metadata={
                "error_code": "STAT_ERROR",
                "file_path": file_path,
            }
        )

    # 8. Delete file
    try:
        os.unlink(file_path)

        return CallableToolResult(
            data={
                "file_path": file_path,
                "file_name": file_name,
                "file_size": file_size,
                "deleted": True,
            },
            success=True,
            metadata={
                "operation": "delete",
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
            error=f"Failed to delete file: {e}",
            metadata={
                "error_code": "DELETE_ERROR",
                "file_path": file_path,
            }
        )


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
    """Create a directory with security controls.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context
        on_progress: Optional progress callback

    Returns:
        CallableToolResult with creation result or error
    """
    from pathlib import Path

    # 1. Check sandbox mode for read-only enforcement
    if context.sandbox_mode and hasattr(context.sandbox_mode, 'value'):
        if context.sandbox_mode.value == "READ_ONLY":
            return CallableToolResult(
                data=None,
                success=False,
                error="Directory creation blocked in read-only mode",
                metadata={
                    "error_code": "READ_ONLY_MODE",
                    "directory_path": input.directory_path,
                }
            )

    # 2. Resolve directory path (support root_dir from context)
    directory_path = input.directory_path
    root_dir = context.root_dir or context.metadata.get("root_dir")

    if root_dir and not os.path.isabs(directory_path):
        directory_path = os.path.join(root_dir, directory_path)

    directory_path = os.path.abspath(directory_path)

    # 3. Security validation: block device paths
    if directory_path.startswith("/dev/"):
        return CallableToolResult(
            data=None,
            success=False,
            error="Cannot create directories in /dev",
            metadata={
                "error_code": "DEVICE_PATH_BLOCKED",
                "directory_path": directory_path,
            }
        )

    # 4. Security validation: block system paths
    system_paths = ["/etc", "/usr", "/bin", "/sbin", "/boot", "/sys", "/proc"]
    if any(directory_path.startswith(path) for path in system_paths):
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Cannot create directories in system paths: {directory_path}",
            metadata={
                "error_code": "SYSTEM_PATH_BLOCKED",
                "directory_path": directory_path,
            }
        )

    # 5. Check permissions (if manager available)
    if context.permission_manager:
        perm_result = await context.check_permission_async(
            tool_name="mkdir",
            input=input.model_dump(),
            tool_content=directory_path
        )

        if perm_result.behavior == PermissionBehavior.DENY:
            return CallableToolResult(
                data=None,
                success=False,
                error=perm_result.reason or "Permission denied",
                metadata={
                    "error_code": "PERMISSION_DENIED",
                    "directory_path": directory_path,
                }
            )

    # 6. Check if directory already exists
    if os.path.exists(directory_path):
        if not input.exist_ok:
            return CallableToolResult(
                data=None,
                success=False,
                error=f"Directory already exists: {directory_path}",
                metadata={
                    "error_code": "DIRECTORY_EXISTS",
                    "directory_path": directory_path,
                }
            )

        if not os.path.isdir(directory_path):
            return CallableToolResult(
                data=None,
                success=False,
                error=f"Path exists but is not a directory: {directory_path}",
                metadata={
                    "error_code": "NOT_A_DIRECTORY",
                    "directory_path": directory_path,
                }
            )

        return CallableToolResult(
            data={
                "directory_path": directory_path,
                "created": False,
                "already_existed": True,
            },
            success=True,
            metadata={
                "operation": "exists",
            }
        )

    # 7. Create directory
    try:
        path_obj = Path(directory_path)
        path_obj.mkdir(parents=input.parents, exist_ok=input.exist_ok, mode=input.mode)

        return CallableToolResult(
            data={
                "directory_path": directory_path,
                "created": True,
                "parents_created": input.parents,
                "mode": oct(input.mode),
            },
            success=True,
            metadata={
                "operation": "create",
            }
        )

    except FileNotFoundError as e:
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Parent directory not found: {e}",
            metadata={
                "error_code": "PARENT_NOT_FOUND",
                "directory_path": directory_path,
            }
        )
    except PermissionError as e:
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Permission denied: {e}",
            metadata={
                "error_code": "OS_PERMISSION_ERROR",
                "directory_path": directory_path,
            }
        )
    except Exception as e:
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Failed to create directory: {e}",
            metadata={
                "error_code": "CREATE_ERROR",
                "directory_path": directory_path,
            }
        )


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
