"""
Search tools for filesystem operations. Provides tools for searching files and directories 
with pattern matching, content search, and filtering capabilities.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools.filesystem_schemas import (
    FILE_FINDER_SCHEMA,
    GLOB_SEARCH_SCHEMA,
    GREP_SEARCH_SCHEMA,
)

_logger = get_logger(__name__)


def _resolve_search_path(tool: AsyncToolInterface, raw_path: str) -> Path:
    """Resolve paths relative to root_dir while preserving absolute paths."""
    path = Path(raw_path)
    if path.is_absolute():
        return path.resolve()
    root_dir = getattr(tool, "root_dir", None)
    if root_dir:
        return (Path(root_dir) / path).resolve()
    return path.resolve()


class GrepSearchTool(AsyncToolInterface):
    """
    Grep-like search tool for file content searching.
    """

    def __init__(self):
        super().__init__()
        self.name = "grep_search"
        self.description = "Search file contents with pattern matching"

        self._schema = GREP_SEARCH_SCHEMA

    async def execute(self, **kwargs) -> dict[str, Any]:
        """
        Execute file content search.
        Args:
            pattern: Search pattern
            directory: Directory to search
            file_pattern: File pattern
            recursive: Search recursively
            case_sensitive: Case sensitive
            max_results: Maximum results
        Returns:
            Dictionary with search results
        """
        try:
            pattern = kwargs["pattern"]
            directory = kwargs.get("directory", ".")
            file_pattern = kwargs.get("file_pattern", "*")
            recursive = kwargs.get("recursive", True)
            case_sensitive = kwargs.get("case_sensitive", False)
            max_results = kwargs.get("max_results", 100)

            # Compile regex pattern
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                regex = re.compile(pattern, flags)
            except re.error as e:
                return self._format_result(
                    success=False,
                    error=f"Invalid regex pattern: {str(e)}"
                )

            # Search files
            matches = []
            files_searched = 0
            truncated = False

            search_path = _resolve_search_path(self, directory)
            if not search_path.exists():
                return self._format_result(
                    success=False,
                    error=f"Directory not found: {directory}"
                )
            if not search_path.is_dir():
                return self._format_result(
                    success=False,
                    error=f"Not a directory: {directory}"
                )

            # Get files to search
            if recursive:
                files = search_path.rglob(file_pattern)
            else:
                files = search_path.glob(file_pattern)

            for file_path in files:
                if file_path.is_file():
                    files_searched += 1
                    
                    # Search in file
                    try:
                        with open(file_path, encoding='utf-8', errors='ignore') as f:
                            for line_num, line in enumerate(f, 1):
                                if regex.search(line):
                                    matches.append({
                                        "file": str(file_path),
                                        "line_number": line_num,
                                        "line": line.rstrip(),
                                        "match": regex.search(line).group()
                                    })
                                    
                                    # Check max results
                                    if len(matches) >= max_results:
                                        truncated = True
                                        break
                    
                    except (UnicodeDecodeError, PermissionError):
                        continue

                if len(matches) >= max_results:
                    break

            return self._format_result(
                success=True,
                result={
                    "matches": matches,
                    "total_files": files_searched,
                    "total_matches": len(matches),
                    "truncated": truncated,
                }
            )

        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Search error: {str(e)}"
            )

    def get_schema(self) -> dict[str, Any]:
        """
        Get tool schema.
        """
        return self._schema.dict()


class GlobSearchTool(AsyncToolInterface):
    """Glob-based file search tool (compatibility name)."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "glob_search"
        self.description = "Find files matching a glob pattern"
        self._schema = GLOB_SEARCH_SCHEMA

    async def execute(self, **kwargs) -> dict[str, Any]:
        try:
            pattern = kwargs["pattern"]
            directory = kwargs.get("directory", ".")
            max_results = int(kwargs.get("max_results", 200))
            include_dirs = bool(kwargs.get("include_dirs", False))
            absolute_paths = bool(kwargs.get("absolute_paths", True))

            base = _resolve_search_path(self, directory)
            if not base.exists():
                return self._format_result(success=False, error=f"Directory not found: {directory}")
            if not base.is_dir():
                return self._format_result(success=False, error=f"Not a directory: {directory}")
            files: list[str] = []
            directories: list[str] = []
            truncated = False

            for match in base.glob(pattern):
                total_so_far = len(files) + len(directories)
                if total_so_far >= max_results:
                    truncated = True
                    break

                if absolute_paths:
                    path_str = str(match.absolute())
                else:
                    try:
                        path_str = str(match.relative_to(base))
                    except ValueError:
                        path_str = str(match)

                if match.is_file():
                    files.append(path_str)
                elif match.is_dir() and include_dirs:
                    directories.append(path_str)

            result = {
                "files": files,
                "total_files": len(files),
                "total_count": len(files) + len(directories),
                "total_matches": len(files) + len(directories),
                "pattern": pattern,
                "directory": str(base.absolute()),
                "truncated": truncated,
            }
            if include_dirs:
                result["directories"] = directories
                result["total_directories"] = len(directories)

            return self._format_result(success=True, result=result)
        except Exception as e:
            return self._format_result(success=False, error=f"Glob search error: {e}")

    def get_schema(self) -> dict[str, Any]:
        return self._schema.dict()


class FileFinderTool(AsyncToolInterface):
    """
    File finder tool for locating files by various criteria.
    """

    def __init__(self):
        super().__init__()
        self.name = "file_finder"
        self.description = "Find files by name, size, date, and other criteria"

        self._schema = FILE_FINDER_SCHEMA

    async def execute(self, **kwargs) -> dict[str, Any]:
        """
        Execute file search.
        Args:
            pattern: File name pattern
            directory: Directory to search
            min_size: Minimum file size
            max_size: Maximum file size
            min_date: Minimum modification date
            max_date: Maximum modification date
            max_results: Maximum results
        Returns:
            Dictionary with search results
        """
        try:
            pattern = kwargs["pattern"]
            directory = kwargs.get("directory", ".")
            recursive = kwargs.get("recursive", True)
            min_size = kwargs.get("min_size")
            max_size = kwargs.get("max_size")
            min_date = kwargs.get("min_date")
            max_date = kwargs.get("max_date")
            max_results = kwargs.get("max_results", 100)

            # Parse dates
            min_timestamp = None
            max_timestamp = None
            
            if min_date:
                min_timestamp = datetime.strptime(min_date, "%Y-%m-%d").timestamp()
            
            if max_date:
                max_timestamp = datetime.strptime(max_date, "%Y-%m-%d").timestamp()

            # Search for files
            search_path = _resolve_search_path(self, directory)
            if not search_path.exists():
                return self._format_result(
                    success=False,
                    error=f"Directory not found: {directory}"
                )
            if not search_path.is_dir():
                return self._format_result(
                    success=False,
                    error=f"Not a directory: {directory}"
                )

            files = []
            truncated = False
            matches = search_path.rglob(pattern) if recursive else search_path.glob(pattern)

            for file_path in matches:
                if not file_path.is_file():
                    continue

                try:
                    stat = file_path.stat()
                    
                    # Size filter
                    if min_size and stat.st_size < min_size:
                        continue
                    
                    if max_size and stat.st_size > max_size:
                        continue
                    
                    # Date filter
                    if min_timestamp and stat.st_mtime < min_timestamp:
                        continue
                    
                    if max_timestamp and stat.st_mtime > max_timestamp:
                        continue
                    
                    files.append({
                        "path": str(file_path),
                        "name": file_path.name,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "modified_date": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d"),
                        "is_directory": False
                    })

                except (OSError, PermissionError):
                    continue

                if len(files) >= max_results:
                    truncated = True
                    break

            return self._format_result(
                success=True,
                result={
                    "files": files,
                    "total_count": len(files),
                    "directory": str(search_path.absolute()),
                    "truncated": truncated,
                }
            )

        except Exception as e:
            return self._format_result(
                success=False,
                error=f"File finder error: {str(e)}"
            )

    def get_schema(self) -> dict[str, Any]:
        """
        Get tool schema.
        """
        return self._schema.dict()


# Compatibility alias expected by filesystem __init__.py
FindFilesTool = FileFinderTool
