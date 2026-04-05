"""
Filesystem operation tools for MindFlow backend. Provides comprehensive file and directory operations 
with security controls, validation, and error handling. 
"""

from __future__ import annotations

import base64
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.agents.tools.security.filesystem_validators import (
    TOCTOUValidator,
    PermissionBehavior,
    validate_device_file,
    validate_secrets,
    validate_symlink,
)
from mindflow_backend.agents.tools.workspace_security import (
    WorkspaceSecurityError,
    is_read_only_mode,
    resolve_workspace_path,
)
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.permissions.types import PermissionBehavior
from mindflow_backend.schemas.tools.filesystem_schemas import (
    DELETE_FILE_SCHEMA,
    EDIT_FILE_SCHEMA,
    LIST_DIRECTORY_SCHEMA,
    READ_FILE_SCHEMA,
    WRITE_FILE_SCHEMA,
)

_logger = get_logger(__name__)


def _resolve_tool_path(tool: AsyncToolInterface, raw_path: str) -> Path:
    """Resolve paths relative to the configured workspace when present."""
    path = Path(raw_path)
    if path.is_absolute():
        return path.resolve()
    if tool.root_dir or tool.secure_mode:
        return resolve_workspace_path(raw_path, tool.root_dir)
    if tool.root_dir:
        path = Path(tool.root_dir) / path
    return path.resolve()


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
            # Web / JS ecosystem
            '.txt', '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs',
            '.html', '.htm', '.css', '.scss', '.sass', '.less',
            '.vue', '.svelte',
            # Config / data
            '.json', '.json5', '.xml', '.yml', '.yaml', '.toml',
            '.ini', '.cfg', '.conf', '.env', '.envrc', '.dotenv',
            '.gitignore', '.gitattributes', '.editorconfig',
            # Python
            '.py', '.pyi', '.pyw',
            # Systems languages
            '.c', '.h', '.cpp', '.cc', '.cxx', '.hpp', '.hxx',
            '.rs', '.go', '.java', '.kt', '.kts', '.scala',
            # Scripting / shell
            '.sh', '.bash', '.zsh', '.fish', '.ps1', '.bat', '.cmd',
            # Database / infra
            '.sql', '.graphql', '.gql', '.proto', '.tf', '.hcl',
            # Docs / markup
            '.md', '.mdx', '.rst', '.tex', '.adoc', '.org',
            # Images
            '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp',
            # Misc
            '.csv', '.tsv', '.log', '.lock', '.rb', '.php',
            '.swift', '.dart', '.lua', '.r', '.R',
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
            offset = int(kwargs.get("offset", 0))
            limit = kwargs.get("limit")
            include_line_numbers = bool(kwargs.get("include_line_numbers", False))
            max_lines = kwargs.get("max_lines")
            if limit is None and max_lines is not None:
                limit = int(max_lines)

            path_obj = _resolve_tool_path(self, file_path)
            resolved_path = str(path_obj)

            # Security validation: device file blocking
            device_decision = validate_device_file(resolved_path)
            if device_decision.behavior == PermissionBehavior.DENY:
                return self._format_result(
                    success=False,
                    error=device_decision.message
                )

            # Security validation: symlink validation
            symlink_decision = validate_symlink(resolved_path, self.root_dir)
            if symlink_decision.behavior in [PermissionBehavior.DENY, PermissionBehavior.ASK]:
                return self._format_result(
                    success=False,
                    error=symlink_decision.message
                )

            # Security validation
            validation_result = self._validate_path(resolved_path)
            if not validation_result["valid"]:
                return self._format_result(
                    success=False,
                    error=validation_result["error"]
                )

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

            # Check if file is an image - return base64
            file_ext = path_obj.suffix.lower()
            image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
            if file_ext in image_extensions:
                return await self._read_image(path_obj)

            with open(path_obj, encoding=encoding) as file:
                lines = file.readlines()

            total_lines = len(lines)
            start = max(offset, 0)
            end = total_lines if limit is None else min(total_lines, start + max(int(limit), 0))
            selected_lines = lines[start:end]

            if include_line_numbers:
                selected_lines = [
                    f"{start + i + 1}\t{line}"
                    for i, line in enumerate(selected_lines)
                ]

            content = "".join(selected_lines)
            lines_returned = len(selected_lines)

            return self._format_result(
                success=True,
                result={
                    "content": content,
                    "line_count": total_lines,
                    "total_lines": total_lines,
                    "lines_returned": lines_returned,
                    "lines_read": lines_returned,
                    "file_size": file_size,
                    "encoding": encoding,
                    "file_path": str(path_obj.absolute()),
                    "offset": start,
                    "limit": limit,
                    "has_more": end < total_lines,
                    "truncated": end < total_lines,
                }
            )

        except UnicodeDecodeError as e:
            return self._format_result(
                success=False,
                error=f"Encoding error: {str(e)}"
            )
        except WorkspaceSecurityError as e:
            return self._format_result(
                success=False,
                error=f"Workspace security error: {str(e)}"
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

    async def _read_image(self, path_obj: Path) -> dict[str, Any]:
        """Read image file and return base64 encoded."""
        with open(path_obj, 'rb') as f:
            image_data = f.read()

        base64_data = base64.b64encode(image_data).decode('utf-8')
        file_ext = path_obj.suffix.lstrip('.')

        return self._format_result(
            success=True,
            result={
                "content": base64_data,
                "file_path": str(path_obj.absolute()),
                "file_type": "image",
                "image_format": file_ext,
                "size_bytes": len(image_data),
                "encoding": "base64"
            }
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
                    if restricted == "/dev":
                        return {
                            "valid": False,
                            "error": f"Cannot read from device file: {path_obj}"
                        }
                    return {
                        "valid": False,
                        "error": f"Restricted path denied: {restricted}"
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
        self.toctou_validator = TOCTOUValidator()

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
        dry_run = bool(kwargs.get("dry_run", False))

        try:
            if is_read_only_mode(self.sandbox_mode):
                return self._format_result(
                    success=False,
                    error="Write operation blocked in read-only sandbox mode",
                )

            path_obj = _resolve_tool_path(self, file_path)
        except WorkspaceSecurityError as e:
            return self._format_result(
                success=False,
                error=f"Workspace security error: {str(e)}"
            )

        validation_result = self._validate_path(str(path_obj))
        if not validation_result["valid"]:
            return self._format_result(success=False, error=validation_result["error"])
        if not path_obj.exists() or not path_obj.is_file():
            return self._format_result(success=False, error=f"File not found: {path_obj}")

        content = path_obj.read_text(encoding=encoding)
        if old_string not in content:
            return self._format_result(success=False, error="old_string not found in file")

        # TOCTOU protection: record mtime before edit
        self.toctou_validator.record_mtime(str(path_obj))

        # Security validation: secret detection in new content
        secret_decision = validate_secrets(new_string, str(path_obj))
        if secret_decision.behavior == PermissionBehavior.DENY:
            return self._format_result(
                success=False,
                error=secret_decision.message
            )

        total_occurrences = content.count(old_string)
        if count == -1:
            new_content = content.replace(old_string, new_string)
            replacements = total_occurrences
        else:
            new_content = content.replace(old_string, new_string, count)
            replacements = min(count, total_occurrences)

        size_before = len(content.encode(encoding))
        size_after = len(new_content.encode(encoding))

        if dry_run:
            return self._format_result(
                success=True,
                result={
                    "dry_run": True,
                    "preview": new_content[:500] + "..." if len(new_content) > 500 else new_content,
                    "replacements": replacements,
                    "replacements_made": replacements,
                    "occurrences_replaced": replacements,
                    "total_occurrences": total_occurrences,
                    "file_path": str(path_obj.absolute()),
                },
            )

        # TOCTOU protection: validate mtime before write
        toctou_decision = self.toctou_validator.validate_mtime(str(path_obj))
        if toctou_decision.behavior == PermissionBehavior.DENY:
            return self._format_result(
                success=False,
                error=toctou_decision.message
            )

        path_obj.write_text(new_content, encoding=encoding)

        return self._format_result(
            success=True,
            result={
                "replacements": replacements,
                "replacements_made": replacements,
                "occurrences_replaced": replacements,
                "total_occurrences": total_occurrences,
                "file_path": str(path_obj.absolute()),
                "encoding": encoding,
                "size_before": size_before,
                "size_after": size_after,
                "size_change": size_after - size_before,
            },
        )

    def _validate_path(self, file_path: str) -> dict[str, Any]:
        try:
            path_obj = Path(file_path).resolve()
            for restricted in self.restricted_paths:
                if str(path_obj).startswith(restricted):
                    if restricted == "/dev":
                        return {"valid": False, "error": f"Cannot edit device file: {path_obj}"}
                    return {"valid": False, "error": f"Restricted path denied: {restricted}"}
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
            # Web / JS ecosystem
            '.txt', '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs',
            '.html', '.htm', '.css', '.scss', '.sass', '.less',
            '.vue', '.svelte',
            # Config / data
            '.json', '.json5', '.xml', '.yml', '.yaml', '.toml',
            '.ini', '.cfg', '.conf', '.env', '.envrc', '.dotenv',
            '.gitignore', '.gitattributes', '.editorconfig',
            # Python
            '.py', '.pyi', '.pyw',
            # Systems languages
            '.c', '.h', '.cpp', '.cc', '.cxx', '.hpp', '.hxx',
            '.rs', '.go', '.java', '.kt', '.kts', '.scala',
            # Scripting / shell
            '.sh', '.bash', '.zsh', '.fish', '.ps1', '.bat', '.cmd',
            # Database / infra
            '.sql', '.graphql', '.gql', '.proto', '.tf', '.hcl',
            # Docs / markup
            '.md', '.mdx', '.rst', '.tex', '.adoc', '.org',
            # Misc
            '.csv', '.tsv', '.log', '.lock', '.rb', '.php',
            '.swift', '.dart', '.lua', '.r', '.R',
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
            create_backup: Create backup before write
            atomic_write: Use atomic write (temp file + rename)
        Returns:
            Dictionary with write operation result
        """
        try:
            file_path = kwargs["file_path"]
            content = kwargs["content"]
            encoding = kwargs.get("encoding", "utf-8")
            create_dirs = kwargs.get("create_dirs", True)
            overwrite = kwargs.get("overwrite", True)
            create_backup = kwargs.get("create_backup", False)
            atomic_write = kwargs.get("atomic_write", False)
            generate_git_diff = kwargs.get("generate_git_diff", False)

            if is_read_only_mode(self.sandbox_mode):
                return self._format_result(
                    success=False,
                    error="Write operation blocked in read-only sandbox mode",
                )

            path_obj = _resolve_tool_path(self, file_path)

            # Security validation
            validation_result = self._validate_path(str(path_obj))
            if not validation_result["valid"]:
                return self._format_result(
                    success=False,
                    error=validation_result["error"]
                )

            # Security validation: secret detection
            secret_decision = validate_secrets(content, str(path_obj))
            if secret_decision.behavior == PermissionBehavior.DENY:
                return self._format_result(
                    success=False,
                    error=secret_decision.message
                )

            # Check content size
            content_size = len(content.encode(encoding))
            if content_size > self.max_file_size:
                return self._format_result(
                    success=False,
                    error=f"Content too large: {content_size} bytes (max: {self.max_file_size})"
                )

            file_exists = path_obj.exists()
            if file_exists and not overwrite:
                return self._format_result(
                    success=False,
                    error=f"File already exists and overwrite=False: {path_obj}"
                )

            # Create parent directories if needed
            if create_dirs:
                path_obj.parent.mkdir(parents=True, exist_ok=True)
            elif not path_obj.parent.exists():
                return self._format_result(
                    success=False,
                    error=f"Parent directory does not exist: {path_obj.parent}"
                )

            # Create backup if requested and file exists
            backup_path = None
            if create_backup and file_exists:
                backup_path = await self._create_backup(path_obj)

            # Write file (atomic or direct)
            try:
                if atomic_write:
                    bytes_written = await self._atomic_write(path_obj, content, encoding)
                else:
                    with open(path_obj, 'w', encoding=encoding) as file:
                        bytes_written = file.write(content)

                # Generate git diff if requested
                git_diff = None
                if generate_git_diff and file_exists:
                    git_diff = await self._generate_git_diff(path_obj)

                return self._format_result(
                    success=True,
                    result={
                        "bytes_written": bytes_written,
                        "file_path": str(path_obj.absolute()),
                        "encoding": encoding,
                        "line_count": content.count('\n') + (1 if content else 0),
                        "created": not file_exists,
                        "overwritten": file_exists,
                        "backup_created": backup_path is not None,
                        "backup_path": str(backup_path) if backup_path else None,
                        "atomic": atomic_write,
                        "git_diff": git_diff,
                    }
                )
            except Exception as write_error:
                # Restore from backup if write failed and backup was created
                if backup_path and backup_path.exists():
                    shutil.copy2(backup_path, path_obj)
                    backup_path.unlink()
                raise write_error

        except PermissionError as e:
            return self._format_result(
                success=False,
                error=f"Permission denied: {str(e)}"
            )
        except WorkspaceSecurityError as e:
            return self._format_result(
                success=False,
                error=f"Workspace security error: {str(e)}"
            )
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"File write error: {str(e)}"
            )

    async def _create_backup(self, path_obj: Path) -> Path:
        """Create backup of file before write."""
        backup_path = Path(f"{path_obj}.backup")
        shutil.copy2(path_obj, backup_path)
        return backup_path

    async def _atomic_write(self, path_obj: Path, content: str, encoding: str) -> int:
        """Write file atomically using temp file + rename."""
        dir_path = path_obj.parent

        # Create temp file in same directory (ensures same filesystem)
        with tempfile.NamedTemporaryFile(
            mode='w',
            encoding=encoding,
            dir=str(dir_path),
            delete=False
        ) as tmp_file:
            tmp_file.write(content)
            tmp_path = Path(tmp_file.name)

        # Atomic rename
        bytes_written = len(content.encode(encoding))
        Path(tmp_path).replace(path_obj)

        return bytes_written

    async def _generate_git_diff(self, path_obj: Path) -> str | None:
        """Generate git diff for the file.

        Note: Requires git to be installed and file to be in a git repo.
        """
        try:
            result = subprocess.run(
                ['git', 'diff', str(path_obj)],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout
            return None
        except Exception:
            return None

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
                    if restricted == "/dev":
                        return {
                            "valid": False,
                            "error": f"Cannot write to device file: {path_obj}"
                        }
                    return {
                        "valid": False,
                        "error": f"Restricted path denied: {restricted}"
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
            show_hidden = kwargs.get("include_hidden", kwargs.get("show_hidden", False))
            include_size = kwargs.get("include_size", True)
            include_type = kwargs.get("include_type", True)
            recursive = kwargs.get("recursive", False)
            pattern = kwargs.get("pattern")
            max_items = int(kwargs.get("max_items", 10000))

            path_obj = _resolve_tool_path(self, directory_path)

            # Security validation
            validation_result = self._validate_path(str(path_obj))
            if not validation_result["valid"]:
                return self._format_result(
                    success=False,
                    error=validation_result["error"]
                )

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
            entries = []

            if recursive:
                items = path_obj.rglob("*") if not pattern else path_obj.rglob(pattern)
            else:
                items = path_obj.iterdir()

            for item in items:
                # Skip hidden files if not requested
                if not show_hidden and item.name.startswith('.'):
                    continue

                if len(entries) >= max_items:
                    break

                modified = datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                entry = {
                    "name": item.name,
                    "path": str(item),
                    "modified": modified,
                }

                if include_type:
                    if item.is_file():
                        entry["type"] = "file"
                    elif item.is_dir():
                        entry["type"] = "directory"
                    elif item.is_symlink():
                        entry["type"] = "symlink"
                    else:
                        entry["type"] = "other"

                if include_size:
                    try:
                        entry["size"] = item.stat().st_size if item.is_file() else 0
                    except (OSError, PermissionError):
                        entry["size"] = None

                if item.is_file():
                    files.append(dict(entry))
                elif item.is_dir():
                    directories.append(dict(entry))

                entries.append(entry)

            return self._format_result(
                success=True,
                result={
                    "entries": entries,
                    "files": files,
                    "directories": directories,
                    "total_count": len(entries),
                    "directory_path": str(path_obj.absolute()),
                    "truncated": len(entries) >= max_items,
                }
            )

        except PermissionError as e:
            return self._format_result(
                success=False,
                error=f"Permission denied: {str(e)}"
            )
        except WorkspaceSecurityError as e:
            return self._format_result(
                success=False,
                error=f"Workspace security error: {str(e)}"
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
                        "error": f"Restricted path denied: {restricted}"
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
            if is_read_only_mode(self.sandbox_mode):
                return self._format_result(
                    success=False,
                    error="Delete operation blocked in read-only sandbox mode",
                )

            path_obj = _resolve_tool_path(self, file_path)

            # Security validation
            validation_result = self._validate_path(str(path_obj))
            if not validation_result["valid"]:
                return self._format_result(
                    success=False,
                    error=validation_result["error"]
                )

            # Check if path exists
            if not path_obj.exists():
                return self._format_result(
                    success=False,
                    error=f"Path not found: {file_path}"
                )

            # Delete file or directory
            file_name = path_obj.name
            file_size = path_obj.stat().st_size if path_obj.is_file() else None
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
                    "deleted_type": deleted_type,
                    "file_name": file_name,
                    "file_size": file_size,
                }
            )

        except PermissionError as e:
            return self._format_result(
                success=False,
                error=f"Permission denied: {str(e)}"
            )
        except WorkspaceSecurityError as e:
            return self._format_result(
                success=False,
                error=f"Workspace security error: {str(e)}"
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
