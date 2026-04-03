"""Task management schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TaskBase(BaseModel):
    """Base task schema with common fields."""

    task_list_id: str = Field(..., max_length=64)
    subject: str = Field(..., max_length=256)
    description: str = Field(default="")
    active_form: str | None = Field(default=None, max_length=256)
    owner: str | None = Field(default=None, max_length=64)
    status: str = Field(default="pending")
    task_metadata: dict[str, Any] = Field(default_factory=dict)


class TaskCreate(TaskBase):
    """Schema for creating a new task."""

    blocks: list[int] = Field(default_factory=list)
    blocked_by: list[int] = Field(default_factory=list)


class TaskUpdate(BaseModel):
    """Schema for updating an existing task."""

    subject: str | None = Field(default=None, max_length=256)
    description: str | None = None
    active_form: str | None = Field(default=None, max_length=256)
    owner: str | None = Field(default=None, max_length=64)
    status: str | None = None
    task_metadata: dict[str, Any] | None = None
    add_blocks: list[int] = Field(default_factory=list)
    remove_blocks: list[int] = Field(default_factory=list)
    add_blocked_by: list[int] = Field(default_factory=list)
    remove_blocked_by: list[int] = Field(default_factory=list)
    version: int | None = None  # For optimistic locking


class TaskResponse(TaskBase):
    """Schema for task response."""

    id: int
    blocks: list[int] = Field(default_factory=list)
    blocked_by: list[int] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    version: int

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """Schema for task list response."""

    tasks: list[TaskResponse]
    total: int
    limit: int
    offset: int


class TaskDependencyCreate(BaseModel):
    """Schema for creating a task dependency."""

    task_id: int
    blocks_task_id: int
