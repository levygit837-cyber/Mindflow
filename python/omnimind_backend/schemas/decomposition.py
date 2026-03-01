from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class DTStatus(StrEnum):
    PENDING = "pending"
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class DTTask(BaseModel):
    """A sub-task within a decomposed thinking session."""
    id: str
    title: str
    description: str
    agent_type: str | None = None  # Specific agent recommended for this task
    dependencies: list[str] = Field(default_factory=list)
    status: DTStatus = DTStatus.PENDING
    result: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class DTSession(BaseModel):
    """State for a multi-step decomposition thinking session."""
    id: str
    session_id: str  # Original chat session ID
    original_task: str
    tasks: list[DTTask] = Field(default_factory=list)
    status: DTStatus = DTStatus.PENDING
    final_response: str | None = None
    complexity_score: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
