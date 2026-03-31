from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class TaskStatus(StrEnum):
    PENDING = "pending"
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    BLOCKED = "blocked"
    DONE = "done"
    FAILED = "failed"


class TaskTask(BaseModel):
    """A sub-task within a decomposed thinking session."""
    id: str
    title: str
    description: str
    agent_type: str | None = None  # Specific agent recommended for this task
    dependencies: list[str] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class TaskSession(BaseModel):
    """State for a multi-step decomposition thinking session."""
    id: str
    session_id: str  # Original chat session ID
    original_task: str
    tasks: list[TaskTask] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    final_response: str | None = None
    complexity_score: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
