"""File operations tools v2 - Enhanced with Claude Code standards.

This module implements FileReadTool, FileWriteTool, and FileEditTool v2
with full integration of:
- Schemas v2 (filesystem_schemas_v2.py)
- Security validators (filesystem_validators.py)
- Metadata tracking (tool_metadata.py)
- Permission system (permission_matcher.py)

Matching Claude Code's feature set and security standards.
"""

from __future__ import annotations

import base64
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools.filesystem_schemas_v2 import (
    FileEditInput,
    FileReadInput,
    FileWriteInput,
)
from mindflow_backend.schemas.tools.tool_metadata import (
    FileModificationMetadata,
)
from mindflow_backend.permissions.types import (
    PermissionBehavior,
    PermissionContext,
)
from mindflow_backend.agents.tools.security.filesystem_validators import (
    validate_filesystem_operation,
    validate_device_file,
    validate_symlink,
    validate_file_mtime,
    validate_secrets,
    record_file_mtime,
    clear_file_mtime,
    TOCTOUValidator,
)

_logger = get_logger(__name__)


def _resolve_input_path(root_dir: str | None, raw_path: str) -> str:
    """Resolve paths relative to root_dir while preserving absolute inputs."""
    path = Path(raw_path)
    if path.is_absolute():
        return str(path.resolve())
    if root_dir:
        return str((Path(root_dir) / path).resolve())
    return str(path.resolve())


# ============================================================================
# FileReadTool v2
# ============================================================================

class FileReadToolV2(AsyncToolInterface):
    """Enhanced file reading tool matching Claude Code standards.

    Features:
    - Device file blocking (/dev/zero, /dev/random)
    - Symlink validation (no escape from workspace)
    - Pagination (offset/limit)
    - Image support (base64 encoding)
    - PDF support (page ranges)
    - Line numbers
    - Security validators integration
    """

    name = "read_file_v2"
    description = (
        "Read file contents with advanced features: pagination, images, PDFs, "
        "line numbers, symlink validation, and device file blocking."
    )

    def __init__(self, root_dir: str | None = None):
        """Initialize FileReadTool v2.

        Args:
            root_dir: Root directory for sandboxing (workspace root)
        """
        self.root_dir = root_dir

    async def execute(self, **kwargs) -> dict[str, Any]:
        """Execute file read with full validation and security checks."""
        # Parse and validate input
        try:
            input_data = FileReadInput(**kwargs)
        except Exception as e:
            return {
                "success": False,
                "error": f"Invalid input: {e}",
                "error_code": "INVALID_INPUT"
            }

        file_path = input_data.file_path

        # Resolve path relative to root_dir if provided
        file_path = _resolve_input_path(self.root_dir, file_path)

        # Security validation: device file blocking
        device_decision = validate_device_file(file_path)
        if device_decision.behavior == PermissionBehavior.DENY:
            return {
                "success": False,
                "error": device_decision.message,
                "error_code": "DEVICE_FILE_BLOCKED"
            }

        # Security validation: symlink validation
        symlink_decision = validate_symlink(file_path, self.root_dir)
        if symlink_decision.behavior in [PermissionBehavior.DENY, PermissionBehavior.ASK]:
            return {
                "success": False,
                "error": symlink_decision.message,
                "error_code": "SYMLINK_VIOLATION"
            }

        # Master filesystem validator
        fs_decision = validate_filesystem_operation(
            file_path=file_path,
            operation="read",
            workspace_root=self.root_dir,
            check_secrets=False  # Don't check secrets on read
        )

        if fs_decision.behavior == PermissionBehavior.DENY:
            return {
                "success": False,
                "error": fs_decision.message,
                "error_code": "PERMISSION_DENIED"
            }

        # Check file exists
        if not os.path.exists(file_path):
            return {
                "success": False,
                "error": f"File not found: {file_path}",
                "error_code": "FILE_NOT_FOUND"
            }

        # Check if it's a file (not directory)
        if not os.path.isfile(file_path):
            return {
                "success": False,
                "error": f"Not a file: {file_path}",
                "error_code": "NOT_A_FILE"
            }

        try:
            # Handle different file types
            file_ext = os.path.splitext(file_path)[1].lower()

            # Image files - return base64
            if file_ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']:
                return await self._read_image(file_path)

            # PDF files - extract text from pages
            if file_ext == '.pdf':
                return await self._read_pdf(file_path, input_data.pages)

            # Regular text files
            return await self._read_text_file(
                file_path,
                offset=input_data.offset,
                limit=input_data.limit,
                include_line_numbers=input_data.include_line_numbers,
                encoding=input_data.encoding
            )

        except Exception as e:
            _logger.error(f"Error reading file {file_path}: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to read file: {e}",
                "error_code": "READ_ERROR"
            }

    async def _read_text_file(
        self,
        file_path: str,
        offset: int | None,
        limit: int | None,
        include_line_numbers: bool,
        encoding: str
    ) -> dict[str, Any]:
        """Read text file with pagination and line numbers."""
        with open(file_path, 'r', encoding=encoding) as f:
            lines = f.readlines()

        total_lines = len(lines)
        offset = offset or 0

        # Apply offset
        if offset > 0:
            lines = lines[offset:]

        # Apply limit
        if limit is not None:
            lines = lines[:limit]

        # Add line numbers if requested
        if include_line_numbers:
            start_line = offset + 1
            lines = [f"{start_line + i}\t{line}" for i, line in enumerate(lines)]

        content = "".join(lines)

        return {
            "success": True,
            "content": content,
            "file_path": file_path,
            "total_lines": total_lines,
            "lines_returned": len(lines),
            "offset": offset,
            "encoding": encoding,
            "truncated": limit is not None and (offset + len(lines)) < total_lines
        }

    async def _read_image(self, file_path: str) -> dict[str, Any]:
        """Read image file and return base64 encoded."""
        with open(file_path, 'rb') as f:
            image_data = f.read()

        base64_data = base64.b64encode(image_data).decode('utf-8')
        file_ext = os.path.splitext(file_path)[1].lstrip('.')

        return {
            "success": True,
            "content": base64_data,
            "file_path": file_path,
            "file_type": "image",
            "image_format": file_ext,
            "size_bytes": len(image_data),
            "encoding": "base64"
        }

    async def _read_pdf(self, file_path: str, pages: str | None) -> dict[str, Any]:
        """Read PDF file and extract text from specified pages.

        Args:
            file_path: Path to PDF file
            pages: Page range (e.g., "1-5", "3", "1,3,5-7")

        Returns:
            Dictionary with extracted text and metadata
        """
        try:
            import PyPDF2
        except ImportError:
            return {
                "success": False,
                "error": "PyPDF2 not installed. Install with: pip install PyPDF2",
                "error_code": "MISSING_DEPENDENCY",
                "file_path": file_path
            }

        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                total_pages = len(reader.pages)

                # Parse page range
                if pages:
                    page_list = self._parse_page_range(pages, total_pages)
                else:
                    page_list = list(range(total_pages))

                # Limit to 20 pages max
                if len(page_list) > 20:
                    return {
                        "success": False,
                        "error": f"Too many pages requested ({len(page_list)}). Maximum is 20 pages per request.",
                        "error_code": "TOO_MANY_PAGES",
                        "file_path": file_path,
                        "total_pages": total_pages,
                    }

                # Extract text from pages
                text_parts = []
                for page_num in page_list:
                    if 0 <= page_num < total_pages:
                        page = reader.pages[page_num]
                        text = page.extract_text()
                        text_parts.append(f"--- Page {page_num + 1} ---\n{text}")

                full_text = "\n\n".join(text_parts)

                return {
                    "success": True,
                    "content": full_text,
                    "pages_read": len(page_list),
                    "total_pages": total_pages,
                    "file_path": file_path,
                }

        except FileNotFoundError:
            return {
                "success": False,
                "error": f"PDF file not found: {file_path}",
                "error_code": "FILE_NOT_FOUND",
                "file_path": file_path,
            }
        except Exception as exc:
            return {
                "success": False,
                "error": f"Error reading PDF: {exc}",
                "error_code": "READ_ERROR",
                "file_path": file_path,
            }

    @staticmethod
    def _parse_page_range(pages: str, total_pages: int) -> list[int]:
        """Parse page range string into list of page numbers (0-indexed).

        Examples:
            "1" -> [0]
            "1-3" -> [0, 1, 2]
            "1,3,5" -> [0, 2, 4]
            "1-3,5,7-9" -> [0, 1, 2, 4, 6, 7, 8]

        Args:
            pages: Page range string
            total_pages: Total number of pages in PDF

        Returns:
            List of 0-indexed page numbers
        """
        page_nums = []

        for part in pages.split(','):
            part = part.strip()

            if '-' in part:
                # Range: "1-5"
                start_str, end_str = part.split('-', 1)
                start = int(start_str.strip()) - 1  # Convert to 0-indexed
                end = int(end_str.strip()) - 1
                page_nums.extend(range(start, end + 1))
            else:
                # Single page: "3"
                page_num = int(part) - 1  # Convert to 0-indexed
                page_nums.append(page_num)

        # Remove duplicates and sort
        page_nums = sorted(set(page_nums))

        # Filter out invalid page numbers
        page_nums = [p for p in page_nums if 0 <= p < total_pages]

        return page_nums

    def get_schema(self) -> dict[str, Any]:
        """Return tool schema for LangChain adapter."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to file to read"
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Line number to start reading from (0-indexed)",
                        "default": 0
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of lines to read (null = all)",
                        "default": None
                    },
                    "include_line_numbers": {
                        "type": "boolean",
                        "description": "Prefix each line with line number",
                        "default": True
                    },
                    "encoding": {
                        "type": "string",
                        "description": "File encoding",
                        "default": "utf-8"
                    },
                    "pages": {
                        "type": "string",
                        "description": "Page range for PDFs (e.g., '1-5', '3', '10-20')",
                        "default": None
                    }
                },
                "required": ["file_path"]
            }
        }


# ============================================================================
# FileWriteTool v2
# ============================================================================

class FileWriteToolV2(AsyncToolInterface):
    """Enhanced file writing tool matching Claude Code standards.

    Features:
    - Atomic write (write to temp, then rename)
    - Backup support (preserve original)
    - Secret detection (block writes with API keys)
    - Git diff generation
    - Permission preservation
    - Security validators integration
    """

    name = "write_file_v2"
    description = (
        "Write file contents with advanced features: atomic write, backup, "
        "secret detection, git diff generation, and permission preservation."
    )

    def __init__(self, root_dir: str | None = None):
        """Initialize FileWriteTool v2.

        Args:
            root_dir: Root directory for sandboxing (workspace root)
        """
        self.root_dir = root_dir

    async def execute(self, **kwargs) -> dict[str, Any]:
        """Execute file write with full validation and security checks."""
        # Parse and validate input
        try:
            input_data = FileWriteInput(**kwargs)
        except Exception as e:
            return {
                "success": False,
                "error": f"Invalid input: {e}",
                "error_code": "INVALID_INPUT"
            }

        file_path = input_data.file_path
        content = input_data.content
        check_secrets = kwargs.get("check_secrets", True)
        generate_git_diff = kwargs.get("generate_git_diff", False)

        # Resolve path relative to root_dir if provided
        file_path = _resolve_input_path(self.root_dir, file_path)

        # Security validation: secret detection
        if check_secrets:
            secret_decision = validate_secrets(content, file_path)
            if secret_decision.behavior == PermissionBehavior.DENY:
                return {
                    "success": False,
                    "error": secret_decision.message,
                    "error_code": "SECRETS_DETECTED"
                }

        # Master filesystem validator
        fs_decision = validate_filesystem_operation(
            file_path=file_path,
            operation="write",
            content=content,
            workspace_root=self.root_dir,
            check_secrets=check_secrets
        )

        if fs_decision.behavior == PermissionBehavior.DENY:
            return {
                "success": False,
                "error": fs_decision.message,
                "error_code": "PERMISSION_DENIED"
            }

        # Collect metadata before write
        metadata = FileModificationMetadata(file_path=file_path)
        file_existed = os.path.exists(file_path)

        if file_existed:
            metadata.modification_time_before = os.path.getmtime(file_path)
            metadata.file_size_before = os.path.getsize(file_path)

            # Preserve permissions if requested
            if input_data.preserve_permissions:
                original_mode = os.stat(file_path).st_mode

        # Create backup if requested
        backup_path = None
        if input_data.backup and file_existed:
            backup_path = f"{file_path}.backup"
            shutil.copy2(file_path, backup_path)

        try:
            # Atomic write if requested
            if input_data.atomic:
                await self._atomic_write(file_path, content, input_data.encoding)
            else:
                # Direct write
                with open(file_path, 'w', encoding=input_data.encoding) as f:
                    f.write(content)

            # Restore permissions if requested
            if input_data.preserve_permissions and file_existed:
                os.chmod(file_path, original_mode)

            # Collect metadata after write
            metadata.modification_time_after = os.path.getmtime(file_path)
            metadata.file_size_after = os.path.getsize(file_path)

            # Generate git diff if requested
            git_diff = None
            if generate_git_diff and file_existed:
                git_diff = await self._generate_git_diff(file_path)

            return {
                "success": True,
                "file_path": file_path,
                "bytes_written": len(content.encode(input_data.encoding)),
                "lines_written": content.count('\n') + 1,
                "file_existed": file_existed,
                "backup_created": backup_path is not None,
                "backup_path": backup_path,
                "atomic": input_data.atomic,
                "git_diff": git_diff,
                "metadata": metadata.model_dump()
            }

        except Exception as e:
            _logger.error(f"Error writing file {file_path}: {e}", exc_info=True)

            # Restore from backup if write failed
            if backup_path and os.path.exists(backup_path):
                shutil.copy2(backup_path, file_path)
                os.remove(backup_path)

            return {
                "success": False,
                "error": f"Failed to write file: {e}",
                "error_code": "WRITE_ERROR"
            }

    async def _atomic_write(self, file_path: str, content: str, encoding: str):
        """Write file atomically using temp file + rename."""
        dir_path = os.path.dirname(file_path)

        # Create temp file in same directory (ensures same filesystem)
        with tempfile.NamedTemporaryFile(
            mode='w',
            encoding=encoding,
            dir=dir_path,
            delete=False
        ) as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name

        # Atomic rename
        os.replace(tmp_path, file_path)

    async def _generate_git_diff(self, file_path: str) -> str | None:
        """Generate git diff for the file.

        Note: Requires git to be installed and file to be in a git repo.
        """
        try:
            import subprocess
            result = subprocess.run(
                ['git', 'diff', file_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout
            return None
        except Exception:
            return None

    def get_schema(self) -> dict[str, Any]:
        """Return tool schema for LangChain adapter."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to file to write"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to file"
                    },
                    "encoding": {
                        "type": "string",
                        "description": "File encoding",
                        "default": "utf-8"
                    },
                    "atomic": {
                        "type": "boolean",
                        "description": "Use atomic write (temp + rename)",
                        "default": True
                    },
                    "backup": {
                        "type": "boolean",
                        "description": "Create backup of existing file",
                        "default": False
                    },
                    "preserve_permissions": {
                        "type": "boolean",
                        "description": "Preserve file permissions",
                        "default": True
                    },
                    "check_secrets": {
                        "type": "boolean",
                        "description": "Check for secrets in content",
                        "default": True
                    },
                    "generate_git_diff": {
                        "type": "boolean",
                        "description": "Generate git diff after write",
                        "default": False
                    }
                },
                "required": ["file_path", "content"]
            }
        }


# ============================================================================
# FileEditTool v2
# ============================================================================

class FileEditToolV2(AsyncToolInterface):
    """Enhanced file editing tool matching Claude Code standards.

    Features:
    - Fuzzy matching (find similar strings)
    - TOCTOU protection (detect concurrent modifications)
    - Quote preservation (maintain quote style)
    - Dry run mode (preview changes)
    - Git diff generation
    - Replace all mode
    - Security validators integration
    """

    name = "edit_file_v2"
    description = (
        "Edit file contents with advanced features: fuzzy matching, TOCTOU protection, "
        "quote preservation, dry run, git diff generation, and replace all mode."
    )

    def __init__(self, root_dir: str | None = None):
        """Initialize FileEditTool v2.

        Args:
            root_dir: Root directory for sandboxing (workspace root)
        """
        self.root_dir = root_dir
        self.toctou_validator = TOCTOUValidator()

    async def execute(self, **kwargs) -> dict[str, Any]:
        """Execute file edit with full validation and security checks."""
        # Parse and validate input
        try:
            input_data = FileEditInput(**kwargs)
        except Exception as e:
            return {
                "success": False,
                "error": f"Invalid input: {e}",
                "error_code": "INVALID_INPUT"
            }

        file_path = input_data.file_path
        old_string = input_data.old_string
        new_string = input_data.new_string
        explicit_replace_all = "replace_all" in kwargs
        encoding = kwargs.get("encoding", "utf-8")
        fuzzy_threshold = kwargs.get("fuzzy_threshold", 0.85)
        check_secrets = kwargs.get("check_secrets", True)
        generate_git_diff = kwargs.get("generate_git_diff", False)

        # Resolve path relative to root_dir if provided
        file_path = _resolve_input_path(self.root_dir, file_path)

        # Check file exists
        if not os.path.exists(file_path):
            return {
                "success": False,
                "error": f"File not found: {file_path}",
                "error_code": "FILE_NOT_FOUND"
            }

        # TOCTOU protection: record mtime before read
        record_file_mtime(file_path)

        try:
            # Read file content
            with open(file_path, 'r', encoding=encoding) as f:
                original_content = f.read()

            # TOCTOU protection: validate mtime hasn't changed
            toctou_decision = validate_file_mtime(file_path)
            if toctou_decision.behavior == PermissionBehavior.DENY:
                clear_file_mtime(file_path)
                return {
                    "success": False,
                    "error": toctou_decision.message,
                    "error_code": "TOCTOU_VIOLATION"
                }

            # Find matches
            use_fuzzy_match = bool(kwargs.get("fuzzy_match", False))
            if use_fuzzy_match:
                matches = self._fuzzy_find(original_content, old_string, fuzzy_threshold)
            else:
                matches = self._exact_find(original_content, old_string)

            if not matches:
                clear_file_mtime(file_path)
                return {
                    "success": False,
                    "error": f"String not found: {old_string[:50]}...",
                    "error_code": "STRING_NOT_FOUND"
                }

            # Check for multiple matches if not replace_all
            if len(matches) > 1 and explicit_replace_all and not input_data.replace_all:
                clear_file_mtime(file_path)
                return {
                    "success": False,
                    "error": f"Multiple matches found ({len(matches)}). Use replace_all=true or provide more context.",
                    "error_code": "MULTIPLE_MATCHES",
                    "match_count": len(matches)
                }

            # Perform replacement
            if input_data.replace_all:
                new_content = original_content.replace(old_string, new_string)
                replacements = len(matches)
            else:
                # Replace first match
                match_start = matches[0]
                new_content = (
                    original_content[:match_start] +
                    new_string +
                    original_content[match_start + len(old_string):]
                )
                replacements = 1

            # Dry run mode - don't write, just preview
            if input_data.dry_run:
                clear_file_mtime(file_path)
                return {
                    "success": True,
                    "dry_run": True,
                    "file_path": file_path,
                    "replacements": replacements,
                    "preview": new_content[:500] + "..." if len(new_content) > 500 else new_content
                }

            # Secret detection on new content
            if check_secrets:
                secret_decision = validate_secrets(new_content, file_path)
                if secret_decision.behavior == PermissionBehavior.DENY:
                    clear_file_mtime(file_path)
                    return {
                        "success": False,
                        "error": secret_decision.message,
                        "error_code": "SECRETS_DETECTED"
                    }

            # Write new content
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(new_content)

            # Clear TOCTOU tracking
            clear_file_mtime(file_path)

            # Generate git diff if requested
            git_diff = None
            if generate_git_diff:
                git_diff = await self._generate_git_diff(file_path)

            return {
                "success": True,
                "file_path": file_path,
                "replacements": replacements,
                "old_length": len(original_content),
                "new_length": len(new_content),
                "diff_lines": new_content.count('\n') - original_content.count('\n'),
                "git_diff": git_diff
            }

        except Exception as e:
            _logger.error(f"Error editing file {file_path}: {e}", exc_info=True)
            clear_file_mtime(file_path)
            return {
                "success": False,
                "error": f"Failed to edit file: {e}",
                "error_code": "EDIT_ERROR"
            }

    def _exact_find(self, content: str, search: str) -> list[int]:
        """Find all exact matches and return their start positions."""
        matches = []
        start = 0
        while True:
            pos = content.find(search, start)
            if pos == -1:
                break
            matches.append(pos)
            start = pos + 1
        return matches

    def _fuzzy_find(self, content: str, search: str, threshold: float) -> list[int]:
        """Find fuzzy matches using sequence similarity (difflib).

        Uses difflib.SequenceMatcher for similarity matching.
        For production with large files, consider rapidfuzz for better performance.
        """
        import difflib
        
        # Try exact match first
        exact_matches = self._exact_find(content, search)
        if exact_matches:
            return exact_matches
        
        # Use sliding window approach with difflib
        matches = []
        search_len = len(search)
        content_len = len(content)
        
        # Slide a window of search text size through content
        step = max(1, search_len // 4)  # Step by quarter of search length
        
        for i in range(0, content_len - search_len + 1, step):
            window = content[i:i + search_len]
            similarity = difflib.SequenceMatcher(None, search, window).ratio()
            
            if similarity >= threshold:
                # Refine: check exact position with smaller step
                for j in range(max(0, i - step), min(content_len - search_len + 1, i + step)):
                    refined_window = content[j:j + search_len]
                    refined_similarity = difflib.SequenceMatcher(None, search, refined_window).ratio()
                    
                    if refined_similarity >= threshold and j not in matches:
                        matches.append(j)
        
        return sorted(matches)

    async def _generate_git_diff(self, file_path: str) -> str | None:
        """Generate git diff for the file."""
        try:
            import subprocess
            result = subprocess.run(
                ['git', 'diff', file_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout
            return None
        except Exception:
            return None

    def get_schema(self) -> dict[str, Any]:
        """Return tool schema for LangChain adapter."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to file to edit"
                    },
                    "old_string": {
                        "type": "string",
                        "description": "String to find and replace"
                    },
                    "new_string": {
                        "type": "string",
                        "description": "Replacement string"
                    },
                    "encoding": {
                        "type": "string",
                        "description": "File encoding",
                        "default": "utf-8"
                    },
                    "replace_all": {
                        "type": "boolean",
                        "description": "Replace all occurrences",
                        "default": False
                    },
                    "fuzzy_match": {
                        "type": "boolean",
                        "description": "Use fuzzy matching",
                        "default": False
                    },
                    "fuzzy_threshold": {
                        "type": "number",
                        "description": "Fuzzy match threshold (0.0-1.0)",
                        "default": 0.8
                    },
                    "preserve_quotes": {
                        "type": "boolean",
                        "description": "Preserve quote style",
                        "default": True
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "Preview changes without writing",
                        "default": False
                    },
                    "check_secrets": {
                        "type": "boolean",
                        "description": "Check for secrets in new content",
                        "default": True
                    },
                    "generate_git_diff": {
                        "type": "boolean",
                        "description": "Generate git diff after edit",
                        "default": False
                    }
                },
                "required": ["file_path", "old_string", "new_string"]
            }
        }
