"""Memory contracts for MindFlow backend.

Defines the core contracts for memory management, including storage,
retrieval, context windows, and agent memory operations.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


class MemoryType(StrEnum):
    """Type of memory storage."""
    
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    WORKING = "working"
    LONG_TERM = "long_term"


class MemoryStatus(StrEnum):
    """Status of memory operations."""
    
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"
    PROCESSING = "processing"


class RetrievalStrategy(StrEnum):
    """Strategy for memory retrieval."""
    
    SIMILARITY = "similarity"
    TEMPORAL = "temporal"
    HYBRID = "hybrid"
    KEYWORD = "keyword"


class MemoryRecallPolicy(StrEnum):
    """Recall policy exposed to orchestrator and tools."""

    ADAPTIVE = "adaptive"
    SESSION_ONLY = "session_only"
    CROSS_SESSION = "cross_session"


class MemoryRecallScope(StrEnum):
    """Search scope for memory recall."""

    CURRENT_SESSION = "current_session"
    CROSS_SESSION = "cross_session"
    CURRENT_THEN_CROSS = "current_then_cross"


class MemorySourceType(StrEnum):
    """Origin of retrieved memory context."""

    SESSION_MESSAGE = "session_message"
    SESSION_BLOCK = "session_block"
    SESSION_EMBEDDING = "session_embedding"
    AGENT_EVENT = "agent_event"
    AGENT_WINDOW = "agent_window"
    TASK_MEMORY = "task_memory"


class MemoryEntry(BaseModel):
    """Core memory entry contract.
    
    Represents a single memory entry with content, metadata,
    and embedding information.
    """
    
    id: UUID = Field(description="Unique memory entry identifier")
    session_id: UUID = Field(description="Session identifier")
    agent_id: str | None = Field(default=None, description="Agent identifier")
    content: str = Field(min_length=1, description="Memory content")
    memory_type: MemoryType = Field(default=MemoryType.EPISODIC, description="Type of memory")
    status: MemoryStatus = Field(default=MemoryStatus.ACTIVE, description="Memory status")
    
    # Temporal information
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")
    expires_at: datetime | None = Field(default=None, description="Expiration timestamp")
    
    # Token and position information
    token_start: int | None = Field(default=None, description="Start token position")
    token_end: int | None = Field(default=None, description="End token position")
    token_count: int = Field(description="Number of tokens in content")
    
    # Embedding information
    embedding: list[float] | None = Field(default=None, description="Vector embedding")
    embedding_model: str | None = Field(default=None, description="Embedding model used")
    
    # Metadata and relationships
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    parent_id: UUID | None = Field(default=None, description="Parent memory entry")
    related_ids: list[UUID] = Field(default_factory=list, description="Related memory entries")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class ContextWindow(BaseModel):
    """Context window contract.
    
    Represents a sliding window of context for memory operations.
    """
    
    id: UUID = Field(description="Context window identifier")
    session_id: UUID = Field(description="Session identifier")
    
    # Window boundaries
    start_token: int = Field(ge=0, description="Start token position")
    end_token: int = Field(ge=0, description="End token position")
    window_size: int = Field(gt=0, description="Window size in tokens")
    
    # Window content
    entries: list[MemoryEntry] = Field(description="Memory entries in window")
    summary: str | None = Field(default=None, description="Window summary")
    
    # Window metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")
    compression_ratio: float | None = Field(default=None, description="Compression ratio")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class MemoryCursor(BaseModel):
    """Memory cursor contract.
    
    Represents a cursor position within memory for navigation.
    """
    
    id: UUID = Field(description="Cursor identifier")
    session_id: UUID = Field(description="Session identifier")
    
    # Cursor position
    position: int = Field(ge=0, description="Current cursor position")
    anchor_token: int | None = Field(default=None, description="Anchor token position")
    
    # Cursor context
    context_window: int | None = Field(default=1000, description="Context window size")
    retrieval_strategy: RetrievalStrategy = Field(default=RetrievalStrategy.TEMPORAL)
    
    # Cursor metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class MemoryEvent(BaseModel):
    """Memory event contract.
    
    Represents events that occur in memory operations.
    """
    
    id: UUID = Field(description="Event identifier")
    session_id: UUID = Field(description="Session identifier")
    
    # Event information
    event_type: str = Field(description="Type of event")
    event_name: str = Field(description="Event name")
    description: str | None = Field(default=None, description="Event description")
    
    # Event data
    data: dict[str, Any] = Field(default_factory=dict, description="Event data")
    affected_entries: list[UUID] = Field(default_factory=list, description="Affected memory entries")
    
    # Event metadata
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    severity: str = Field(default="info", description="Event severity")
    source: str | None = Field(default=None, description="Event source")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class MemoryFact(BaseModel):
    """Memory fact contract.
    
    Represents factual information stored in memory.
    """
    
    id: UUID = Field(description="Fact identifier")
    session_id: UUID = Field(description="Session identifier")
    
    # Fact content
    fact: str = Field(min_length=1, description="Fact statement")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    
    # Fact classification
    category: str | None = Field(default=None, description="Fact category")
    tags: list[str] = Field(default_factory=list, description="Fact tags")
    
    # Fact metadata
    source: str | None = Field(default=None, description="Fact source")
    verified: bool = Field(default=False, description="Whether fact is verified")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class MemoryEmbedding(BaseModel):
    """Memory embedding contract.
    
    Represents embedding information for memory entries.
    """
    
    id: UUID = Field(description="Embedding identifier")
    memory_id: UUID = Field(description="Associated memory entry")
    
    # Embedding data
    vector: list[float] = Field(description="Embedding vector")
    dimension: int = Field(description="Vector dimension")
    model: str = Field(description="Embedding model used")
    
    # Embedding metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    version: str | None = Field(default=None, description="Model version")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Model parameters")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class MemoryRetrievalResult(BaseModel):
    """Result of a memory retrieval operation.

    Used by memory services when returning context to callers.
    """

    context: str = Field(description="Formatted context string ready to prepend to LLM messages")
    references: list[str] = Field(default_factory=list, description="Source references for the context")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional retrieval metadata")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


# ---------------------------------------------------------------------------
# Canonical facade contracts (Phase 1 — public surface)
# ---------------------------------------------------------------------------


class MemoryPersistResult(BaseModel):
    """Result returned by MemoryFacade.record_message().

    Provides just enough information for callers to track persistence outcomes
    without coupling them to internal storage details.
    """

    embedding_id: str | None = Field(default=None, description="ID of the stored embedding, if any")
    event_id: int | None = Field(default=None, description="ID of the stored AgentMemoryEvent row")
    stored: bool = Field(default=True, description="True when at least one memory backend accepted the write")
    chat_stored: bool = Field(
        default=False,
        description="True when the originating chat message was already normalized into chat_messages",
    )
    embedding_stored: bool = Field(
        default=False,
        description="True when a semantic session embedding was persisted",
    )
    agent_event_stored: bool = Field(
        default=False,
        description="True when the per-agent memory event row was persisted",
    )
    block_updated: bool = Field(
        default=False,
        description="True when a categorical session block was created or updated",
    )
    degraded_reason: str | None = Field(
        default=None,
        description="Operational degradation reason when a non-critical write path was skipped",
    )
    indexable: bool = Field(
        default=True,
        description="Whether the content was eligible for semantic indexing",
    )
    skipped_reasons: list[str] = Field(
        default_factory=list,
        description="Reasons why semantic indexing paths were skipped or degraded",
    )
    was_deduplicated: bool = Field(default=False, description="True when the message was skipped as a duplicate")
    token_count: int = Field(default=0, description="Estimated token count of the recorded content")


class SessionBlockSchema(BaseModel):
    """Canonical categorical block for a session."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: int | None = None
    session_id: str
    sequence: int
    category: str
    title: str
    summary_md: str
    content_excerpt: str
    topic_tags: list[str] = Field(default_factory=list)
    message_start_id: int
    message_end_id: int
    token_count: int
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    source: str = "inferred"
    indexable: bool = True
    content_kind: str = "answer"
    quality_flags: list[str] = Field(default_factory=list)
    source_status: str = "final"
    derived_from_recall: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
    closed_at: datetime | None = None


class MemoryRecallHit(BaseModel):
    """Structured recall hit returned by semantic memory recall."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    source_type: MemorySourceType | str = MemorySourceType.SESSION_MESSAGE
    source_id: int | None = None
    session_id: str | None = None
    agent_id: str | None = None
    content: str = ""
    score: float = 0.0
    final_score: float = 0.0
    reference: str | None = None
    category: str | None = None
    title: str | None = None
    summary_md: str | None = None
    content_excerpt: str | None = None
    topic_tags: list[str] = Field(default_factory=list)
    role: str | None = None
    content_kind: str = "query"
    quality_flags: list[str] = Field(default_factory=list)
    source_status: str = "final"
    derived_from_recall: bool = False
    answer_bearing: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _normalize_hit(self) -> MemoryRecallHit:
        if not self.content:
            self.content = self.content_excerpt or self.summary_md or ""
        if self.final_score == 0.0:
            self.final_score = self.score
        if not self.reference and self.source_id is not None:
            self.reference = f"{self.source_type}:{self.source_id}"
        if self.content_kind == "answer" or str(self.source_type) == MemorySourceType.SESSION_BLOCK.value:
            self.answer_bearing = True
        return self


class SessionBlockHit(MemoryRecallHit):
    """Typed convenience schema for session-block recall hits."""

    source_type: MemorySourceType | str = MemorySourceType.SESSION_BLOCK


class MemoryRecallRequest(BaseModel):
    """Request payload for MemoryFacade.recall()."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    session_id: str = Field(description="Session to search within")
    agent_id: str = Field(description="Agent whose memory to query")
    query: str = Field(description="Natural-language retrieval query")
    top_k: int = Field(
        default=4,
        ge=1,
        description="Maximum number of hits to return",
        validation_alias=AliasChoices("top_k", "max_results"),
    )
    cross_session: bool = Field(default=False, description="Whether to search across all sessions")
    min_score: float = Field(default=0.35, ge=0.0, le=1.0, description="Minimum similarity score")
    policy: MemoryRecallPolicy = Field(
        default=MemoryRecallPolicy.ADAPTIVE,
        description="Recall policy for orchestrator-driven retrieval",
    )
    scope: MemoryRecallScope = Field(
        default=MemoryRecallScope.CURRENT_THEN_CROSS,
        description="Requested search scope",
    )
    category_filters: list[str] = Field(
        default_factory=list,
        description="Optional categorical filters used when recalling session blocks",
    )
    include_messages: bool = Field(default=True, description="Whether message-level semantic hits are allowed")
    include_blocks: bool = Field(default=True, description="Whether categorical session block hits are allowed")
    top_k_messages: int = Field(default=4, ge=0, description="Maximum message hits to return")
    top_k_blocks: int = Field(default=2, ge=0, description="Maximum session block hits to return")
    cross_session_fallback: bool = Field(default=True, description="Whether adaptive recall may fallback cross-session")
    cross_session_min_hits: int = Field(default=2, ge=1, description="Minimum session hits before fallback is skipped")
    fallback_score_threshold: float = Field(
        default=0.55,
        ge=0.0,
        le=1.0,
        description="Fallback threshold applied to the best score during adaptive recall",
    )
    exclude_session_id: str | None = Field(
        default=None,
        description="Optional session to exclude when searching across sessions",
    )

    @property
    def max_results(self) -> int:
        """Backward-compatible alias used by some callers."""
        return self.top_k

    @model_validator(mode="after")
    def _sync_limits(self) -> MemoryRecallRequest:
        if self.top_k_messages == 0 and self.include_messages:
            self.top_k_messages = self.top_k
        if self.top_k_blocks == 0 and self.include_blocks:
            self.top_k_blocks = min(self.top_k, 2)
        if self.scope == MemoryRecallScope.CROSS_SESSION:
            self.cross_session = True
        return self


class MemoryRecallResponse(BaseModel):
    """Response from MemoryFacade.recall().

    This is the *primary* contract for retrieved context consumed by agents.
    schemas.session.contracts.RetrievedContext is a backward-compat alias.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    context: str = Field(
        default="",
        description="Formatted context ready to inject into an LLM prompt",
        validation_alias=AliasChoices("context", "content"),
    )
    references: list[str] = Field(default_factory=list, description="Source references (type:id)")
    hit_count: int = Field(default=0, description="Number of retrieval hits before formatting")
    hits: list[MemoryRecallHit] = Field(default_factory=list, description="Structured retrieval hits")
    best_score: float = Field(default=0.0, description="Highest score among returned hits")
    grounding_recommended: bool = Field(
        default=False,
        description="Whether the caller should prefer a memory-grounded answer before tool use",
    )
    filtered_hits_count: int = Field(
        default=0,
        description="How many candidate hits were filtered out before final formatting",
    )
    scope_used: MemoryRecallScope = Field(
        default=MemoryRecallScope.CURRENT_SESSION,
        description="Effective scope used to answer the recall request",
    )
    fallback_used: bool = Field(default=False, description="Whether cross-session fallback was used")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional retrieval metadata")

    @property
    def content(self) -> str:
        """Backward-compatible alias for older callers."""
        return self.context

    @property
    def message_hits(self) -> list[MemoryRecallHit]:
        allowed = {
            MemorySourceType.SESSION_MESSAGE.value,
            MemorySourceType.SESSION_EMBEDDING.value,
        }
        return [hit for hit in self.hits if str(hit.source_type) in allowed]

    @property
    def block_hits(self) -> list[MemoryRecallHit]:
        return [
            hit
            for hit in self.hits
            if str(hit.source_type) == MemorySourceType.SESSION_BLOCK.value
        ]

    @property
    def crossed_session(self) -> bool:
        """Backward-compatible alias used by older orchestrator shims."""
        return self.fallback_used or self.scope_used == MemoryRecallScope.CROSS_SESSION

    @model_validator(mode="after")
    def _derive_summary_fields(self) -> MemoryRecallResponse:
        if self.hit_count == 0 and self.hits:
            self.hit_count = len(self.hits)
        if self.best_score == 0.0 and self.hits:
            self.best_score = max(float(hit.score) for hit in self.hits)
        if not self.grounding_recommended and self.hits:
            self.grounding_recommended = (
                self.best_score >= 0.72
                or any(bool(hit.answer_bearing) for hit in self.hits)
            )
        if not self.references and self.hits:
            derived_refs = [str(hit.reference) for hit in self.hits if hit.reference]
            if derived_refs:
                self.references = derived_refs
        return self


class AgentMemorySnapshot(BaseModel):
    """Snapshot of an agent's memory state for context injection.

    Returned by MemoryFacade.get_agent_snapshot().
    """

    session_id: str = Field(description="Session identifier")
    agent_id: str = Field(description="Agent identifier")
    event_count: int = Field(default=0, description="Total recorded events for this agent/session")
    window_count: int = Field(default=0, description="Number of summarised windows")
    total_tokens: int = Field(default=0, description="Cumulative token count (from cursor)")
    context_summary: str = Field(default="", description="Latest extractive window summary, or empty")
    events: list[dict[str, Any]] = Field(default_factory=list, description="Raw memory events when requested")
    windows: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of window metadata dicts (window_index, summary_md, key_points)",
    )

    @property
    def token_total(self) -> int:
        """Backward-compatible alias used by shim callers."""
        return self.total_tokens


# Export all contracts
__all__ = [
    "MemoryType",
    "MemoryStatus",
    "RetrievalStrategy",
    "MemoryEntry",
    "ContextWindow",
    "MemoryCursor",
    "MemoryEvent",
    "MemoryFact",
    "MemoryEmbedding",
    "MemoryRetrievalResult",
    "MemoryRecallPolicy",
    "MemoryRecallScope",
    "MemorySourceType",
    "SessionBlockSchema",
    "MemoryRecallHit",
    "SessionBlockHit",
    # Canonical facade contracts
    "MemoryPersistResult",
    "MemoryRecallRequest",
    "MemoryRecallResponse",
    "AgentMemorySnapshot",
]
