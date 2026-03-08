"""
Search tools for filesystem operations. Provides tools for searching files and directories 
with pattern matching, content search, and filtering capabilities.
"""

from __future__ import annotations
import os
import re
import fnmatch
import asyncio
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.orchestration.orchestrator import AgentType
from ..base.tool_interface import AsyncToolInterface
from ..base.tool_schemas import (
    ToolSchema, ToolParameter, ParameterType, create_tool_schema, create_parameter
)

_logger = get_logger(__name__)


class GrepSearchTool(AsyncToolInterface):
    """
    Grep-like search tool for file content searching.
    """

    def __init__(self):
        super().__init__()
        self.name = "grep_search"
        self.description = "Search file contents with pattern matching"

        self._schema = create_tool_schema(
            name=self.name,
            description=self.description,
            category="filesystem",
            parameters=[
                create_parameter(
                    name="pattern",
                    param_type=ParameterType.STRING,
                    description="Search pattern (regex or string)",
                    required=True
                ),
                create_parameter(
                    name="directory",
                    param_type=ParameterType.STRING,
                    description="Directory to search in",
                    required=False,
                    default="."
                ),
                create_parameter(
                    name="file_pattern",
                    param_type=ParameterType.STRING,
                    description="File pattern to match (glob)",
                    required=False,
                    default="*"
                ),
                create_parameter(
                    name="recursive",
                    param_type=ParameterType.BOOLEAN,
                    description="Search recursively",
                    required=False,
                    default=True
                ),
                create_parameter(
                    name="case_sensitive",
                    param_type=ParameterType.BOOLEAN,
                    description="Case sensitive search",
                    required=False,
                    default=False
                ),
                create_parameter(
                    name="max_results",
                    param_type=ParameterType.INTEGER,
                    description="Maximum number of results",
                    required=False,
                    default=100
                )
            ],
            returns={
                "type": "object",
                "description": "Search results",
                "properties": {
                    "matches": {"type": "array", "description": "Found matches"},
                    "total_files": {"type": "integer", "description": "Total files searched"},
                    "total_matches": {"type": "integer", "description": "Total matches found"}
                }
            }
        )

    async def execute(self, **kwargs) -> Dict[str, Any]:
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

            search_path = Path(directory)
            if not search_path.exists():
                return self._format_result(
                    success=False,
                    error=f"Directory not found: {directory}"
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
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
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
                    "total_matches": len(matches)
                }
            )

        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Search error: {str(e)}"
            )

    def get_schema(self) -> Dict[str, Any]:
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
        self._schema = create_tool_schema(
            name=self.name,
            description=self.description,
            category="filesystem",
            parameters=[
                create_parameter(
                    name="pattern",
                    param_type=ParameterType.STRING,
                    description="Glob pattern (e.g. **/*.py)",
                    required=True,
                ),
                create_parameter(
                    name="directory",
                    param_type=ParameterType.STRING,
                    description="Directory to search in",
                    required=False,
                    default=".",
                ),
                create_parameter(
                    name="max_results",
                    param_type=ParameterType.INTEGER,
                    description="Maximum number of results",
                    required=False,
                    default=200,
                ),
            ],
            returns={
                "type": "object",
                "description": "Glob results",
                "properties": {
                    "files": {"type": "array"},
                    "total_count": {"type": "integer"},
                },
            },
        )

    async def execute(self, **kwargs) -> Dict[str, Any]:
        try:
            pattern = kwargs["pattern"]
            directory = kwargs.get("directory", ".")
            max_results = int(kwargs.get("max_results", 200))

            base = Path(directory)
            files = [str(p) for p in base.glob(pattern)]
            if len(files) > max_results:
                files = files[:max_results]

            return self._format_result(success=True, result={"files": files, "total_count": len(files)})
        except Exception as e:
            return self._format_result(success=False, error=f"Glob search error: {e}")

    def get_schema(self) -> Dict[str, Any]:
        return self._schema.dict()


class FileFinderTool(AsyncToolInterface):
    """
    File finder tool for locating files by various criteria.
    """

    def __init__(self):
        super().__init__()
        self.name = "file_finder"
        self.description = "Find files by name, size, date, and other criteria"

        self._schema = create_tool_schema(
            name=self.name,
            description=self.description,
            category="filesystem",
            parameters=[
                create_parameter(
                    name="pattern",
                    param_type=ParameterType.STRING,
                    description="File name pattern (glob)",
                    required=True
                ),
                create_parameter(
                    name="directory",
                    param_type=ParameterType.STRING,
                    description="Directory to search in",
                    required=False,
                    default="."
                ),
                create_parameter(
                    name="min_size",
                    param_type=ParameterType.INTEGER,
                    description="Minimum file size in bytes",
                    required=False
                ),
                create_parameter(
                    name="max_size",
                    param_type=ParameterType.INTEGER,
                    description="Maximum file size in bytes",
                    required=False
                ),
                create_parameter(
                    name="min_date",
                    param_type=ParameterType.STRING,
                    description="Minimum modification date (YYYY-MM-DD)",
                    required=False
                ),
                create_parameter(
                    name="max_date",
                    param_type=ParameterType.STRING,
                    description="Maximum modification date (YYYY-MM-DD)",
                    required=False
                ),
                create_parameter(
                    name="max_results",
                    param_type=ParameterType.INTEGER,
                    description="Maximum number of results",
                    required=False,
                    default=100
                )
            ],
            returns={
                "type": "object",
                "description": "File finder results",
                "properties": {
                    "files": {"type": "array", "description": "Found files"},
                    "total_count": {"type": "integer", "description": "Total files found"}
                }
            }
        )

    async def execute(self, **kwargs) -> Dict[str, Any]:
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
            min_size = kwargs.get("min_size")
            max_size = kwargs.get("max_size")
            min_date = kwargs.get("min_date")
            max_date = kwargs.get("max_date")
            max_results = kwargs.get("max_results", 100)

            # Parse dates
            min_timestamp = None
            max_timestamp = None
            
            if min_date:
                from datetime import datetime
                min_timestamp = datetime.strptime(min_date, "%Y-%m-%d").timestamp()
            
            if max_date:
                from datetime import datetime
                max_timestamp = datetime.strptime(max_date, "%Y-%m-%d").timestamp()

            # Search for files
            search_path = Path(directory)
            if not search_path.exists():
                return self._format_result(
                    success=False,
                    error=f"Directory not found: {directory}"
                )

            files = []
            for file_path in search_path.rglob(pattern):
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
                        "modified": stat.st_mtime,
                        "is_directory": False
                    })

                except (OSError, PermissionError):
                    continue

                if len(files) >= max_results:
                    break

            return self._format_result(
                success=True,
                result={
                    "files": files,
                    "total_count": len(files)
                }
            )

        except Exception as e:
            return self._format_result(
                success=False,
                error=f"File finder error: {str(e)}"
            )

    def get_schema(self) -> Dict[str, Any]:
        """
        Get tool schema.
        """
        return self._schema.dict()


# Compatibility alias expected by filesystem __init__.py
FindFilesTool = FileFinderTool
