"""Streaming progress schemas for MindFlow tool execution.

Mirrors Claude Code CLI progressive output system (Tool.ts Progress types):
- ToolProgress: generic wrapper for streaming updates
- Progress types: percentage, log, artifact, hook_progress
- ProgressMessage: a single progress event in tool execution

Design principles:
- All progress updates follow a consistent schema
- Supports multiple progress types per tool execution
- Compatible with streaming APIs (SSE, websockets, async generators)
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ProgressType(StrEnum):
    """Type of progress update a tool can emit."""

    PERCENTAGE = "percentage"    # Numeric progress (0-100)
    LOG = "log"                  # Text log line
    ARTIFACT = "artifact"        # Partial artifact (file preview, etc.)
    HOOK_PROGRESS = "hook_progress"  # Hook execution progress


class ProgressLevel(StrEnum):
    """Severity/importance of a progress message."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Progress Data Models
# ---------------------------------------------------------------------------


class PercentageProgress(BaseModel):
    """Numeric progress update (0-100%)."""

    model_config = {"extra": "ignore", "populate_by_name": True}

    percentage: int = Field(
        ...,
        ge=0,
        le=100,
        description="Current progress percentage (0-100)",
    )
    message: str = Field(default="", description="Current status message")
    total_steps: int | None = Field(default=None, description="Total number of steps")
    completed_steps: int = Field(default=0, description="Number of completed steps")


class LogProgress(BaseModel):
    """Text log line from tool execution."""

    model_config = {"extra": "ignore", "populate_by_name": True}

    line: str = Field(..., description="Log line content")
    stream: str = Field(default="stdout", description="Stream name (stdout/stderr)")
    level: ProgressLevel = Field(default=ProgressLevel.INFO, description="Log level")
    timestamp: str | None = Field(default=None, description="ISO timestamp")


class ArtifactProgress(BaseModel):
    """Partial artifact preview (file content, image, etc.)."""

    model_config = {"extra": "ignore", "populate_by_name": True}

    content_preview: str = Field(
        default="",
        description="Preview of the artifact content",
    )
    total_size: int | None = Field(default=None, description="Total size in bytes")
    completed_size: int | None = Field(default=None, description="Downloaded/processed size")
    mime_type: str | None = Field(default=None, description="MIME type of artifact")
    filename: str | None = Field(default=None, description="Artifact filename")
    truncated: bool = Field(default=False, description="Whether preview is truncated")


class HookProgress(BaseModel):
    """Progress from hook execution."""

    model_config = {"extra": "ignore", "populate_by_name": True}

    hook_name: str = Field(..., description="Name of the executing hook")
    hook_type: str = Field(..., description="Type of hook (PreToolUse, PostToolUse, etc.)")
    message: str = Field(default="", description="Progress message from hook")
    status: str = Field(default="running", description="Hook status: running/completed/failed")


# ---------------------------------------------------------------------------
# Container Models
# ---------------------------------------------------------------------------


class ToolProgressData(BaseModel):
    """Unified progress data union.

    Similar to Claude Code's ToolProgressData type which can hold different
    progress subtypes depending on the tool emitting the progress.
    """

    model_config = {"extra": "ignore", "populate_by_name": True}

    type: ProgressType = Field(..., description="Type of progress update")
    tool_id: str = Field(default="", description="Tool identifier")
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="Progress payload (type-specific)",
    )

    @classmethod
    def from_percentage(
        cls,
        tool_id: str,
        percentage: int,
        message: str = "",
        total: int | None = None,
        completed: int = 0,
    ) -> ToolProgressData:
        """Create a percentage progress update."""
        return cls(
            type=ProgressType.PERCENTAGE,
            tool_id=tool_id,
            data={
                "percentage": percentage,
                "message": message,
                "total_steps": total,
                "completed_steps": completed,
            },
        )

    @classmethod
    def from_log(
        cls,
        tool_id: str,
        line: str,
        stream: str = "stdout",
        level: ProgressLevel = ProgressLevel.INFO,
    ) -> ToolProgressData:
        """Create a log progress update."""
        return cls(
            type=ProgressType.LOG,
            tool_id=tool_id,
            data={"line": line, "stream": stream, "level": level.value},
        )

    @classmethod
    def from_artifact(
        cls,
        tool_id: str,
        content: str = "",
        filename: str | None = None,
        mime_type: str | None = None,
        total_size: int | None = None,
        completed_size: int | None = None,
    ) -> ToolProgressData:
        """Create an artifact progress update."""
        return cls(
            type=ProgressType.ARTIFACT,
            tool_id=tool_id,
            data={
                "content_preview": content[:500] if content else "",
                "filename": filename,
                "mime_type": mime_type,
                "total_size": total_size,
                "completed_size": completed_size,
                "truncated": len(content) > 500 if content else False,
            },
        )

    @classmethod
    def from_hook(
        cls,
        tool_id: str,
        hook_name: str,
        hook_type: str,
        message: str = "",
        status: str = "running",
    ) -> ToolProgressData:
        """Create a hook progress update."""
        return cls(
            type=ProgressType.HOOK_PROGRESS,
            tool_id=tool_id,
            data={
                "hook_name": hook_name,
                "hook_type": hook_type,
                "message": message,
                "status": status,
            },
        )