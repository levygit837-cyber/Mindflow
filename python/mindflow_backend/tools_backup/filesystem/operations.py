"""Filesystem operation tools for MindFlow backend.

Provides core file and directory operations with security,
validation, and error handling.
"""

from __future__ import annotations

import os
import shutil
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.interfaces.tools.base import AsyncToolInterface
from mindflow_backend.schemas.tools.tool_config import create_tool_schema
from mindflow_backend.schemas.orchestration.orchestrator import AgentType

_logger = get_logger(__name__)


class DirectoryListTool(AsyncToolInterface):
    """Tool for listing directory contents."""
    
    def __init__(self, backend: Optional[Any] = None):
        """Initialize the directory list tool.
        
        Args:
            backend: Optional backend for compatibility
        """
        super().__init__()
        self.backend = backend
        self.name = "list_directory"
        self.description = "List directory contents with detailed information"
        
        self._schema = create_tool_schema(
            name=self.name,
            description=self.description,
            category="filesystem",
            parameters=[
                {
                    "name": "directory_path",
                    "type": "string",
                    "description": "Path to directory to list",
                    "required": True,
                    "format": "file-path"
                },
                {
                    "name": "show_hidden",
                    "type": "boolean",
                    "description": "Show hidden files and directories",
                    "required": False,
                    "default": False
                },
                {
                    "name": "recursive",
                    "type": "boolean",
                    "description": "List recursively",
                    "required": False,
                    "default": False
                }
            ],
            returns={
                "type": "object",
                "description": "Directory listing",
                "properties": {
                    "items": {"type": "array", "description": "Directory items"},
                    "count": {"type": "integer", "description": "Number of items"}
                }
            }
        )
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """List directory contents.
        
        Args:
            directory_path: Path to directory to list
            show_hidden: Show hidden files (default: False)
            recursive: List recursively (default: False)
            
        Returns:
            Dictionary with directory listing
        """
        try:
            directory_path = kwargs["directory_path"]
            show_hidden = kwargs.get("show_hidden", False)
            recursive = kwargs.get("recursive", False)
            
            path = Path(directory_path)
            if not path.exists():
                return self._format_result(
                    success=False,
                    error=f"Directory not found: {directory_path}"
                )
            
            if not path.is_dir():
                return self._format_result(
                    success=False,
                    error=f"Path is not a directory: {directory_path}"
                )
            
            items = []
            
            if recursive:
                pattern = "**/*"
            else:
                pattern = "*"
            
            for item_path in path.glob(pattern):
                # Skip hidden files if not requested
                if not show_hidden and item_path.name.startswith('.'):
                    continue
                
                try:
                    stat = item_path.stat()
                    item_info = {
                        "name": item_path.name,
                        "path": str(item_path.absolute()),
                        "type": "directory" if item_path.is_dir() else "file",
                        "size": stat.st_size if item_path.is_file() else 0,
                        "modified": stat.st_mtime,
                        "permissions": oct(stat.st_mode)[-3:]
                    }
                    items.append(item_info)
                except (OSError, PermissionError):
                    continue
            
            return self._format_result(
                success=True,
                result={
                    "items": items,
                    "count": len(items),
                    "directory": str(path.absolute())
                }
            )
            
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Directory listing failed: {str(e)}"
            )
    
    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema."""
        return self._schema.dict()


class DirectoryCreateTool(AsyncToolInterface):
    """Tool for creating directories."""
    
    def __init__(self, backend: Optional[Any] = None):
        """Initialize the directory create tool.
        
        Args:
            backend: Optional backend for compatibility
        """
        super().__init__()
        self.backend = backend
        self.name = "create_directory"
        self.description = "Create directories with parent creation support"
        
        self._schema = create_tool_schema(
            name=self.name,
            description=self.description,
            category="filesystem",
            parameters=[
                {
                    "name": "directory_path",
                    "type": "string",
                    "description": "Path to directory to create",
                    "required": True,
                    "format": "file-path"
                },
                {
                    "name": "parents",
                    "type": "boolean",
                    "description": "Create parent directories if needed",
                    "required": False,
                    "default": True
                },
                {
                    "name": "exist_ok",
                    "type": "boolean",
                    "description": "Don't error if directory already exists",
                    "required": False,
                    "default": True
                }
            ],
            returns={
                "type": "object",
                "description": "Directory creation result",
                "properties": {
                    "created": {"type": "boolean", "description": "Whether directory was created"},
                    "path": {"type": "string", "description": "Directory path"}
                }
            }
        )
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Create directory.
        
        Args:
            directory_path: Path to directory to create
            parents: Create parent directories (default: True)
            exist_ok: Don't error if exists (default: True)
            
        Returns:
            Dictionary with creation result
        """
        try:
            directory_path = kwargs["directory_path"]
            parents = kwargs.get("parents", True)
            exist_ok = kwargs.get("exist_ok", True)
            
            path = Path(directory_path)
            
            if path.exists():
                if path.is_dir():
                    return self._format_result(
                        success=True,
                        result={
                            "created": False,
                            "path": str(path.absolute()),
                            "message": "Directory already exists"
                        }
                    )
                else:
                    return self._format_result(
                        success=False,
                        error=f"Path exists but is not a directory: {directory_path}"
                    )
            
            path.mkdir(parents=parents, exist_ok=exist_ok)
            
            return self._format_result(
                success=True,
                result={
                    "created": True,
                    "path": str(path.absolute())
                }
            )
            
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Directory creation failed: {str(e)}"
            )
    
    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema."""
        return self._schema.dict()


class FileDeleteTool(AsyncToolInterface):
    """Tool for deleting files and directories."""
    
    def __init__(self, backend: Optional[Any] = None):
        """Initialize the file delete tool.
        
        Args:
            backend: Optional backend for compatibility
        """
        super().__init__()
        self.backend = backend
        self.name = "delete_file"
        self.description = "Delete files and directories safely"
        
        self._schema = create_tool_schema(
            name=self.name,
            description=self.description,
            category="filesystem",
            parameters=[
                {
                    "name": "path",
                    "type": "string",
                    "description": "Path to file or directory to delete",
                    "required": True,
                    "format": "file-path"
                },
                {
                    "name": "recursive",
                    "type": "boolean",
                    "description": "Delete directories recursively",
                    "required": False,
                    "default": False
                },
                {
                    "name": "ignore_missing",
                    "type": "boolean",
                    "description": "Don't error if path doesn't exist",
                    "required": False,
                    "default": True
                }
            ],
            returns={
                "type": "object",
                "description": "Deletion result",
                "properties": {
                    "deleted": {"type": "boolean", "description": "Whether path was deleted"},
                    "path": {"type": "string", "description": "Path that was deleted"}
                }
            }
        )
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Delete file or directory.
        
        Args:
            path: Path to delete
            recursive: Delete directories recursively (default: False)
            ignore_missing: Don't error if missing (default: True)
            
        Returns:
            Dictionary with deletion result
        """
        try:
            path = kwargs["path"]
            recursive = kwargs.get("recursive", False)
            ignore_missing = kwargs.get("ignore_missing", True)
            
            path_obj = Path(path)
            
            if not path_obj.exists():
                if ignore_missing:
                    return self._format_result(
                        success=True,
                        result={
                            "deleted": False,
                            "path": str(path_obj.absolute()),
                            "message": "Path does not exist"
                        }
                    )
                else:
                    return self._format_result(
                        success=False,
                        error=f"Path not found: {path}"
                    )
            
            if path_obj.is_file():
                path_obj.unlink()
                deleted = True
            elif path_obj.is_dir():
                if recursive:
                    shutil.rmtree(path_obj)
                else:
                    path_obj.rmdir()
                deleted = True
            else:
                return self._format_result(
                    success=False,
                    error=f"Path is neither file nor directory: {path}"
                )
            
            return self._format_result(
                success=True,
                result={
                    "deleted": deleted,
                    "path": str(path_obj.absolute())
                }
            )
            
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Deletion failed: {str(e)}"
            )
    
    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema."""
        return self._schema.dict()
