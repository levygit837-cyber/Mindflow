"""Session contracts for context governance.

Defines the core contracts for session management, context retrieval,
and summarization in the context governance system.

Note on RetrievedContext
------------------------
``RetrievedContext`` is a **backward-compatibility alias** for
``mindflow_backend.schemas.memory.contracts.MemoryRecallResponse``.
New code must use ``MemoryRecallResponse`` directly.
Existing callers that import ``RetrievedContext`` continue to work
without modification.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from mindflow_backend.schemas.memory.contracts import MemoryRecallResponse


class SessionMode(StrEnum):
    """Session execution mode."""
    
    NORMAL = "normal"
    BATCH = "batch"


class RelationshipType(StrEnum):
    """Relationship type between sessions."""
    
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    DEPENDENCY = "dependency"


class RetrievalMode(StrEnum):
    """Context retrieval mode."""
    
    RANGE = "range"
    TOPIC = "topic"
    SEMANTIC = "semantic"


class SessionReview(BaseModel):
    """Main execution session contract.
    
    Represents a complete session with token ranges, execution windows,
    and hierarchical relationships.
    """
    
    session_id: UUID
    main_session_id: UUID = Field(description="Self-reference for root sessions")
    token_range: str = Field(example="0-10k", description="Human-readable token range")
    execution_window: tuple[int, int] = Field(example=(0, 10000), description="Execution token boundaries")
    context_window: tuple[int, int] = Field(example=(0, 100000), description="Analysis token boundaries")
    mode: SessionMode = Field(default=SessionMode.NORMAL)
    parent_session_id: UUID | None = Field(default=None, description="Parent session reference")
    child_sessions: list[UUID] = Field(default_factory=list, description="Child session references")
    current_window_position: int = Field(default=0, description="Current execution window index")
    total_tokens_processed: int = Field(default=0, description="Total tokens in this session")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict = Field(default_factory=dict, description="Additional session metadata")


class SubSessionReview(BaseModel):
    """Child session contract for sub-sessions of main reviews.
    
    Represents a sub-session within a parent SessionReview,
    with specific token sub-ranges and relationship types.
    """
    
    session_id: UUID
    parent_session_id: UUID = Field(description="References parent SessionReview")
    main_session_id: UUID = Field(description="Root session reference")
    token_sub_range: str = Field(example="30k-60k", description="Token range within parent")
    execution_window: tuple[int, int] = Field(example=(30000, 60000))
    relationship_type: RelationshipType = Field(default=RelationshipType.SEQUENTIAL)
    dependency_order: int | None = Field(default=None, description="Order for dependency relationships")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict = Field(default_factory=dict)


class SessionRetriever(BaseModel):
    """Context window access contract.
    
    Defines parameters for retrieving context from specific
    token ranges and sessions.
    """
    
    retriever_id: UUID
    session_id: UUID
    context_window: tuple[int, int] = Field(example=(0, 100000), description="Context analysis window")
    retrieval_query: str = Field(default="", description="Query for semantic retrieval")
    retrieval_mode: RetrievalMode = Field(default=RetrievalMode.RANGE)
    included_sessions: list[UUID] = Field(default_factory=list)
    excluded_sessions: list[UUID] = Field(default_factory=list)
    max_results: int = Field(default=10, description="Maximum results to return")
    min_relevance_score: float = Field(default=0.3, description="Minimum relevance threshold")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SummarizationReview(BaseModel):
    """Analysis results contract for SessionRetriever.
    
    Contains the results of context analysis including
    summaries, insights, and related session information.
    """
    
    review_id: UUID
    session_retriever_id: UUID
    context_summary: str = Field(description="Generated context summary")
    files_analyzed: list[str] = Field(default_factory=list, description="Files included in analysis")
    writes_detected: list[str] = Field(default_factory=list, description="Write operations detected")
    goal_achievement: float = Field(default=0.0, ge=0.0, le=1.0, description="Goal achievement score")
    description: str = Field(description="Analysis description")
    related_sessions: list[UUID] = Field(default_factory=list, description="Related session IDs")
    key_insights: list[str] = Field(default_factory=list, description="Key insights from analysis")
    action_items: list[str] = Field(default_factory=list, description="Recommended action items")
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Analysis confidence")
    token_coverage: float = Field(default=1.0, ge=0.0, le=1.0, description="Token coverage ratio")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ContextWindowInfo(BaseModel):
    """Information about current and adjacent token windows."""
    
    current_window: tuple[int, int] = Field(example=(83000, 93000))
    current_window_index: int = Field(example=8)
    previous_window: tuple[int, int] | None = Field(example=(73000, 83000))
    next_window: tuple[int, int] | None = Field(example=(93000, 103000))
    window_size: int = Field(example=10000)
    total_tokens: int = Field(example=150000)
    progress_percentage: float = Field(example=0.553, description="Progress through total tokens")


class ContextControlResult(BaseModel):
    """Result from context_control_arch function."""
    
    action_taken: Literal["none", "session_created", "window_advanced", "context_summarized"]
    session_review: SessionReview | None = None
    sub_session_review: SubSessionReview | None = None
    window_info: ContextWindowInfo
    tokens_processed: int
    message: str = Field(default="")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# Backward-compatibility alias.  The primary contract lives in
# mindflow_backend.schemas.memory.contracts.MemoryRecallResponse.
RetrievedContext = MemoryRecallResponse
