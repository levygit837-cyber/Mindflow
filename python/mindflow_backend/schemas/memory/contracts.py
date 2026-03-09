"""Memory contracts for MindFlow backend.

Defines the core contracts for memory management, including storage,
retrieval, context windows, and agent memory operations.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from pydantic import BaseModel, Field


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


class MemoryEntry(BaseModel):
    """Core memory entry contract.
    
    Represents a single memory entry with content, metadata,
    and embedding information.
    """
    
    id: UUID = Field(description="Unique memory entry identifier")
    session_id: UUID = Field(description="Session identifier")
    agent_id: Optional[str] = Field(default=None, description="Agent identifier")
    content: str = Field(min_length=1, description="Memory content")
    memory_type: MemoryType = Field(default=MemoryType.EPISODIC, description="Type of memory")
    status: MemoryStatus = Field(default=MemoryStatus.ACTIVE, description="Memory status")
    
    # Temporal information
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    expires_at: Optional[datetime] = Field(default=None, description="Expiration timestamp")
    
    # Token and position information
    token_start: Optional[int] = Field(default=None, description="Start token position")
    token_end: Optional[int] = Field(default=None, description="End token position")
    token_count: int = Field(description="Number of tokens in content")
    
    # Embedding information
    embedding: Optional[List[float]] = Field(default=None, description="Vector embedding")
    embedding_model: Optional[str] = Field(default=None, description="Embedding model used")
    
    # Metadata and relationships
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    parent_id: Optional[UUID] = Field(default=None, description="Parent memory entry")
    related_ids: List[UUID] = Field(default_factory=list, description="Related memory entries")
    
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
    entries: List[MemoryEntry] = Field(description="Memory entries in window")
    summary: Optional[str] = Field(default=None, description="Window summary")
    
    # Window metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    compression_ratio: Optional[float] = Field(default=None, description="Compression ratio")
    
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
    anchor_token: Optional[int] = Field(default=None, description="Anchor token position")
    
    # Cursor context
    context_window: Optional[int] = Field(default=1000, description="Context window size")
    retrieval_strategy: RetrievalStrategy = Field(default=RetrievalStrategy.TEMPORAL)
    
    # Cursor metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
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
    description: Optional[str] = Field(default=None, description="Event description")
    
    # Event data
    data: Dict[str, Any] = Field(default_factory=dict, description="Event data")
    affected_entries: List[UUID] = Field(default_factory=list, description="Affected memory entries")
    
    # Event metadata
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    severity: str = Field(default="info", description="Event severity")
    source: Optional[str] = Field(default=None, description="Event source")
    
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
    category: Optional[str] = Field(default=None, description="Fact category")
    tags: List[str] = Field(default_factory=list, description="Fact tags")
    
    # Fact metadata
    source: Optional[str] = Field(default=None, description="Fact source")
    verified: bool = Field(default=False, description="Whether fact is verified")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    
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
    vector: List[float] = Field(description="Embedding vector")
    dimension: int = Field(description="Vector dimension")
    model: str = Field(description="Embedding model used")
    
    # Embedding metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    version: Optional[str] = Field(default=None, description="Model version")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Model parameters")
    
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
    references: List[str] = Field(default_factory=list, description="Source references for the context")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional retrieval metadata")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


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
]
