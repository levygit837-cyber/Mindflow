"""Enhanced filesystem tool schemas for MindFlow backend (v2).

Provides comprehensive schemas matching Claude Code standards with all
missing fields, validation rules, and metadata support.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from mindflow_backend.schemas.tools.tool_config import ToolParameter, ToolSchema
from mindflow_backend.schemas.tools.tool_metadata import StructuredPatch


# ============================================================================
# FileReadTool Schema (Enhanced)
# ============================================================================

class FileReadInput(BaseModel):
    """Input schema for FileReadTool."""

    file_path: str = Field(..., description="Absolute path to file to read")
    offset: int | None = Field(None, description="Line number to start reading from (0-indexed)", ge=0)
    limit: int | None = Field(None, description="Maximum number of lines to read", ge=1)
    pages: str | None = Field(None, description="Page range for PDF files (e.g., '1-5', '3', '10-20')")
    encoding: str = Field(default="utf-8", description="File encoding")
    include_line_numbers: bool = Field(default=False, description="Include line numbers in output")
    follow_symlinks: bool = Field(default=True, description="Follow symbolic links")

    @field_validator("file_path")
    @classmethod
    def validate_absolute_path(cls, v: str) -> str:
        """Validate that path is absolute."""
        from pathlib import Path
        path = Path(v).expanduser()
        if not path.is_absolute():
            raise ValueError(f"Path must be absolute: {v}")
        return str(path)

    @field_validator("pages")
    @classmethod
    def validate_pages(cls, v: str | None) -> str | None:
        """Validate PDF page range format."""
        if v is None:
            return v
        # Format: "1-5" or "3" or "10-20"
        import re
        if not re.match(r"^\d+(-\d+)?$", v):
            raise ValueError(f"Invalid page range format: {v}. Use '1-5' or '3'")
        return v


class FileReadOutput(BaseModel):
    """Output schema for FileReadTool."""

    content: str = Field(..., description="File content")
    metadata: dict[str, Any] = Field(default_factory=dict, description="File metadata")
    line_count: int | None = Field(None, description="Number of lines read")
    file_size: int | None = Field(None, description="File size in bytes")
    encoding: str | None = Field(None, description="Detected encoding")
    is_truncated: bool = Field(default=False, description="Whether output was truncated")
    # For images
    image_data: str | None = Field(None, description="Base64 encoded image data")
    image_dimensions: dict[str, int] | None = Field(None, description="Image dimensions (width, height)")
    # For PDFs
    pdf_pages: list[str] | None = Field(None, description="Extracted PDF pages")
    pdf_page_count: int | None = Field(None, description="Total PDF page count")


READ_FILE_SCHEMA_V2 = ToolSchema(
    name="read_file",
    description="Read file contents with advanced features (images, PDFs, notebooks, pagination)",
    category="filesystem",
    parameters=[
        ToolParameter(
            name="file_path",
            type="string",
            description="Absolute path to file to read",
            required=True,
            format="file-path"
        ),
        ToolParameter(
            name="offset",
            type="integer",
            description="Line number to start reading from (0-indexed)",
            required=False,
            constraints={"minimum": 0}
        ),
        ToolParameter(
            name="limit",
            type="integer",
            description="Maximum number of lines to read",
            required=False,
            constraints={"minimum": 1, "maximum": 10000}
        ),
        ToolParameter(
            name="pages",
            type="string",
            description="Page range for PDF files (e.g., '1-5', '3')",
            required=False,
            format="page-range"
        ),
        ToolParameter(
            name="encoding",
            type="string",
            description="File encoding",
            required=False,
            default="utf-8",
            enum=["utf-8", "utf-16", "latin-1", "ascii"]
        ),
        ToolParameter(
            name="include_line_numbers",
            type="boolean",
            description="Include line numbers in output",
            required=False,
            default=False
        ),
        ToolParameter(
            name="follow_symlinks",
            type="boolean",
            description="Follow symbolic links",
            required=False,
            default=True
        ),
    ],
    returns={
        "type": "object",
        "description": "File read result with content and metadata",
        "properties": {
            "content": {"type": "string"},
            "metadata": {"type": "object"},
            "line_count": {"type": "integer"},
            "file_size": {"type": "integer"},
            "encoding": {"type": "string"},
            "is_truncated": {"type": "boolean"},
        }
    },
    version="2.0.0"
)


# ============================================================================
# FileWriteTool Schema (Enhanced)
# ============================================================================

class FileWriteInput(BaseModel):
    """Input schema for FileWriteTool."""

    file_path: str = Field(..., description="Absolute path to file to write")
    content: str = Field(..., description="Content to write to file")
    encoding: str = Field(default="utf-8", description="File encoding")
    create_dirs: bool = Field(default=True, description="Create parent directories if needed")
    backup: bool = Field(default=False, description="Create backup of existing file")
    overwrite: bool = Field(default=True, description="Overwrite existing file")
    atomic: bool = Field(default=True, description="Use atomic write (temp file + rename)")
    preserve_permissions: bool = Field(default=True, description="Preserve file permissions")

    @field_validator("file_path")
    @classmethod
    def validate_absolute_path(cls, v: str) -> str:
        """Validate that path is absolute."""
        from pathlib import Path
        path = Path(v).expanduser()
        if not path.is_absolute():
            raise ValueError(f"Path must be absolute: {v}")
        return str(path)


class FileWriteOutput(BaseModel):
    """Output schema for FileWriteTool."""

    operation: str = Field(..., description="Operation type (create/update)")
    file_path: str = Field(..., description="Path to written file")
    bytes_written: int = Field(..., description="Number of bytes written")
    backup_path: str | None = Field(None, description="Path to backup file if created")
    structured_patch: StructuredPatch | None = Field(None, description="Structured diff patch")
    git_diff: str | None = Field(None, description="Git diff output")


WRITE_FILE_SCHEMA_V2 = ToolSchema(
    name="write_file",
    description="Write content to files with safety features (backup, atomic write, git diff)",
    category="filesystem",
    parameters=[
        ToolParameter(
            name="file_path",
            type="string",
            description="Absolute path to file to write",
            required=True,
            format="file-path"
        ),
        ToolParameter(
            name="content",
            type="string",
            description="Content to write to file",
            required=True
        ),
        ToolParameter(
            name="encoding",
            type="string",
            description="File encoding",
            required=False,
            default="utf-8"
        ),
        ToolParameter(
            name="create_dirs",
            type="boolean",
            description="Create parent directories if needed",
            required=False,
            default=True
        ),
        ToolParameter(
            name="backup",
            type="boolean",
            description="Create backup of existing file",
            required=False,
            default=False
        ),
        ToolParameter(
            name="overwrite",
            type="boolean",
            description="Overwrite existing file",
            required=False,
            default=True
        ),
        ToolParameter(
            name="atomic",
            type="boolean",
            description="Use atomic write (temp file + rename)",
            required=False,
            default=True
        ),
        ToolParameter(
            name="preserve_permissions",
            type="boolean",
            description="Preserve file permissions",
            required=False,
            default=True
        ),
    ],
    returns={
        "type": "object",
        "description": "File write result with metadata",
        "properties": {
            "operation": {"type": "string", "enum": ["create", "update"]},
            "file_path": {"type": "string"},
            "bytes_written": {"type": "integer"},
            "backup_path": {"type": "string"},
        }
    },
    version="2.0.0"
)


# ============================================================================
# FileEditTool Schema (Enhanced)
# ============================================================================

class FileEditInput(BaseModel):
    """Input schema for FileEditTool."""

    file_path: str = Field(..., description="Absolute path to file to edit")
    old_string: str = Field(..., description="String to replace")
    new_string: str = Field(..., description="Replacement string")
    replace_all: bool = Field(default=False, description="Replace all occurrences")
    preserve_quotes: bool = Field(default=True, description="Preserve quote style (single/double)")
    dry_run: bool = Field(default=False, description="Preview changes without applying")
    fuzzy_match: bool = Field(default=True, description="Enable fuzzy matching")

    @field_validator("file_path")
    @classmethod
    def validate_absolute_path(cls, v: str) -> str:
        """Validate that path is absolute."""
        from pathlib import Path
        path = Path(v).expanduser()
        if not path.is_absolute():
            raise ValueError(f"Path must be absolute: {v}")
        return str(path)

    @field_validator("old_string", "new_string")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Validate strings are not empty."""
        if not v:
            raise ValueError("String cannot be empty")
        return v


class FileEditOutput(BaseModel):
    """Output schema for FileEditTool."""

    file_path: str = Field(..., description="Path to edited file")
    lines_changed: int = Field(..., description="Number of lines changed")
    occurrences_replaced: int = Field(..., description="Number of occurrences replaced")
    structured_patch: StructuredPatch | None = Field(None, description="Structured diff patch")
    git_diff: str | None = Field(None, description="Git diff output")
    preview: str | None = Field(None, description="Preview of changes (dry_run mode)")


EDIT_FILE_SCHEMA_V2 = ToolSchema(
    name="edit_file",
    description="Edit files with fuzzy matching, quote preservation, and TOCTOU protection",
    category="filesystem",
    parameters=[
        ToolParameter(
            name="file_path",
            type="string",
            description="Absolute path to file to edit",
            required=True,
            format="file-path"
        ),
        ToolParameter(
            name="old_string",
            type="string",
            description="String to replace",
            required=True
        ),
        ToolParameter(
            name="new_string",
            type="string",
            description="Replacement string",
            required=True
        ),
        ToolParameter(
            name="replace_all",
            type="boolean",
            description="Replace all occurrences",
            required=False,
            default=False
        ),
        ToolParameter(
            name="preserve_quotes",
            type="boolean",
            description="Preserve quote style (single/double)",
            required=False,
            default=True
        ),
        ToolParameter(
            name="dry_run",
            type="boolean",
            description="Preview changes without applying",
            required=False,
            default=False
        ),
        ToolParameter(
            name="fuzzy_match",
            type="boolean",
            description="Enable fuzzy matching",
            required=False,
            default=True
        ),
    ],
    returns={
        "type": "object",
        "description": "File edit result with diff",
        "properties": {
            "file_path": {"type": "string"},
            "lines_changed": {"type": "integer"},
            "occurrences_replaced": {"type": "integer"},
        }
    },
    version="2.0.0"
)


# ============================================================================
# GlobTool Schema (Enhanced)
# ============================================================================

class GlobSearchInput(BaseModel):
    """Input schema for GlobTool."""

    pattern: str = Field(..., description="Glob pattern (e.g., '**/*.py')")
    path: str | None = Field(None, description="Directory to search in (default: cwd)")
    exclude_patterns: list[str] = Field(default_factory=list, description="Patterns to exclude")
    follow_symlinks: bool = Field(default=False, description="Follow symbolic links")
    max_depth: int | None = Field(None, description="Maximum directory depth", ge=1)
    file_types: list[str] | None = Field(None, description="File types to include (e.g., ['py', 'js'])")
    sort_by_mtime: bool = Field(default=True, description="Sort by modification time (newest first)")
    head_limit: int = Field(default=250, description="Maximum results to return", ge=1, le=10000)
    offset: int = Field(default=0, description="Skip first N results", ge=0)

    @field_validator("pattern")
    @classmethod
    def validate_pattern(cls, v: str) -> str:
        """Validate pattern is not empty."""
        if not v or not v.strip():
            raise ValueError("Pattern cannot be empty")
        return v.strip()


class GlobSearchOutput(BaseModel):
    """Output schema for GlobTool."""

    files: list[str] = Field(..., description="List of matching file paths")
    total_count: int = Field(..., description="Total number of matches")
    is_truncated: bool = Field(default=False, description="Whether results were truncated")


GLOB_SEARCH_SCHEMA_V2 = ToolSchema(
    name="glob_search",
    description="Search files by glob pattern with sorting, filtering, and pagination",
    category="filesystem",
    parameters=[
        ToolParameter(
            name="pattern",
            type="string",
            description="Glob pattern (e.g., '**/*.py')",
            required=True
        ),
        ToolParameter(
            name="path",
            type="string",
            description="Directory to search in (default: cwd)",
            required=False
        ),
        ToolParameter(
            name="exclude_patterns",
            type="array",
            description="Patterns to exclude",
            required=False
        ),
        ToolParameter(
            name="follow_symlinks",
            type="boolean",
            description="Follow symbolic links",
            required=False,
            default=False
        ),
        ToolParameter(
            name="max_depth",
            type="integer",
            description="Maximum directory depth",
            required=False,
            constraints={"minimum": 1}
        ),
        ToolParameter(
            name="sort_by_mtime",
            type="boolean",
            description="Sort by modification time (newest first)",
            required=False,
            default=True
        ),
        ToolParameter(
            name="head_limit",
            type="integer",
            description="Maximum results to return",
            required=False,
            default=250,
            constraints={"minimum": 1, "maximum": 10000}
        ),
        ToolParameter(
            name="offset",
            type="integer",
            description="Skip first N results",
            required=False,
            default=0,
            constraints={"minimum": 0}
        ),
    ],
    returns={
        "type": "object",
        "description": "Glob search results",
        "properties": {
            "files": {"type": "array", "items": {"type": "string"}},
            "total_count": {"type": "integer"},
            "is_truncated": {"type": "boolean"},
        }
    },
    version="2.0.0"
)


# ============================================================================
# GrepTool Schema (Enhanced)
# ============================================================================

class GrepSearchInput(BaseModel):
    """Input schema for GrepTool."""

    pattern: str = Field(..., description="Regex pattern to search")
    path: str | None = Field(None, description="File or directory to search (default: cwd)")
    glob: str | None = Field(None, description="Glob pattern to filter files (e.g., '*.py')")
    file_type: str | None = Field(None, description="File type filter (py, js, rust, etc.)")
    output_mode: str = Field(default="content", description="Output mode: content/files/count")
    case_sensitive: bool = Field(default=True, description="Case sensitive search")
    multiline: bool = Field(default=False, description="Enable multiline mode")
    context_before: int = Field(default=0, description="Lines of context before match", ge=0, le=10)
    context_after: int = Field(default=0, description="Lines of context after match", ge=0, le=10)
    context: int | None = Field(None, description="Lines of context (before + after)", ge=0, le=10)
    line_numbers: bool = Field(default=True, description="Show line numbers")
    head_limit: int = Field(default=250, description="Maximum results", ge=1, le=10000)
    offset: int = Field(default=0, description="Skip first N results", ge=0)

    @field_validator("pattern")
    @classmethod
    def validate_pattern(cls, v: str) -> str:
        """Validate pattern is not empty."""
        if not v or not v.strip():
            raise ValueError("Pattern cannot be empty")
        return v.strip()

    @field_validator("output_mode")
    @classmethod
    def validate_output_mode(cls, v: str) -> str:
        """Validate output mode."""
        valid_modes = ["content", "files", "count", "files_with_matches"]
        if v not in valid_modes:
            raise ValueError(f"Invalid output_mode: {v}. Must be one of {valid_modes}")
        return v


class GrepSearchOutput(BaseModel):
    """Output schema for GrepTool."""

    matches: list[dict[str, Any]] = Field(..., description="Search matches")
    total_count: int = Field(..., description="Total number of matches")
    num_files: int | None = Field(None, description="Number of files with matches")
    num_lines: int | None = Field(None, description="Number of matching lines")
    is_truncated: bool = Field(default=False, description="Whether results were truncated")


GREP_SEARCH_SCHEMA_V2 = ToolSchema(
    name="grep_search",
    description="Search file contents with regex, context lines, and multiple output modes",
    category="filesystem",
    parameters=[
        ToolParameter(
            name="pattern",
            type="string",
            description="Regex pattern to search",
            required=True
        ),
        ToolParameter(
            name="path",
            type="string",
            description="File or directory to search (default: cwd)",
            required=False
        ),
        ToolParameter(
            name="glob",
            type="string",
            description="Glob pattern to filter files (e.g., '*.py')",
            required=False
        ),
        ToolParameter(
            name="file_type",
            type="string",
            description="File type filter (py, js, rust, etc.)",
            required=False
        ),
        ToolParameter(
            name="output_mode",
            type="string",
            description="Output mode",
            required=False,
            default="content",
            enum=["content", "files", "count", "files_with_matches"]
        ),
        ToolParameter(
            name="case_sensitive",
            type="boolean",
            description="Case sensitive search",
            required=False,
            default=True
        ),
        ToolParameter(
            name="multiline",
            type="boolean",
            description="Enable multiline mode",
            required=False,
            default=False
        ),
        ToolParameter(
            name="context_before",
            type="integer",
            description="Lines of context before match (-B)",
            required=False,
            default=0,
            constraints={"minimum": 0, "maximum": 10}
        ),
        ToolParameter(
            name="context_after",
            type="integer",
            description="Lines of context after match (-A)",
            required=False,
            default=0,
            constraints={"minimum": 0, "maximum": 10}
        ),
        ToolParameter(
            name="context",
            type="integer",
            description="Lines of context (before + after) (-C)",
            required=False,
            constraints={"minimum": 0, "maximum": 10}
        ),
        ToolParameter(
            name="line_numbers",
            type="boolean",
            description="Show line numbers",
            required=False,
            default=True
        ),
        ToolParameter(
            name="head_limit",
            type="integer",
            description="Maximum results",
            required=False,
            default=250,
            constraints={"minimum": 1, "maximum": 10000}
        ),
        ToolParameter(
            name="offset",
            type="integer",
            description="Skip first N results",
            required=False,
            default=0,
            constraints={"minimum": 0}
        ),
    ],
    returns={
        "type": "object",
        "description": "Grep search results",
        "properties": {
            "matches": {"type": "array"},
            "total_count": {"type": "integer"},
            "num_files": {"type": "integer"},
            "num_lines": {"type": "integer"},
            "is_truncated": {"type": "boolean"},
        }
    },
    version="2.0.0"
)


# Export all schemas
FILESYSTEM_SCHEMAS_V2 = {
    "read_file": READ_FILE_SCHEMA_V2,
    "write_file": WRITE_FILE_SCHEMA_V2,
    "edit_file": EDIT_FILE_SCHEMA_V2,
    "glob_search": GLOB_SEARCH_SCHEMA_V2,
    "grep_search": GREP_SEARCH_SCHEMA_V2,
}
