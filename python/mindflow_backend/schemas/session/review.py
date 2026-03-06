"""Session review schemas for context governance and agent memory.

Defines contracts for session review configuration, execution,
and structured documentation of agent actions within token windows.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ReviewTriggerType(StrEnum):
    """Trigger types for automatic session reviews."""
    
    TOKEN_THRESHOLD = "token_threshold"
    TIME_BASED = "time_based"
    MANUAL = "manual"
    EVENT_BASED = "event_based"


class WindowSize(StrEnum):
    """Standard window sizes for session reviews."""
    
    SMALL = "small"  # 5K tokens
    MEDIUM = "medium"  # 10K tokens
    LARGE = "large"  # 20K tokens
    EXTRA_LARGE = "extra_large"  # 50K tokens
    CUSTOM = "custom"


class ReviewPriority(StrEnum):
    """Priority levels for session reviews."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SessionReviewConfig(BaseModel):
    """Configuration for session review system.
    
    Defines when and how to perform automatic reviews
    of agent sessions within token windows.
    """
    
    session_id: UUID
    enabled: bool = Field(default=True, description="Enable automatic reviews")
    window_size: WindowSize = Field(default=WindowSize.MEDIUM, description="Size of review windows")
    custom_window_tokens: int | None = Field(default=None, description="Custom token count for CUSTOM size")
    trigger_type: ReviewTriggerType = Field(default=ReviewTriggerType.TOKEN_THRESHOLD)
    trigger_threshold: int = Field(default=10000, description="Tokens threshold for automatic review")
    max_reviews_per_session: int = Field(default=50, description="Maximum reviews to prevent infinite loops")
    review_priority: ReviewPriority = Field(default=ReviewPriority.MEDIUM)
    auto_advance_windows: bool = Field(default=True, description="Automatically advance to next window")
    include_embeddings: bool = Field(default=True, description="Generate embeddings for reviews")
    retention_days: int = Field(default=30, description="Days to retain review data")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TokenWindowConfig(BaseModel):
    """Configuration for token window boundaries."""
    
    window_size: int = Field(description="Size of each token window")
    overlap_tokens: int = Field(default=500, description="Overlap between consecutive windows")
    max_windows: int = Field(default=100, description="Maximum number of windows")
    current_window: int = Field(default=0, description="Current window index")
    total_tokens: int = Field(default=0, description="Total tokens processed")
    
    def get_window_bounds(self, window_index: int) -> tuple[int, int]:
        """Get start and end token bounds for a window."""
        start = window_index * self.window_size
        end = start + self.window_size
        return start, end
    
    def get_current_bounds(self) -> tuple[int, int]:
        """Get bounds for current window."""
        return self.get_window_bounds(self.current_window)


class ReviewTriggerConfig(BaseModel):
    """Configuration for review triggers."""
    
    trigger_type: ReviewTriggerType
    threshold_value: int | None = Field(default=None, description="Threshold value for trigger")
    time_interval_minutes: int | None = Field(default=None, description="Time interval in minutes")
    event_types: list[str] = Field(default_factory=list, description="Event types that trigger review")
    enabled: bool = Field(default=True)
    last_triggered_at: datetime | None = Field(default=None)


class ActionDocumentation(BaseModel):
    """Documentation of a specific action taken by an agent."""
    
    action_id: UUID = Field(default_factory=lambda: UUID())
    session_id: UUID
    window_range: tuple[int, int] = Field(description="Token window where action occurred")
    action_type: str = Field(description="Type of action performed")
    description: str = Field(description="Detailed description of action")
    agent_type: str = Field(description="Type of agent that performed action")
    files_affected: list[str] = Field(default_factory=list, description="Files modified/created")
    commands_executed: list[str] = Field(default_factory=list, description="Commands run by agent")
    outcomes: list[str] = Field(default_factory=list, description="Results of action")
    confidence_score: float = Field(default=0.8, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict = Field(default_factory=dict)


class ContextInsight(BaseModel):
    """Key insight extracted from a session window."""
    
    insight_id: UUID = Field(default_factory=lambda: UUID())
    session_id: UUID
    window_range: tuple[int, int]
    insight_type: str = Field(description="Type of insight (pattern, decision, outcome)")
    content: str = Field(description="Insight content")
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    supporting_evidence: list[str] = Field(default_factory=list, description="Evidence supporting insight")
    related_actions: list[UUID] = Field(default_factory=list, description="Related action IDs")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SessionReviewResult(BaseModel):
    """Complete result of a session window review."""
    
    review_id: UUID = Field(default_factory=lambda: UUID())
    session_id: UUID
    window_range: tuple[int, int] = Field(description="Token window reviewed")
    window_index: int = Field(description="Index of this window in sequence")
    review_config_id: UUID = Field(description="Configuration used for this review")
    
    # Analysis Results
    actions_documented: list[ActionDocumentation] = Field(default_factory=list)
    insights_extracted: list[ContextInsight] = Field(default_factory=list)
    summary_text: str = Field(description="Human-readable summary of window")
    
    # Metrics
    total_actions: int = Field(default=0)
    total_insights: int = Field(default=0)
    coverage_percentage: float = Field(default=1.0, ge=0.0, le=1.0)
    processing_time_seconds: float = Field(default=0.0)
    
    # Quality Indicators
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    completeness_score: float = Field(default=0.5, ge=0.0, le=1.0)
    relevance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Metadata
    review_type: str = Field(default="automatic")
    reviewer_agent_id: str = Field(description="Agent that performed review")
    trigger_reason: str = Field(description="Why this review was triggered")
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = Field(default=None)


class TokenWindowTracker(BaseModel):
    """Tracker for current position in token windows."""
    
    session_id: UUID
    current_window: int = Field(default=0)
    total_tokens_processed: int = Field(default=0)
    window_size: int = Field(default=10000)
    overlap_tokens: int = Field(default=500)
    
    # Progress tracking
    tokens_in_current_window: int = Field(default=0)
    progress_percentage: float = Field(default=0.0)
    windows_completed: int = Field(default=0)
    
    # Threshold tracking
    next_review_threshold: int = Field(default=10000)
    last_review_at: datetime | None = Field(default=None)
    next_review_scheduled_at: datetime | None = Field(default=None)
    
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    def should_trigger_review(self, threshold: int) -> bool:
        """Check if review should be triggered."""
        return self.tokens_in_current_window >= threshold
    
    def advance_to_next_window(self) -> tuple[int, int]:
        """Advance to next window and return new bounds."""
        self.windows_completed += 1
        self.current_window += 1
        self.tokens_in_current_window = 0
        return self.get_current_window_bounds()
    
    def get_current_window_bounds(self) -> tuple[int, int]:
        """Get current window token bounds."""
        start = self.current_window * self.window_size
        end = start + self.window_size
        return start, end


class WindowProgressInfo(BaseModel):
    """Information about window progress and scheduling."""
    
    session_id: UUID
    current_window: tuple[int, int] = Field(description="Current window bounds")
    window_index: int = Field(description="Current window index")
    progress_in_window: float = Field(description="Progress through current window (0-1)")
    overall_progress: float = Field(description="Progress through all tokens (0-1)")
    tokens_until_next_review: int = Field(description="Tokens remaining until next review")
    estimated_next_review: datetime | None = Field(description="When next review will occur")
    windows_remaining: int = Field(description="Estimated windows remaining")
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReviewSchedule(BaseModel):
    """Scheduled review information."""
    
    schedule_id: UUID = Field(default_factory=lambda: UUID())
    session_id: UUID
    window_index: int
    scheduled_for: datetime
    priority: ReviewPriority = Field(default=ReviewPriority.MEDIUM)
    review_type: str = Field(default="automatic")
    estimated_duration_minutes: int = Field(default=5)
    dependencies: list[UUID] = Field(default_factory=list, description="Prerequisite reviews")
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = Field(default=None)
    status: Literal["scheduled", "in_progress", "completed", "failed"] = Field(default="scheduled")


class SessionReviewAgent(BaseModel):
    """Configuration for the session review agent."""
    
    agent_id: str = Field(default="session_reviewer")
    agent_type: str = Field(default="specialized")
    capabilities: list[str] = Field(
        default=["action_extraction", "insight_generation", "summarization", "documentation"]
    )
    llm_config: dict = Field(default_factory=dict, description="Model configuration")
    prompt_templates: dict = Field(default_factory=dict, description="Custom prompt templates")
    max_context_tokens: int = Field(default=50000, description="Max tokens for review context")
    
    # Processing preferences
    extraction_depth: Literal["shallow", "medium", "deep"] = Field(default="medium")
    insight_types: list[str] = Field(
        default=["patterns", "decisions", "outcomes", "dependencies"]
    )
    documentation_style: Literal["concise", "detailed", "technical"] = Field(default="detailed")
    
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReviewTask(BaseModel):
    """Individual review task for the agent."""
    
    task_id: UUID = Field(default_factory=lambda: UUID())
    session_id: UUID
    window_range: tuple[int, int]
    window_index: int
    task_type: str = Field(default="full_review")
    priority: ReviewPriority = Field(default=ReviewPriority.MEDIUM)
    
    # Task parameters
    extract_actions: bool = Field(default=True)
    extract_insights: bool = Field(default=True)
    generate_summary: bool = Field(default=True)
    create_embeddings: bool = Field(default=True)
    
    # Constraints
    max_processing_time_minutes: int = Field(default=10)
    max_tokens_to_analyze: int = Field(default=20000)
    
    # Status tracking
    status: Literal["pending", "in_progress", "completed", "failed"] = Field(default="pending")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    
    # Results
    result_id: UUID | None = Field(default=None, description="Reference to SessionReviewResult")
    error_message: str | None = Field(default=None)


class ReviewExecutionContext(BaseModel):
    """Execution context for a review task."""
    
    task_id: UUID
    session_id: UUID
    window_range: tuple[int, int]
    
    # Context data
    session_messages: list[dict] = Field(default_factory=list)
    previous_reviews: list[UUID] = Field(default_factory=list)
    agent_capabilities: list[str] = Field(default_factory=list)
    
    # Processing constraints
    max_tokens: int = Field(default=20000)
    time_limit_minutes: int = Field(default=10)
    quality_threshold: float = Field(default=0.7)
    
    # Execution metadata
    execution_id: str = Field(default_factory=lambda: UUID())
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    environment: dict = Field(default_factory=dict)
    
    def get_window_size(self) -> int:
        """Get size of the window being reviewed."""
        return self.window_range[1] - self.window_range[0]
    
    def is_within_token_limit(self) -> bool:
        """Check if window is within processing limits."""
        return self.get_window_size() <= self.max_tokens
