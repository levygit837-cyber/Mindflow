"""Execution task runtime contracts for orchestrated task processing."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ExecutionTaskStatus(StrEnum):
    """Operational status for a runtime execution task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"


class ExecutionTaskType(StrEnum):
    """Execution task type for runtime visibility."""

    AGENT_STEP = "agent_step"
    TOOL_CALL = "tool_call"
    WORKFLOW_STEP = "workflow_step"


class ExecutionTaskContract(BaseModel):
    """A single runtime execution task instance."""

    execution_task_id: str
    session_id: str
    task_id: str
    item_id: str | None = None
    execution_key: str
    type: ExecutionTaskType = ExecutionTaskType.WORKFLOW_STEP
    status: ExecutionTaskStatus = ExecutionTaskStatus.PENDING
    description: str
    attempt: int = 1
    output: list[str] = Field(default_factory=list)
    output_ref: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    ended_at: datetime | None = None


class ExecutionTaskControl(BaseModel):
    """Task-level control flags shared by runtime executions."""

    cancel_requested: bool = False
    cancel_requested_at: datetime | None = None
    cancel_reason: str | None = None
    force: bool = False

