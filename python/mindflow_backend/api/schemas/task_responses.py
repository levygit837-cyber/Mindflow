"""Response schemas for Tasks API."""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any


class TaskInfoResponse(BaseModel):
    """Response for task information operations."""
    
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    task: Dict[str, Any] = Field(..., description="Task information")


class TaskListResponse(BaseModel):
    """Response for task listing operations."""
    
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    session_id: str = Field(..., description="Session identifier")
    tasks: List[Dict[str, Any]] = Field(..., description="List of tasks")
    total: int = Field(..., description="Total number of tasks")


class TaskCancelResponse(BaseModel):
    """Response for task cancellation operations."""
    
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    task_id: str = Field(..., description="ID of the cancelled task")
    cancel_result: Dict[str, Any] = Field(..., description="Cancellation result details")


class TaskRetryResponse(BaseModel):
    """Response for task retry operations."""
    
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    task_id: str = Field(..., description="ID of the retried task")
    retry_result: Dict[str, Any] = Field(..., description="Retry result details")


class TaskSubtasksResponse(BaseModel):
    """Response for task subtasks operations."""
    
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    task_id: str = Field(..., description="Parent task identifier")
    subtasks: List[Dict[str, Any]] = Field(..., description="List of subtasks")
    total: int = Field(..., description="Total number of subtasks")
