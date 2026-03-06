"""File operation tools for the OmniMind system.

Provides comprehensive file manipulation capabilities including
reading, writing, editing, and directory operations with
proper validation and error handling.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Union

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


class FileReadTool(AsyncToolInterface):
    """Tool for reading file contents safely."""
    
    def __init__(self, backend: Optional[BackendProtocol] = None):
        super().__init__()
        self.backend = backend
        self.name = "read_file"
        self.description = "Read contents of a file with optional offset and limit"
    
    def get_schema(self) -> Dict[str, Any]:
        """Return tool schema for validation."""
        return create_tool_schema(
            name=self.name,
            description=self.description,
            category="filesystem",
            parameters=[
                create_parameter(
                    name="file_path",
                    param_type=ParameterType.STRING,
                    description="Path to the file to read",
                    required=True,
                    min_length=1
                ),
                create_parameter(
                    name="offset",
                    param_type=ParameterType.INTEGER,
                    description="Starting line number (1-based)",
                    required=False,
                    default=0,
                    min_value=0
                ),
                create_parameter(
                    name="limit",
                    param_type=ParameterType.INTEGER,
                    description="Maximum number of lines to read",
                    required=False,
                    default=2000,
                    min_value=1,
                    max_value=10000
                )
            ],
            requires_backend=False,
            supported_agents=list(AgentType)
        ).dict()
    
    async def execute(self, file_path: str, offset: int = 0, limit: int = 2000) -> Dict[str, Any]:
        """Execute file read operation."""
        try:
            # Validate file path
            path = Path(file_path)
            if not path.exists():
                return self._format_result(
                    success=False,
                    error=f"File not found: {file_path}"
                )
            
            if not path.is_file():
                return self._format_result(
                    success=False,
                    error=f"Path is not a file: {file_path}"
                )
            
            # Use backend if available, otherwise read directly
            if self.backend:
                result = self.backend.read(file_path, offset=offset, limit=limit)
                return self._format_result(success=True, result=result)
            else:
                # Direct file reading
                with open(path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Apply offset and limit
                if offset > 0:
                    lines = lines[offset:]
                if limit > 0:
                    lines = lines[:limit]
                
                content = ''.join(lines)
                
                return self._format_result(
                    success=True,
                    result=content,
                    metadata={
                        "file_path": str(path),
                        "total_lines": len(lines),
                        "bytes_read": len(content.encode('utf-8'))
                    }
                )
        
        except PermissionError:
            return self._format_result(
                success=False,
                error=f"Permission denied reading file: {file_path}"
            )
        except UnicodeDecodeError as e:
            return self._format_result(
                success=False,
                error=f"Encoding error reading file: {str(e)}"
            )
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Error reading file: {str(e)}"
            )


class FileWriteTool(AsyncToolInterface):
    """Tool for writing content to files safely."""
    
    def __init__(self, backend: Optional[BackendProtocol] = None):
        super().__init__()
        self.backend = backend
        self.name = "write_file"
        self.description = "Write content to a file, creating parent directories if needed"
    
    def get_schema(self) -> Dict[str, Any]:
        """Return tool schema for validation."""
        return create_tool_schema(
            name=self.name,
            description=self.description,
            category="filesystem",
            parameters=[
                create_parameter(
                    name="file_path",
                    param_type=ParameterType.STRING,
                    description="Path to the file to write",
                    required=True,
                    min_length=1
                ),
                create_parameter(
                    name="content",
                    param_type=ParameterType.STRING,
                    description="Content to write to the file",
                    required=True
                ),
                create_parameter(
                    name="create_dirs",
                    param_type=ParameterType.BOOLEAN,
                    description="Create parent directories if they don't exist",
                    required=False,
                    default=True
                ),
                create_parameter(
                    name="backup",
                    param_type=ParameterType.BOOLEAN,
                    description="Create backup of existing file",
                    required=False,
                    default=False
                )
            ],
            requires_backend=False,
            supported_agents=list(AgentType)
        ).dict()
    
    async def execute(
        self, 
        file_path: str, 
        content: str, 
        create_dirs: bool = True,
        backup: bool = False
    ) -> Dict[str, Any]:
        """Execute file write operation."""
        try:
            path = Path(file_path)
            
            # Create parent directories if requested
            if create_dirs:
                path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create backup if requested and file exists
            if backup and path.exists():
                backup_path = path.with_suffix(f"{path.suffix}.backup")
                shutil.copy2(path, backup_path)
                _logger.info("file_backup_created", original=str(path), backup=str(backup_path))
            
            # Use backend if available, otherwise write directly
            if self.backend:
                result = self.backend.write(file_path, content)
                return self._format_result(success=True, result=result)
            else:
                # Direct file writing
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                return self._format_result(
                    success=True,
                    result=f"Successfully wrote {len(content)} characters to {file_path}",
                    metadata={
                        "file_path": str(path),
                        "bytes_written": len(content.encode('utf-8')),
                        "backup_created": backup and path.exists()
                    }
                )
        
        except PermissionError:
            return self._format_result(
                success=False,
                error=f"Permission denied writing to file: {file_path}"
            )
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Error writing file: {str(e)}"
            )


class FileEditTool(AsyncToolInterface):
    """Tool for editing files with search and replace."""
    
    def __init__(self, backend: Optional[BackendProtocol] = None):
        super().__init__()
        self.backend = backend
        self.name = "edit_file"
        self.description = "Edit file by replacing text with new content"
    
    def get_schema(self) -> Dict[str, Any]:
        """Return tool schema for validation."""
        return create_tool_schema(
            name=self.name,
            description=self.description,
            category="filesystem",
            parameters=[
                create_parameter(
                    name="file_path",
                    param_type=ParameterType.STRING,
                    description="Path to the file to edit",
                    required=True,
                    min_length=1
                ),
                create_parameter(
                    name="old_string",
                    param_type=ParameterType.STRING,
                    description="Text to replace",
                    required=True,
                    min_length=1
                ),
                create_parameter(
                    name="new_string",
                    param_type=ParameterType.STRING,
                    description="Replacement text",
                    required=True
                ),
                create_parameter(
                    name="replace_all",
                    param_type=ParameterType.BOOLEAN,
                    description="Replace all occurrences",
                    required=False,
                    default=False
                )
            ],
            requires_backend=False,
            supported_agents=list(AgentType)
        ).dict()
    
    async def execute(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False
    ) -> Dict[str, Any]:
        """Execute file edit operation."""
        try:
            # Use backend if available
            if self.backend:
                result = self.backend.edit(
                    file_path, old_string, new_string, replace_all=replace_all
                )
                return self._format_result(success=True, result=result)
            else:
                # Direct file editing
                path = Path(file_path)
                
                if not path.exists():
                    return self._format_result(
                        success=False,
                        error=f"File not found: {file_path}"
                    )
                
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Perform replacement
                if replace_all:
                    new_content = content.replace(old_string, new_string)
                    replacements = content.count(old_string)
                else:
                    new_content = content.replace(old_string, new_string, 1)
                    replacements = 1 if old_string in content else 0
                
                # Write back
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                return self._format_result(
                    success=True,
                    result=f"Successfully made {replacements} replacement(s)",
                    metadata={
                        "file_path": str(path),
                        "replacements": replacements,
                        "replace_all": replace_all
                    }
                )
        
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Error editing file: {str(e)}"
            )


class DirectoryListTool(AsyncToolInterface):
    """Tool for listing directory contents."""
    
    def __init__(self, backend: Optional[BackendProtocol] = None):
        super().__init__()
        self.backend = backend
        self.name = "list_directory"
        self.description = "List contents of a directory with file information"
    
    def get_schema(self) -> Dict[str, Any]:
        """Return tool schema for validation."""
        return create_tool_schema(
            name=self.name,
            description=self.description,
            category="filesystem",
            parameters=[
                create_parameter(
                    name="directory_path",
                    param_type=ParameterType.STRING,
                    description="Path to the directory to list",
                    required=True,
                    min_length=1
                ),
                create_parameter(
                    name="show_hidden",
                    param_type=ParameterType.BOOLEAN,
                    description="Include hidden files and directories",
                    required=False,
                    default=False
                ),
                create_parameter(
                    name="recursive",
                    param_type=ParameterType.BOOLEAN,
                    description="List directories recursively",
                    required=False,
                    default=False
                )
            ],
            requires_backend=False,
            supported_agents=list(AgentType)
        ).dict()
    
    async def execute(
        self,
        directory_path: str,
        show_hidden: bool = False,
        recursive: bool = False
    ) -> Dict[str, Any]:
        """Execute directory listing operation."""
        try:
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
            
            # Use backend if available
            if self.backend:
                result = self.backend.ls_info(directory_path)
                return self._format_result(success=True, result=result)
            else:
                # Direct directory listing
                items = []
                
                if recursive:
                    pattern = "**/*"
                else:
                    pattern = "*"
                
                for item in path.glob(pattern):
                    if not show_hidden and item.name.startswith('.'):
                        continue
                    
                    try:
                        stat = item.stat()
                        items.append({
                            "name": item.name,
                            "path": str(item),
                            "type": "directory" if item.is_dir() else "file",
                            "size": stat.st_size,
                            "modified": stat.st_mtime,
                            "permissions": oct(stat.st_mode)[-3:]
                        })
                    except Exception as e:
                        _logger.warning("item_stat_failed", item=str(item), error=str(e))
                        continue
                
                return self._format_result(
                    success=True,
                    result={
                        "directory": str(path),
                        "items": items,
                        "total_items": len(items)
                    },
                    metadata={
                        "directory_path": str(path),
                        "show_hidden": show_hidden,
                        "recursive": recursive
                    }
                )
        
        except PermissionError:
            return self._format_result(
                success=False,
                error=f"Permission denied accessing directory: {directory_path}"
            )
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Error listing directory: {str(e)}"
            )


class FileDeleteTool(AsyncToolInterface):
    """Tool for safely deleting files and directories."""
    
    def __init__(self, backend: Optional[BackendProtocol] = None):
        super().__init__()
        self.name = "delete_file"
        self.description = "Delete files or directories safely"
    
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
                    description="Path to file or directory to delete",
                    required=True,
                    min_length=1
                ),
                create_parameter(
                    name="recursive",
                    param_type=ParameterType.BOOLEAN,
                    description="Delete directories recursively",
                    required=False,
                    default=False
                ),
                create_parameter(
                    name="force",
                    param_type=ParameterType.BOOLEAN,
                    description="Force deletion without confirmation",
                    required=False,
                    default=False
                )
            ],
            requires_backend=False,
            supported_agents=[AgentType.CODER, AgentType.ORCHESTRATOR]  # Restricted
        ).dict()
    
    async def execute(
        self,
        path: str,
        recursive: bool = False,
        force: bool = False
    ) -> Dict[str, Any]:
        """Execute file/directory deletion operation."""
        try:
            path_obj = Path(path)
            
            if not path_obj.exists():
                return self._format_result(
                    success=False,
                    error=f"Path not found: {path}"
                )
            
            if path_obj.is_file():
                path_obj.unlink()
                deleted_type = "file"
            elif path_obj.is_dir():
                if recursive:
                    shutil.rmtree(path_obj)
                    deleted_type = "directory (recursive)"
                else:
                    path_obj.rmdir()
                    deleted_type = "directory"
            else:
                return self._format_result(
                    success=False,
                    error=f"Path is neither file nor directory: {path}"
                )
            
            return self._format_result(
                success=True,
                result=f"Successfully deleted {deleted_type}: {path}",
                metadata={
                    "deleted_path": str(path_obj),
                    "deleted_type": deleted_type,
                    "recursive": recursive
                }
            )
        
        except PermissionError:
            return self._format_result(
                success=False,
                error=f"Permission denied deleting: {path}"
            )
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Error deleting: {str(e)}"
            )


class DirectoryCreateTool(AsyncToolInterface):
    """Tool for creating directories."""
    
    def __init__(self, backend: Optional[BackendProtocol] = None):
        super().__init__()
        self.name = "create_directory"
        self.description = "Create directory with parent directories if needed"
    
    def get_schema(self) -> Dict[str, Any]:
        """Return tool schema for validation."""
        return create_tool_schema(
            name=self.name,
            description=self.description,
            category="filesystem",
            parameters=[
                create_parameter(
                    name="directory_path",
                    param_type=ParameterType.STRING,
                    description="Path to the directory to create",
                    required=True,
                    min_length=1
                ),
                create_parameter(
                    name="parents",
                    param_type=ParameterType.BOOLEAN,
                    description="Create parent directories if needed",
                    required=False,
                    default=True
                ),
                create_parameter(
                    name="exist_ok",
                    param_type=ParameterType.BOOLEAN,
                    description="Don't error if directory already exists",
                    required=False,
                    default=True
                )
            ],
            requires_backend=False,
            supported_agents=list(AgentType)
        ).dict()
    
    async def execute(
        self,
        directory_path: str,
        parents: bool = True,
        exist_ok: bool = True
    ) -> Dict[str, Any]:
        """Execute directory creation operation."""
        try:
            path = Path(directory_path)
            
            path.mkdir(parents=parents, exist_ok=exist_ok)
            
            return self._format_result(
                success=True,
                result=f"Successfully created directory: {directory_path}",
                metadata={
                    "directory_path": str(path),
                    "created": not path.exists(),
                    "parents_created": parents
                }
            )
        
        except FileExistsError:
            return self._format_result(
                success=False,
                error=f"Directory already exists: {directory_path}"
            )
        except PermissionError:
            return self._format_result(
                success=False,
                error=f"Permission denied creating directory: {directory_path}"
            )
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Error creating directory: {str(e)}"
            )
