"""
Filesystem operation tools for MindFlow backend. Provides comprehensive file and directory operations 
with security controls, validation, and error handling. 
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools.filesystem_schemas import (
    DELETE_FILE_SCHEMA,
    EDIT_FILE_SCHEMA,
    LIST_DIRECTORY_SCHEMA,
    READ_FILE_SCHEMA,
    WRITE_FILE_SCHEMA,
)

_logger = get_logger(__name__)


class FileReadTool(AsyncToolInterface):
    """
    File reading tool with security controls and validation.
    """

    def __init__(self):
        super().__init__()
        self.name = "read_file"
        self.description = "Read file contents with security controls"
        
        # Security settings
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.allowed_extensions = {
            '.txt', '.py', '.js', '.html', '.css', '.json', '.xml',
            '.md', '.yml', '.yaml', '.csv', '.log', '.conf',
            '.ini', '.cfg', '.toml', '.env', '.gitignore'
        }
        self.restricted_paths = {
            '/etc', '/usr', '/bin', '/sbin', '/boot', '/sys',
            '/proc', '/dev', '/root', '/var/log'
        }

        self._schema = READ_FILE_SCHEMA

    async def execute(self, **kwargs) -> dict[str, Any]:
        """
        Read file contents with security validation.
        Args:
            file_path: Path to the file
            encoding: File encoding
            max_lines: Maximum lines to read
        Returns:
            Dictionary with file content and metadata
        """
        try:
            file_path = kwargs["file_path"]
            encoding = kwargs.get("encoding", "utf-8")
            max_lines = kwargs.get("max_lines")

            # Security validation
            validation_result = self._validate_path(file_path)
            if not validation_result["valid"]:
                return self._format_result(
                    success=False,
                    error=validation_result["error"]
                )

            # Convert to Path object
            path_obj = Path(file_path)

            # Check if file exists
            if not path_obj.exists():
                return self._format_result(
                    success=False,
                    error=f"File not found: {file_path}"
                )

            # Check if it's a file
            if not path_obj.is_file():
                return self._format_result(
                    success=False,
                    error=f"Path is not a file: {file_path}"
                )

            # Check file size
            file_size = path_obj.stat().st_size
            if file_size > self.max_file_size:
                return self._format_result(
                    success=False,
                    error=f"File too large: {file_size} bytes (max: {self.max_file_size})"
                )

            # Read file
            with open(path_obj, encoding=encoding) as file:
                if max_lines:
                    lines = []
                    for i, line in enumerate(file):
                        if i >= max_lines:
                            break
                        lines.append(line.rstrip('\n\r'))
                    content = '\n'.join(lines)
                    line_count = len(lines)
                else:
                    content = file.read()
                    line_count = content.count('\n') + 1 if content else 0

            return self._format_result(
                success=True,
                result={
                    "content": content,
                    "line_count": line_count,
                    "file_size": file_size,
                    "encoding": encoding,
                    "file_path": str(path_obj.absolute())
                }
            )

        except UnicodeDecodeError as e:
            return self._format_result(
                success=False,
                error=f"Encoding error: {str(e)}"
            )
        except PermissionError as e:
            return self._format_result(
                success=False,
                error=f"Permission denied: {str(e)}"
            )
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"File read error: {str(e)}"
            )

    def _validate_path(self, file_path: str) -> dict[str, Any]:
        """
        Validate file path for security restrictions.
        Args:
            file_path: File path to validate
        Returns:
            Validation result
        """
        try:
            path_obj = Path(file_path).resolve()
            
            # Check restricted paths
            for restricted in self.restricted_paths:
                if str(path_obj).startswith(restricted):
                    return {
                        "valid": False,
                        "error": f"Access to restricted path denied: {restricted}"
                    }

            # Check file extension
            if path_obj.suffix.lower() not in self.allowed_extensions:
                return {
                    "valid": False,
                    "error": f"File type not allowed: {path_obj.suffix}"
                }

            return {"valid": True}

        except Exception as e:
            return {
                "valid": False,
                "error": f"Path validation error: {str(e)}"
            }

    def get_schema(self) -> dict[str, Any]:
        """
        Get tool schema.
        """
        return self._schema.dict()


class FileEditTool(AsyncToolInterface):
    """Simple file edit tool (single replace).

    This is a minimal implementation used by the unified filesystem tool registry.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "edit_file"
        self.description = "Edit a file by replacing a substring (single occurrence)"

        self.restricted_paths = {
            "/etc", "/usr", "/bin", "/sbin", "/boot", "/sys",
            "/proc", "/dev", "/root", "/var/log",
        }

        self._schema = EDIT_FILE_SCHEMA

    async def execute(self, **kwargs) -> dict[str, Any]:
        file_path = kwargs["file_path"]
        old_string = kwargs["old_string"]
        new_string = kwargs["new_string"]
        count = int(kwargs.get("count", 1))
        encoding = kwargs.get("encoding", "utf-8")

        validation_result = self._validate_path(file_path)
        if not validation_result["valid"]:
            return {"success": False, "error": validation_result["error"]}

        path_obj = Path(file_path)
        if not path_obj.exists() or not path_obj.is_file():
            return {"success": False, "error": f"File not found: {file_path}"}

        content = path_obj.read_text(encoding=encoding)
        if old_string not in content:
            return {"success": False, "error": "old_string not found in file"}

        new_content = content.replace(old_string, new_string, count)
        replacements = 1 if count == 1 else content.count(old_string)
        path_obj.write_text(new_content, encoding=encoding)

        return {"success": True, "replacements": replacements}

    def _validate_path(self, file_path: str) -> dict[str, Any]:
        try:
            path_obj = Path(file_path).resolve()
            for restricted in self.restricted_paths:
                if str(path_obj).startswith(restricted):
                    return {"valid": False, "error": f"Access denied: {restricted}"}
            return {"valid": True}
        except Exception as e:
            return {"valid": False, "error": f"Path validation error: {e}"}

    def get_schema(self) -> dict[str, Any]:
        return self._schema.dict()


class FileWriteTool(AsyncToolInterface):
    """
    File writing tool with security controls and validation.
    """

    def __init__(self):
        super().__init__()
        self.name = "write_file"
        self.description = "Write content to files with security controls"
        
        # Security settings
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.allowed_extensions = {
            '.txt', '.py', '.js', '.html', '.css', '.json', '.xml',
            '.md', '.yml', '.yaml', '.csv', '.log', '.conf',
            '.ini', '.cfg', '.toml', '.env', '.gitignore'
        }
        self.restricted_paths = {
            '/etc', '/usr', '/bin', '/sbin', '/boot', '/sys',
            '/proc', '/dev', '/root', '/var/log'
        }

        self._schema = WRITE_FILE_SCHEMA

    async def execute(self, **kwargs) -> dict[str, Any]:
        """
        Write content to file with security validation.
        Args:
            file_path: Path to the file
            content: Content to write
            encoding: File encoding
            create_dirs: Create parent directories
        Returns:
            Dictionary with write operation result
        """
        try:
            file_path = kwargs["file_path"]
            content = kwargs["content"]
            encoding = kwargs.get("encoding", "utf-8")
            create_dirs = kwargs.get("create_dirs", True)

            # Security validation
            validation_result = self._validate_path(file_path)
            if not validation_result["valid"]:
                return self._format_result(
                    success=False,
                    error=validation_result["error"]
                )

            # Check content size
            content_size = len(content.encode(encoding))
            if content_size > self.max_file_size:
                return self._format_result(
                    success=False,
                    error=f"Content too large: {content_size} bytes (max: {self.max_file_size})"
                )

            # Convert to Path object
            path_obj = Path(file_path)

            # Create parent directories if needed
            if create_dirs:
                path_obj.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            with open(path_obj, 'w', encoding=encoding) as file:
                bytes_written = file.write(content)

            return self._format_result(
                success=True,
                result={
                    "bytes_written": bytes_written,
                    "file_path": str(path_obj.absolute()),
                    "encoding": encoding
                }
            )

        except PermissionError as e:
            return self._format_result(
                success=False,
                error=f"Permission denied: {str(e)}"
            )
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"File write error: {str(e)}"
            )

    def _validate_path(self, file_path: str) -> dict[str, Any]:
        """
        Validate file path for security restrictions.
        Args:
            file_path: File path to validate
        Returns:
            Validation result
        """
        try:
            path_obj = Path(file_path).resolve()
            
            # Check restricted paths
            for restricted in self.restricted_paths:
                if str(path_obj).startswith(restricted):
                    return {
                        "valid": False,
                        "error": f"Access to restricted path denied: {restricted}"
                    }

            # Check file extension
            if path_obj.suffix.lower() not in self.allowed_extensions:
                return {
                    "valid": False,
                    "error": f"File type not allowed: {path_obj.suffix}"
                }

            return {"valid": True}

        except Exception as e:
            return {
                "valid": False,
                "error": f"Path validation error: {str(e)}"
            }

    def get_schema(self) -> dict[str, Any]:
        """
        Get tool schema.
        """
        return self._schema.dict()


class DirectoryListTool(AsyncToolInterface):
    """
    Directory listing tool with security controls.
    """

    def __init__(self):
        super().__init__()
        self.name = "list_directory"
        self.description = "List directory contents with security controls"
        
        # Security settings
        self.restricted_paths = {
            '/etc', '/usr', '/bin', '/sbin', '/boot', '/sys',
            '/proc', '/dev', '/root', '/var/log'
        }

        self._schema = LIST_DIRECTORY_SCHEMA

    async def execute(self, **kwargs) -> dict[str, Any]:
        """
        List directory contents with security validation.
        Args:
            directory_path: Path to the directory
            show_hidden: Include hidden files
            recursive: List recursively
            pattern: Filter pattern
        Returns:
            Dictionary with directory listing
        """
        try:
            directory_path = kwargs["directory_path"]
            show_hidden = kwargs.get("show_hidden", False)
            recursive = kwargs.get("recursive", False)
            pattern = kwargs.get("pattern")

            # Security validation
            validation_result = self._validate_path(directory_path)
            if not validation_result["valid"]:
                return self._format_result(
                    success=False,
                    error=validation_result["error"]
                )

            # Convert to Path object
            path_obj = Path(directory_path)

            # Check if directory exists
            if not path_obj.exists():
                return self._format_result(
                    success=False,
                    error=f"Directory not found: {directory_path}"
                )

            # Check if it's a directory
            if not path_obj.is_dir():
                return self._format_result(
                    success=False,
                    error=f"Path is not a directory: {directory_path}"
                )

            # List directory
            files = []
            directories = []

            if recursive:
                items = path_obj.rglob("*") if not pattern else path_obj.rglob(pattern)
            else:
                items = path_obj.iterdir()

            for item in items:
                # Skip hidden files if not requested
                if not show_hidden and item.name.startswith('.'):
                    continue

                if item.is_file():
                    files.append({
                        "name": item.name,
                        "path": str(item),
                        "size": item.stat().st_size,
                        "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                    })
                elif item.is_dir():
                    directories.append({
                        "name": item.name,
                        "path": str(item),
                        "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                    })

            return self._format_result(
                success=True,
                result={
                    "files": files,
                    "directories": directories,
                    "total_count": len(files) + len(directories),
                    "directory_path": str(path_obj.absolute())
                }
            )

        except PermissionError as e:
            return self._format_result(
                success=False,
                error=f"Permission denied: {str(e)}"
            )
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Directory listing error: {str(e)}"
            )

    def _validate_path(self, directory_path: str) -> dict[str, Any]:
        """
        Validate directory path for security restrictions.
        Args:
            directory_path: Directory path to validate
        Returns:
            Validation result
        """
        try:
            path_obj = Path(directory_path).resolve()
            
            # Check restricted paths
            for restricted in self.restricted_paths:
                if str(path_obj).startswith(restricted):
                    return {
                        "valid": False,
                        "error": f"Access to restricted path denied: {restricted}"
                    }

            return {"valid": True}

        except Exception as e:
            return {
                "valid": False,
                "error": f"Path validation error: {str(e)}"
            }

    def get_schema(self) -> dict[str, Any]:
        """
        Get tool schema.
        """
        return self._schema.dict()


class FileDeleteTool(AsyncToolInterface):
    """
    File deletion tool with security controls.
    """

    def __init__(self):
        super().__init__()
        self.name = "delete_file"
        self.description = "Delete files with security controls"
        
        # Security settings
        self.restricted_paths = {
            '/etc', '/usr', '/bin', '/sbin', '/boot', '/sys',
            '/proc', '/dev', '/root', '/var/log'
        }

        self._schema = DELETE_FILE_SCHEMA

    async def execute(self, **kwargs) -> dict[str, Any]:
        """
        Delete file or directory with security validation.
        Args:
            file_path: Path to delete
            recursive: Delete recursively
            force: Force deletion
        Returns:
            Dictionary with deletion result
        """
        try:
            file_path = kwargs["file_path"]
            recursive = kwargs.get("recursive", False)
            force = kwargs.get("force", False)

            # Security validation
            validation_result = self._validate_path(file_path)
            if not validation_result["valid"]:
                return self._format_result(
                    success=False,
                    error=validation_result["error"]
                )

            # Convert to Path object
            path_obj = Path(file_path)

            # Check if path exists
            if not path_obj.exists():
                return self._format_result(
                    success=False,
                    error=f"Path not found: {file_path}"
                )

            # Delete file or directory
            if path_obj.is_file():
                path_obj.unlink()
                deleted_type = "file"
            elif path_obj.is_dir():
                if recursive:
                    shutil.rmtree(path_obj)
                    deleted_type = "directory (recursive)"
                else:
                    try:
                        path_obj.rmdir()
                        deleted_type = "directory"
                    except OSError as e:
                        return self._format_result(
                            success=False,
                            error=f"Directory not empty, use recursive: {str(e)}"
                        )
            else:
                return self._format_result(
                    success=False,
                    error=f"Path is neither file nor directory: {file_path}"
                )

            return self._format_result(
                success=True,
                result={
                    "deleted": True,
                    "file_path": str(path_obj.absolute()),
                    "deleted_type": deleted_type
                }
            )

        except PermissionError as e:
            return self._format_result(
                success=False,
                error=f"Permission denied: {str(e)}"
            )
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Deletion error: {str(e)}"
            )

    def _validate_path(self, file_path: str) -> dict[str, Any]:
        """
        Validate file path for security restrictions.
        Args:
            file_path: File path to validate
        Returns:
            Validation result
        """
        try:
            path_obj = Path(file_path).resolve()
            
            # Check restricted paths
            for restricted in self.restricted_paths:
                if str(path_obj).startswith(restricted):
                    return {
                        "valid": False,
                        "error": f"Access to restricted path denied: {restricted}"
                    }

            return {"valid": True}

        except Exception as e:
            return {
                "valid": False,
                "error": f"Path validation error: {str(e)}"
            }

    def get_schema(self) -> dict[str, Any]:
        """
        Get tool schema.
        """
        return self._schema.dict()
