"""Enhanced tool metadata schemas for MindFlow backend.

Provides comprehensive metadata tracking for tools including git integration,
LSP integration, file history, and execution context.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ToolExecutionStatus(str, Enum):
    """Tool execution status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FileModificationMetadata(BaseModel):
    """Metadata for file modification operations."""

    file_path: str = Field(..., description="Absolute path to modified file")
    modification_time_before: datetime | None = Field(None, description="Modification time before operation")
    modification_time_after: datetime | None = Field(None, description="Modification time after operation")
    file_size_before: int | None = Field(None, description="File size before operation (bytes)")
    file_size_after: int | None = Field(None, description="File size after operation (bytes)")
    encoding: str = Field(default="utf-8", description="File encoding")
    line_ending: str | None = Field(None, description="Line ending type (LF/CRLF)")

    class Config:
        json_schema_extra = {
            "example": {
                "file_path": "/home/user/project/file.py",
                "modification_time_before": "2026-04-01T10:00:00",
                "modification_time_after": "2026-04-01T10:00:05",
                "file_size_before": 1024,
                "file_size_after": 1536,
                "encoding": "utf-8",
                "line_ending": "LF"
            }
        }


class GitDiffMetadata(BaseModel):
    """Git diff metadata for file changes."""

    file_path: str = Field(..., description="File path relative to git root")
    diff_text: str | None = Field(None, description="Git diff output")
    additions: int = Field(default=0, description="Number of lines added")
    deletions: int = Field(default=0, description="Number of lines deleted")
    is_new_file: bool = Field(default=False, description="Whether file is newly created")
    is_deleted: bool = Field(default=False, description="Whether file is deleted")
    commit_sha: str | None = Field(None, description="Associated commit SHA")

    class Config:
        json_schema_extra = {
            "example": {
                "file_path": "src/main.py",
                "diff_text": "@@ -1,3 +1,4 @@\n import sys\n+import os\n",
                "additions": 1,
                "deletions": 0,
                "is_new_file": False,
                "is_deleted": False
            }
        }


class FileHistoryEntry(BaseModel):
    """File history entry for rollback support."""

    file_path: str = Field(..., description="Absolute path to file")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp of change")
    operation: str = Field(..., description="Operation type (read/write/edit)")
    content_before: str | None = Field(None, description="Content before change")
    content_after: str | None = Field(None, description="Content after change")
    user_id: str | None = Field(None, description="User who made the change")
    session_id: str | None = Field(None, description="Session ID")

    class Config:
        json_schema_extra = {
            "example": {
                "file_path": "/home/user/project/config.py",
                "timestamp": "2026-04-01T10:00:00",
                "operation": "edit",
                "content_before": "DEBUG = False",
                "content_after": "DEBUG = True",
                "session_id": "sess_123"
            }
        }


class LSPDiagnostic(BaseModel):
    """LSP diagnostic information."""

    file_path: str = Field(..., description="File path")
    line: int = Field(..., description="Line number (0-indexed)")
    column: int = Field(..., description="Column number (0-indexed)")
    severity: str = Field(..., description="Severity (error/warning/info/hint)")
    message: str = Field(..., description="Diagnostic message")
    source: str | None = Field(None, description="Diagnostic source (e.g., 'pylint')")
    code: str | None = Field(None, description="Diagnostic code")

    class Config:
        json_schema_extra = {
            "example": {
                "file_path": "/home/user/project/main.py",
                "line": 10,
                "column": 5,
                "severity": "error",
                "message": "Undefined variable 'foo'",
                "source": "pylint",
                "code": "E0602"
            }
        }


class ToolExecutionMetadata(BaseModel):
    """Comprehensive metadata for tool execution."""

    tool_name: str = Field(..., description="Tool name")
    execution_id: str = Field(..., description="Unique execution ID")
    session_id: str | None = Field(None, description="Session ID")
    user_id: str | None = Field(None, description="User ID")

    # Timing
    start_time: datetime = Field(default_factory=datetime.now, description="Execution start time")
    end_time: datetime | None = Field(None, description="Execution end time")
    duration_ms: int | None = Field(None, description="Execution duration in milliseconds")

    # Status
    status: ToolExecutionStatus = Field(default=ToolExecutionStatus.PENDING, description="Execution status")
    error_message: str | None = Field(None, description="Error message if failed")

    # File operations
    file_metadata: FileModificationMetadata | None = Field(None, description="File modification metadata")
    git_diff: GitDiffMetadata | None = Field(None, description="Git diff metadata")
    file_history: FileHistoryEntry | None = Field(None, description="File history entry")

    # LSP integration
    lsp_diagnostics: list[LSPDiagnostic] = Field(default_factory=list, description="LSP diagnostics")

    # Performance
    memory_usage_mb: float | None = Field(None, description="Memory usage in MB")
    cpu_time_ms: int | None = Field(None, description="CPU time in milliseconds")

    # Context
    working_directory: str | None = Field(None, description="Working directory")
    environment_vars: dict[str, str] = Field(default_factory=dict, description="Environment variables")

    # Additional metadata
    custom_metadata: dict[str, Any] = Field(default_factory=dict, description="Custom metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "tool_name": "file_read",
                "execution_id": "exec_abc123",
                "session_id": "sess_xyz789",
                "start_time": "2026-04-01T10:00:00",
                "end_time": "2026-04-01T10:00:01",
                "duration_ms": 1000,
                "status": "completed",
                "working_directory": "/home/user/project"
            }
        }


class StructuredPatchHunk(BaseModel):
    """Structured representation of a diff hunk."""

    old_start: int = Field(..., description="Start line in old file")
    old_lines: int = Field(..., description="Number of lines in old file")
    new_start: int = Field(..., description="Start line in new file")
    new_lines: int = Field(..., description="Number of lines in new file")
    header: str = Field(..., description="Hunk header (e.g., '@@ -1,3 +1,4 @@')")
    lines: list[str] = Field(..., description="Diff lines (with +/- prefix)")

    class Config:
        json_schema_extra = {
            "example": {
                "old_start": 1,
                "old_lines": 3,
                "new_start": 1,
                "new_lines": 4,
                "header": "@@ -1,3 +1,4 @@",
                "lines": [
                    " import sys",
                    "+import os",
                    " ",
                    " def main():"
                ]
            }
        }


class StructuredPatch(BaseModel):
    """Structured representation of file changes."""

    file_path: str = Field(..., description="File path")
    operation: str = Field(..., description="Operation (create/update/delete)")
    hunks: list[StructuredPatchHunk] = Field(default_factory=list, description="Diff hunks")
    additions: int = Field(default=0, description="Total lines added")
    deletions: int = Field(default=0, description="Total lines deleted")

    class Config:
        json_schema_extra = {
            "example": {
                "file_path": "src/main.py",
                "operation": "update",
                "hunks": [],
                "additions": 1,
                "deletions": 0
            }
        }
