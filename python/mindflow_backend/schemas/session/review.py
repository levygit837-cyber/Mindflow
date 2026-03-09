"""Session review schemas for MindFlow backend.

Provides schemas for session review operations including context
analysis, quality assessment, and review workflows.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ReviewPriority(StrEnum):
    """Priority level for review tasks."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReviewTaskType(StrEnum):
    """Type of review task."""
    
    CONTEXT_REVIEW = "context_review"
    QUALITY_ASSESSMENT = "quality_assessment"
    PERFORMANCE_ANALYSIS = "performance_analysis"
    ERROR_DETECTION = "error_detection"
    OPTIMIZATION = "optimization"


class ReviewTriggerType(StrEnum):
    """Type of review trigger."""
    
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    EVENT_BASED = "event_based"


class ReviewTask(BaseModel):
    """Review task definition."""
    
    id: UUID = Field(description="Review task identifier")
    session_id: UUID = Field(description="Session identifier")
    
    # Task information
    task_type: ReviewTaskType = Field(description="Type of review task")
    priority: ReviewPriority = Field(default=ReviewPriority.MEDIUM, description="Task priority")
    title: str = Field(description="Task title")
    description: Optional[str] = Field(default=None, description="Task description")
    
    # Task configuration
    trigger_type: ReviewTriggerType = Field(description="What triggered this review")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Task parameters")
    
    # Temporal information
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    scheduled_for: Optional[datetime] = Field(default=None, description="Scheduled execution time")
    started_at: Optional[datetime] = Field(default=None, description="Task start time")
    completed_at: Optional[datetime] = Field(default=None, description="Task completion time")
    
    # Task status
    status: str = Field(default="pending", description="Task status")
    progress: float = Field(default=0.0, ge=0.0, le=1.0, description="Task progress")
    
    # Results
    result: Optional[Dict[str, Any]] = Field(default=None, description="Task results")
    issues_found: List[str] = Field(default_factory=list, description="Issues found during review")
    recommendations: List[str] = Field(default_factory=list, description="Review recommendations")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class ReviewExecutionContext(BaseModel):
    """Context for review execution."""
    
    session_id: UUID = Field(description="Session identifier")
    task_id: UUID = Field(description="Review task identifier")
    
    # Context window
    window_start: int = Field(ge=0, description="Window start position")
    window_end: int = Field(ge=0, description="Window end position")
    window_size: int = Field(gt=0, description="Window size")
    
    # Review configuration
    review_type: ReviewTaskType = Field(description="Type of review to perform")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Review parameters")
    
    # Context data
    messages: List[Dict[str, Any]] = Field(default_factory=list, description="Messages in context")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context metadata")
    
    # Execution context
    agent_id: Optional[str] = Field(default=None, description="Agent performing review")
    tools_available: List[str] = Field(default_factory=list, description="Available tools")
    
    class Config:
        json_encoders = {
            UUID: lambda v: str(v),
        }


class ReviewResult(BaseModel):
    """Result of a review operation."""
    
    task_id: UUID = Field(description="Review task identifier")
    session_id: UUID = Field(description="Session identifier")
    
    # Review outcome
    success: bool = Field(description="Whether review was successful")
    completion_rate: float = Field(ge=0.0, le=1.0, description="Review completion rate")
    
    # Findings
    issues_found: List[Dict[str, Any]] = Field(default_factory=list, description="Issues identified")
    recommendations: List[Dict[str, Any]] = Field(default_factory=list, description="Recommendations made")
    
    # Quality metrics
    quality_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Overall quality score")
    context_relevance: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Context relevance score")
    
    # Performance metrics
    processing_time_ms: Optional[int] = Field(default=None, description="Processing time")
    tokens_analyzed: int = Field(ge=0, description="Number of tokens analyzed")
    
    # Metadata
    reviewed_by: Optional[str] = Field(default=None, description="Agent or system that performed review")
    reviewed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional result metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class ReviewSession(BaseModel):
    """Complete review session for a context window."""
    
    id: UUID = Field(description="Review session identifier")
    session_id: UUID = Field(description="Original session identifier")
    
    # Session information
    window_start: int = Field(ge=0, description="Window start position")
    window_end: int = Field(ge=0, description="Window end position")
    window_size: int = Field(gt=0, description="Window size")
    
    # Review tasks
    tasks: List[ReviewTask] = Field(default_factory=list, description="Review tasks in this session")
    completed_tasks: List[ReviewTask] = Field(default_factory=list, description="Completed tasks")
    
    # Session status
    status: str = Field(default="active", description="Session status")
    progress: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall session progress")
    
    # Temporal information
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: Optional[datetime] = Field(default=None, description="Session start time")
    completed_at: Optional[datetime] = Field(default=None, description="Session completion time")
    
    # Results summary
    total_issues: int = Field(default=0, description="Total issues found")
    critical_issues: int = Field(default=0, description="Critical issues found")
    recommendations_count: int = Field(default=0, description="Total recommendations made")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


# Export all review schemas
__all__ = [
    "ReviewPriority",
    "ReviewTaskType",
    "ReviewTriggerType",
    "ReviewTask",
    "ReviewExecutionContext",
    "ReviewResult",
    "ReviewSession",
]
