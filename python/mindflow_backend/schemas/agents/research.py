"""Research-specific data contracts and enums.

Defines the vocabulary for research operations: iteration types,
source classifications, confidence levels, and research-specific
models for browser automation and result synthesis.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class IterationType(StrEnum):
    """Types of browser actions during research execution."""
    
    BROWSER_CREATE = "browser_create"
    NAVIGATE = "navigate"
    SEARCH = "search"
    EXTRACT = "extract"
    CLICK = "click"
    FILL = "fill"
    PRESS = "press"
    SNAPSHOT = "snapshot"
    SYNTHESIZE = "synthesize"
    CLEANUP = "cleanup"


class SourceType(StrEnum):
    """Classification of research sources by trust level."""
    
    OFFICIAL = "official"          # Official docs, APIs, .gov
    ACADEMIC = "academic"          # .edu, arxiv, scholarly
    REPUTABLE_COMMUNITY = "reputable_community"  # StackOverflow, GitHub
    TECH_PUBLICATION = "tech_publication"  # Medium, Dev.to, CSS-Tricks
    UNKNOWN_BLOG = "unknown_blog"   # Personal blogs, generic articles
    SOCIAL = "social"              # Twitter, Reddit, HN (signal only)


class QuestionType(StrEnum):
    """Classification of research questions for query planning."""
    
    DEFINITION = "definition"       # "What is X?"
    TUTORIAL = "tutorial"           # "How to do X?"
    COMPARISON = "comparison"       # "X vs Y?"
    CURRENT_STATE = "current_state" # "What is the latest on X?"
    DEBUG = "debug"                 # "Why does X fail?"
    INFORMATIONAL_DATA = "informational_data"  # "What are the stats on X?"
    DOCUMENTATION = "documentation" # "API/reference for X"
    GENERAL = "general"             # Open-ended


class ConfidenceLevel(StrEnum):
    """Confidence levels for research findings."""
    
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class ResearchStatus(StrEnum):
    """Status of research operations."""
    
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class BrowserAction(BaseModel):
    """Single browser action with metadata."""
    
    browser_id: str
    iteration_type: IterationType
    timestamp: str
    action_data: dict = Field(default_factory=dict)
    success: bool = True
    error_message: str | None = None
    duration_ms: int | None = None


class QueryIntent(BaseModel):
    """Intent analysis result for query planning."""
    
    question_type: QuestionType
    complexity_level: Literal["simple", "moderate", "complex", "deep"]
    browser_count: int = Field(ge=1, le=10)
    target_sources: list[SourceType] = Field(default_factory=list)
    requires_deep_navigation: bool = False
    estimated_duration_seconds: int = Field(default=60)


class QueryPlan(BaseModel):
    """Research query plan with multiple query variants."""
    
    intent: QueryIntent
    queries: list[str] = Field(min_length=1)
    search_engines: list[str] = Field(default_factory=lambda: ["google.com"])
    max_results_per_browser: int = Field(default=3, ge=1, le=10)
    parallel_execution: bool = True


class SourceClassification(BaseModel):
    """Classification result for a research source."""
    
    url: str
    source_type: SourceType
    trust_level: ConfidenceLevel
    domain_authority: float = Field(ge=0.0, le=1.0)
    content_type: str | None = None
    last_updated: str | None = None


class ResearchFinding(BaseModel):
    """Individual research finding with metadata."""
    
    source_url: str
    source_classification: SourceClassification
    content_summary: str
    key_points: list[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0)
    relevance_score: float = Field(ge=0.0, le=1.0)
    extraction_method: str = "text_extraction"
    conflicts_with: list[str] = Field(default_factory=list)  # URLs that conflict


class ResearchResult(BaseModel):
    """Complete research result with synthesis."""
    
    session_id: str
    original_query: str
    question_type: QuestionType
    browsers_used: int
    findings: list[ResearchFinding]
    synthesis_summary: str
    confidence_level: ConfidenceLevel
    conflicts_identified: list[dict] = Field(default_factory=list)
    gaps_identified: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    total_duration_seconds: int
    action_trail: list[BrowserAction] = Field(default_factory=list)


class BrowserSession(BaseModel):
    """Browser session state tracking."""
    
    browser_id: str
    instance_id: str
    tab_id: str
    current_url: str | None = None
    status: ResearchStatus = ResearchStatus.PENDING
    created_at: str
    last_activity: str
    actions_completed: int = 0
    error_count: int = 0


class ResearchConfig(BaseModel):
    """Configuration for research operations."""
    
    max_concurrent_browsers: int = Field(default=5, ge=1, le=10)
    default_timeout_seconds: int = Field(default=30, ge=10, le=120)
    retry_attempts: int = Field(default=2, ge=0, le=5)
    enable_stealth_mode: bool = True
    headless_mode: bool = True
    preferred_search_engines: list[str] = Field(
        default_factory=lambda: ["google.com", "duckduckgo.com", "brave.com"]
    )
    token_efficiency_target: int = Field(default=800, ge=400, le=2000)  # tokens per page


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------

class ResearchRequest(BaseModel):
    """Request model for research operations."""
    
    query: str = Field(min_length=3, max_length=1000)
    session_id: str
    agent_id: str
    config: ResearchConfig | None = None
    force_browser_search: bool = False


class ResearchResponse(BaseModel):
    """Response model for research operations."""
    
    success: bool
    result: ResearchResult | None = None
    error_message: str | None = None
    execution_summary: dict = Field(default_factory=dict)


class BrowserActionRequest(BaseModel):
    """Request model for individual browser actions."""
    
    browser_id: str
    iteration_type: IterationType
    action_data: dict = Field(default_factory=dict)
    timeout_seconds: int | None = None


class BrowserActionResponse(BaseModel):
    """Response model for browser action results."""
    
    success: bool
    browser_id: str
    iteration_type: IterationType
    result_data: dict = Field(default_factory=dict)
    error_message: str | None = None
    duration_ms: int | None = None
