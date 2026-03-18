"""Session review schemas with backward-compatible runtime contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReviewPriority(StrEnum):
    """Priority level for review tasks."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReviewTaskType(StrEnum):
    """Known review task types."""

    CONTEXT_REVIEW = "context_review"
    QUALITY_ASSESSMENT = "quality_assessment"
    PERFORMANCE_ANALYSIS = "performance_analysis"
    ERROR_DETECTION = "error_detection"
    OPTIMIZATION = "optimization"
    MANUAL_REVIEW = "manual_review"
    AUTOMATIC_THRESHOLD = "automatic_threshold"
    SESSION_REVIEW_REQUESTED = "session_review.requested"


class ReviewTriggerType(StrEnum):
    """Type of review trigger."""

    AUTOMATIC = "automatic"
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    EVENT_BASED = "event_based"
    TOKEN_THRESHOLD = "token_threshold"


class WindowSize(StrEnum):
    """Logical token window presets for session review."""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    EXTRA_LARGE = "extra_large"
    CUSTOM = "custom"


class SessionReviewConfig(BaseModel):
    """Configuration of a tracked review session."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    window_size: WindowSize
    custom_window_tokens: int | None = None
    trigger_type: ReviewTriggerType = ReviewTriggerType.TOKEN_THRESHOLD
    trigger_threshold: int
    enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TokenWindowTracker(BaseModel):
    """In-memory tracker of token progress for a session."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    window_size: int
    current_window: int = 0
    windows_completed: int = 0
    total_tokens_processed: int = 0
    tokens_in_current_window: int = 0
    next_review_threshold: int | None = None
    last_review_at: datetime | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def populate_threshold(self) -> "TokenWindowTracker":
        if self.next_review_threshold is None:
            self.next_review_threshold = self.window_size
        return self

    @property
    def tokens_until_next_review(self) -> int:
        threshold = self.next_review_threshold or self.window_size
        return max(0, threshold - self.tokens_in_current_window)

    def should_trigger_review(self, threshold: int | None = None) -> bool:
        review_threshold = threshold or self.next_review_threshold or self.window_size
        return self.tokens_in_current_window >= review_threshold

    def get_current_window_bounds(self) -> tuple[int, int]:
        return self.get_window_bounds(self.current_window)

    def get_window_bounds(self, window_index: int) -> tuple[int, int]:
        window_start = window_index * self.window_size
        return (window_start, window_start + self.window_size)

    def advance_to_next_window(self) -> tuple[int, int]:
        self.current_window += 1
        self.windows_completed += 1
        self.tokens_in_current_window = 0
        self.updated_at = datetime.now(UTC)
        return self.get_current_window_bounds()


class WindowProgressInfo(BaseModel):
    """Progress view returned by the session review service."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    current_window: tuple[int, int]
    window_index: int
    progress_in_window: float
    overall_progress: float
    tokens_until_next_review: int
    estimated_next_review: datetime
    windows_remaining: int


class ReviewTask(BaseModel):
    """Review task definition used by the service and workers."""

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    window_range: tuple[int, int] = (0, 0)
    window_index: int = 0
    task_type: str = ReviewTaskType.CONTEXT_REVIEW.value
    priority: ReviewPriority = ReviewPriority.MEDIUM
    trigger_type: ReviewTriggerType = ReviewTriggerType.AUTOMATIC
    title: str = "Session review"
    description: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    max_tokens_to_analyze: int = 10_000
    max_processing_time_minutes: int = 10
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    scheduled_for: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: str = "pending"
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    result: dict[str, Any] | None = None
    issues_found: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

    @property
    def id(self) -> str:
        return self.task_id


class ReviewExecutionContext(BaseModel):
    """Context consumed by the review agent."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    task_id: str
    window_range: tuple[int, int]
    session_messages: list[dict[str, Any]] = Field(default_factory=list)
    agent_capabilities: list[str] = Field(default_factory=list)
    max_tokens: int = 10_000
    time_limit_minutes: int = 10
    quality_threshold: float = 0.7
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def window_start(self) -> int:
        return self.window_range[0]

    @property
    def window_end(self) -> int:
        return self.window_range[1]

    @property
    def window_size(self) -> int:
        return max(0, self.window_end - self.window_start)

    @property
    def messages(self) -> list[dict[str, Any]]:
        return self.session_messages


class SessionReviewResult(BaseModel):
    """Persistable result of a session review window."""

    model_config = ConfigDict(extra="forbid")

    review_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    window_range: tuple[int, int]
    priority: ReviewPriority = ReviewPriority.MEDIUM
    summary_text: str = ""
    actions_documented: list[str] = Field(default_factory=list)
    insights_extracted: list[str] = Field(default_factory=list)
    review_data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def populate_review_data(self) -> "SessionReviewResult":
        if not self.review_data:
            self.review_data = {
                "summary_text": self.summary_text,
                "actions_documented": list(self.actions_documented),
                "insights_extracted": list(self.insights_extracted),
            }
        if not self.summary_text:
            self.summary_text = str(self.review_data.get("summary_text", ""))
        return self


ReviewResult = SessionReviewResult


class ReviewSession(BaseModel):
    """Aggregate of review tasks for a session window."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    window_start: int
    window_end: int
    window_size: int
    tasks: list[ReviewTask] = Field(default_factory=list)
    completed_tasks: list[ReviewTask] = Field(default_factory=list)
    status: str = "active"
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    total_issues: int = 0
    critical_issues: int = 0
    recommendations_count: int = 0


__all__ = [
    "ReviewPriority",
    "ReviewTaskType",
    "ReviewTriggerType",
    "WindowSize",
    "SessionReviewConfig",
    "TokenWindowTracker",
    "WindowProgressInfo",
    "ReviewTask",
    "ReviewExecutionContext",
    "SessionReviewResult",
    "ReviewResult",
    "ReviewSession",
]
