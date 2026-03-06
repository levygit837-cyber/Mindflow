"""Search tools for filesystem operations.

Provides comprehensive search capabilities including pattern
matching, grep-style searching, and file discovery
with proper validation and performance optimization.
"""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Pattern

from deepagents.backends.protocol import BackendProtocol

from omnimind_backend.infra.logging import get_logger
from omnimind_backend.schemas.orchestration.orchestrator import AgentType
from ..base.tool_interface import AsyncToolInterface
from ..base.tool_schemas import (
    ToolSchema, 
    ToolParameter, 
    ParameterType,
    create_tool_schema,
    create_parameter
)

_logger = get_logger(__name__)


class GrepSearchTool(AsyncToolInterface):
    """Tool for searching text patterns in files."""
    
    def __init__(self, backend: Optional[BackendProtocol] = None):
        super().__init__()
        self.backend = backend
        self.name = "grep_search"
        self.description = "Search for text patterns in files using grep-like functionality"
    
    def get_schema(self) -> Dict[str, Any]:
        """Return tool schema for validation."""
        return create_tool_schema(
            name=self.name,
            description=self.description,
            category="filesystem",
            parameters=[
                create_parameter(
                    name="pattern",
                    param_type=ParameterType.STRING,
                    description="Text pattern to search for (supports regex)",
                    required=True,
                    min_length=1
                ),
                create_parameter(
                    name="path",
                    param_type=ParameterType.STRING,
                    description="Directory path to search in",
                    required=False,
                    default="."
                ),
                create_parameter(
                    name="glob",
                    param_type=ParameterType.STRING,
                    description="File pattern to match (e.g., '*.py')",
                    required=False,
                    default="*"
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
                    description="Maximum number of results to return",
                    required=False,
                    default=100,
                    min_value=1,
                    max_value=1000
                ),
                create_parameter(
                    name="context_lines",
                    param_type=ParameterType.INTEGER,
                    description="Number of context lines around matches",
                    required=False,
                    default=2,
                    min_value=0,
                    max_value=10
                )
            ],
            requires_backend=False,
            supported_agents=list(AgentType)
        ).dict()
    
    async def execute(
        self,
        pattern: str,
        path: str = ".",
        glob: str = "*",
        case_sensitive: bool = False,
        max_results: int = 100,
        context_lines: int = 2
    ) -> Dict[str, Any]:
        """Execute grep search operation."""
        try:
            search_path = Path(path)
            
            if not search_path.exists():
                return self._format_result(
                    success=False,
                    error=f"Search path not found: {path}"
                )
            
            # Use backend if available
            if self.backend:
                result = self.backend.grep_raw(pattern, path=path, glob=glob)
                return self._format_result(success=True, result=result)
            
            # Compile regex pattern
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                regex_pattern = re.compile(pattern, flags)
            except re.error as e:
                return self._format_result(
                    success=False,
                    error=f"Invalid regex pattern: {str(e)}"
                )
            
            # Search files
            matches = []
            files_searched = 0
            
            for file_path in search_path.rglob(glob):
                if file_path.is_file():
                    files_searched += 1
                    
                    try:
                        matches.extend(
                            self._search_in_file(
                                file_path, regex_pattern, context_lines
                            )
                        )
                        
                        # Check max results limit
                        if len(matches) >= max_results:
                            break
                            
                    except (UnicodeDecodeError, PermissionError) as e:
                        _logger.warning(
                            "file_search_failed",
                            file=str(file_path),
                            error=str(e)
                        )
                        continue
            
            return self._format_result(
                success=True,
                result={
                    "pattern": pattern,
                    "search_path": str(search_path),
                    "file_pattern": glob,
                    "matches": matches[:max_results],
                    "total_matches": len(matches),
                    "files_searched": files_searched,
                    "case_sensitive": case_sensitive,
                    "context_lines": context_lines
                },
                metadata={
                    "search_performance": {
                        "files_searched": files_searched,
                        "matches_found": len(matches),
                        "truncated": len(matches) > max_results
                    }
                }
            )
        
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Error during search: {str(e)}"
            )
    
    def _search_in_file(
        self, 
        file_path: Path, 
        pattern: Pattern, 
        context_lines: int
    ) -> List[Dict[str, Any]]:
        """Search for pattern in a single file."""
        matches = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                for match in pattern.finditer(line):
                    # Extract context
                    start_line = max(0, line_num - context_lines - 1)
                    end_line = min(len(lines), line_num + context_lines)
                    
                    context = ''.join(lines[start_line:end_line])
                    
                    matches.append({
                        "file": str(file_path),
                        "line_number": line_num,
                        "line_content": line.strip(),
                        "match_text": match.group(),
                        "match_start": match.start(),
                        "match_end": match.end(),
                        "context": context.strip(),
                        "context_start_line": start_line + 1,
                        "context_end_line": end_line
                    })
        
        except Exception as e:
            _logger.warning("file_search_error", file=str(file_path), error=str(e))
        
        return matches


class GlobSearchTool(AsyncToolInterface):
    """Tool for finding files using glob patterns."""
    
    def __init__(self, backend: Optional[BackendProtocol] = None):
        super().__init__()
        self.backend = backend
        self.name = "glob_search"
        self.description = "Find files using glob patterns"
    
    def get_schema(self) -> Dict[str, Any]:
        """Return tool schema for validation."""
        return create_tool_schema(
            name=self.name,
            description=self.description,
            category="filesystem",
            parameters=[
                create_parameter(
                    name="pattern",
                    param_type=ParameterType.STRING,
                    description="Glob pattern to match files",
                    required=True,
                    min_length=1
                ),
                create_parameter(
                    name="path",
                    param_type=ParameterType.STRING,
                    description="Directory path to search in",
                    required=False,
                    default="/"
                ),
                create_parameter(
                    name="recursive",
                    param_type=ParameterType.BOOLEAN,
                    description="Search recursively in subdirectories",
                    required=False,
                    default=True
                ),
                create_parameter(
                    name="include_hidden",
                    param_type=ParameterType.BOOLEAN,
                    description="Include hidden files and directories",
                    required=False,
                    default=False
                ),
                create_parameter(
                    name="max_results",
                    param_type=ParameterType.INTEGER,
                    description="Maximum number of results to return",
                    required=False,
                    default=100,
                    min_value=1,
                    max_value=1000
                )
            ],
            requires_backend=False,
            supported_agents=list(AgentType)
        ).dict()
    
    async def execute(
        self,
        pattern: str,
        path: str = "/",
        recursive: bool = True,
        include_hidden: bool = False,
        max_results: int = 100
    ) -> Dict[str, Any]:
        """Execute glob search operation."""
        try:
            search_path = Path(path)
            
            if not search_path.exists():
                return self._format_result(
                    success=False,
                    error=f"Search path not found: {path}"
                )
            
            # Use backend if available
            if self.backend:
                result = self.backend.glob_info(pattern, path=path)
                return self._format_result(success=True, result=result)
            
            # Perform glob search
            if recursive:
                glob_pattern = f"**/{pattern}"
            else:
                glob_pattern = pattern
            
            matches = []
            
            for item in search_path.glob(glob_pattern):
                if not include_hidden and any(part.startswith('.') for part in item.parts):
                    continue
                
                try:
                    stat = item.stat()
                    matches.append({
                        "path": str(item),
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                        "relative_path": str(item.relative_to(search_path))
                    })
                except Exception as e:
                    _logger.warning("item_stat_failed", item=str(item), error=str(e))
                    continue
                
                if len(matches) >= max_results:
                    break
            
            return self._format_result(
                success=True,
                result={
                    "pattern": pattern,
                    "search_path": str(search_path),
                    "matches": matches,
                    "total_matches": len(matches),
                    "recursive": recursive,
                    "include_hidden": include_hidden
                },
                metadata={
                    "search_performance": {
                        "items_found": len(matches),
                        "truncated": len(matches) > max_results
                    }
                }
            )
        
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Error during glob search: {str(e)}"
            )


class FindFilesTool(AsyncToolInterface):
    """Advanced tool for finding files with multiple criteria."""
    
    def __init__(self, backend: Optional[BackendProtocol] = None):
        super().__init__()
        self.backend = backend
        self.name = "find_files"
        self.description = "Find files with advanced criteria (name, size, date, type)"
    
    def get_schema(self) -> Dict[str, Any]:
        """Return tool schema for validation."""
        return create_tool_schema(
            name=self.name,
            description=self.description,
            category="filesystem",
            parameters=[
                create_parameter(
                    name="path",
                    param_type=ParameterType.STRING,
                    description="Directory path to search in",
                    required=False,
                    default="."
                ),
                create_parameter(
                    name="name_pattern",
                    param_type=ParameterType.STRING,
                    description="Name pattern (supports wildcards)",
                    required=False
                ),
                create_parameter(
                    name="file_type",
                    param_type=ParameterType.STRING,
                    description="File type filter (file, directory, both)",
                    required=False,
                    default="both",
                    enum=["file", "directory", "both"]
                ),
                create_parameter(
                    name="min_size",
                    param_type=ParameterType.INTEGER,
                    description="Minimum file size in bytes",
                    required=False,
                    min_value=0
                ),
                create_parameter(
                    name="max_size",
                    param_type=ParameterType.INTEGER,
                    description="Maximum file size in bytes",
                    required=False,
                    min_value=0
                ),
                create_parameter(
                    name="extension",
                    param_type=ParameterType.STRING,
                    description="File extension filter (e.g., 'py', 'txt')",
                    required=False
                ),
                create_parameter(
                    name="max_results",
                    param_type=ParameterType.INTEGER,
                    description="Maximum number of results",
                    required=False,
                    default=100,
                    min_value=1,
                    max_value=1000
                )
            ],
            requires_backend=False,
            supported_agents=list(AgentType)
        ).dict()
    
    async def execute(
        self,
        path: str = ".",
        name_pattern: Optional[str] = None,
        file_type: str = "both",
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        extension: Optional[str] = None,
        max_results: int = 100
    ) -> Dict[str, Any]:
        """Execute advanced file search."""
        try:
            search_path = Path(path)
            
            if not search_path.exists():
                return self._format_result(
                    success=False,
                    error=f"Search path not found: {path}"
                )
            
            matches = []
            
            for item in search_path.rglob("*"):
                # Apply filters
                if not self._matches_criteria(
                    item, name_pattern, file_type, min_size, max_size, extension
                ):
                    continue
                
                try:
                    stat = item.stat()
                    matches.append({
                        "path": str(item),
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                        "extension": item.suffix.lower().lstrip('.') if item.suffix else None,
                        "relative_path": str(item.relative_to(search_path))
                    })
                except Exception as e:
                    _logger.warning("item_stat_failed", item=str(item), error=str(e))
                    continue
                
                if len(matches) >= max_results:
                    break
            
            return self._format_result(
                success=True,
                result={
                    "search_path": str(search_path),
                    "criteria": {
                        "name_pattern": name_pattern,
                        "file_type": file_type,
                        "min_size": min_size,
                        "max_size": max_size,
                        "extension": extension
                    },
                    "matches": matches,
                    "total_matches": len(matches)
                },
                metadata={
                    "search_performance": {
                        "items_found": len(matches),
                        "truncated": len(matches) > max_results
                    }
                }
            )
        
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Error during file search: {str(e)}"
            )
    
    def _matches_criteria(
        self,
        item: Path,
        name_pattern: Optional[str],
        file_type: str,
        min_size: Optional[int],
        max_size: Optional[int],
        extension: Optional[str]
    ) -> bool:
        """Check if item matches all search criteria."""
        try:
            # File type filter
            if file_type != "both":
                if file_type == "file" and not item.is_file():
                    return False
                elif file_type == "directory" and not item.is_dir():
                    return False
            
            # Name pattern filter
            if name_pattern and not fnmatch.fnmatch(item.name, name_pattern):
                return False
            
            # Size filter (only for files)
            if item.is_file():
                stat = item.stat()
                file_size = stat.st_size
                
                if min_size is not None and file_size < min_size:
                    return False
                if max_size is not None and file_size > max_size:
                    return False
            
            # Extension filter
            if extension and item.suffix.lower().lstrip('.') != extension.lower():
                return False
            
            return True
            
        except Exception:
            return False
