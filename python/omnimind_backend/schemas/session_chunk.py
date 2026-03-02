"""Session chunk schemas for context segmentation and retrieval."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class ChunkType(StrEnum):
    """Content classification for session chunks."""

    PLANNING = "planning"
    IMPLEMENTATION = "implementation"
    RESEARCH = "research"
    REVIEW = "review"
    DISCUSSION = "discussion"
    META = "meta"


class ChunkEdgeType(StrEnum):
    """Relationship types between chunks in the session canvas."""

    FOLLOWS = "follows"
    REFERENCES = "references"
    SUPERSEDES = "supersedes"
    DEPENDS_ON = "depends_on"


class ChunkMetadata(BaseModel):
    """Metadata for a single session context chunk."""

    chunk_id: UUID
    session_id: str
    agent_id: str
    sequence: int
    token_count: int = 0
    start_turn: int = 0
    end_turn: int = 0
    topic_tags: list[str] = Field(default_factory=list)
    summary: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    freshness: float = Field(default=1.0, ge=0.0, le=1.0)
    chunk_type: ChunkType = ChunkType.DISCUSSION
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ChunkEdge(BaseModel):
    """An edge between two chunks in the session canvas graph."""

    source_chunk_id: UUID
    target_chunk_id: UUID
    edge_type: ChunkEdgeType


class ChunkRetrievalQuery(BaseModel):
    """Query parameters for retrieving session chunks."""

    session_id: str
    by_range: tuple[int, int] | None = None
    by_topic: list[str] | None = None
    by_agent: str | None = None
    by_recency: int | None = None
    limit: int = 10
    min_score: float = 0.3
