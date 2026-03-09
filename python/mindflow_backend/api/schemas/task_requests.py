"""Additional request schemas for Tasks API."""

from pydantic import BaseModel, Field
from typing import Optional


class TaskCancelRequest(BaseModel):
    """Request to cancel a task."""
    
    reason: Optional[str] = Field(None, description="Reason for cancellation")
    force: bool = Field(False, description="Force cancellation even if in critical state")


class TaskRetryRequest(BaseModel):
    """Request to retry a task."""
    
    retry_subtasks: bool = Field(False, description="Also retry failed subtasks")
    retry_from_beginning: bool = Field(False, description="Start retry from the beginning")
    max_retry_attempts: int = Field(3, description="Maximum retry attempts")
