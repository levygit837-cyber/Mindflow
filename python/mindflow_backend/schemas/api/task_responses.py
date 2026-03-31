"""Response schemas for Tasks API."""

from typing import Any

from pydantic import BaseModel, Field


class TaskInfoResponse(BaseModel):
    """Response for task information operations."""
    
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    task: dict[str, Any] = Field(..., description="Task information")


class TaskListResponse(BaseModel):
    """Response for task listing operations."""
    
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    session_id: str = Field(..., description="Session identifier")
    tasks: list[dict[str, Any]] = Field(..., description="List of tasks")
    total: int = Field(..., description="Total number of tasks")


class TaskCancelResponse(BaseModel):
    """Response for task cancellation operations."""
    
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    task_id: str = Field(..., description="ID of the cancelled task")
    cancel_result: dict[str, Any] = Field(..., description="Cancellation result details")


class TaskRetryResponse(BaseModel):
    """Response for task retry operations."""
    
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    task_id: str = Field(..., description="ID of the retried task")
    retry_result: dict[str, Any] = Field(..., description="Retry result details")


class TaskSubtasksResponse(BaseModel):
    """Response for task subtasks operations."""
    
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    task_id: str = Field(..., description="Parent task identifier")
    subtasks: list[dict[str, Any]] = Field(..., description="List of subtasks")
    total: int = Field(..., description="Total number of subtasks")
