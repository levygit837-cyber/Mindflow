"""Memory request schemas for MindFlow backend.

Provides request schemas for all memory operations including storage,
retrieval, search, and management operations.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, validator

from .contracts import MemoryType, RetrievalStrategy


class MemoryStoreRequest(BaseModel):
    """Request schema for storing memory entries."""
    
    session_id: UUID = Field(description="Session identifier")
    agent_id: str | None = Field(default=None, description="Agent identifier")
    content: str = Field(min_length=1, max_length=100000, description="Memory content")
    memory_type: MemoryType = Field(default=MemoryType.EPISODIC, description="Type of memory")
    
    # Optional positioning
    token_start: int | None = Field(default=None, ge=0, description="Start token position")
    token_end: int | None = Field(default=None, ge=0, description="End token position")
    
    # Metadata and relationships
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    parent_id: UUID | None = Field(default=None, description="Parent memory entry")
    tags: list[str] = Field(default_factory=list, description="Memory tags")
    
    # Embedding options
    generate_embedding: bool = Field(default=True, description="Whether to generate embedding")
    embedding_model: str | None = Field(default=None, description="Specific embedding model")
    
    # Expiration
    expires_at: datetime | None = Field(default=None, description="Expiration timestamp")
    
    @validator('token_end')
    def validate_token_range(cls, v, values):
        """Validate token range is logical."""
        if v is not None and 'token_start' in values and values['token_start'] is not None:
            if v <= values['token_start']:
                raise ValueError('token_end must be greater than token_start')
        return v


class MemoryRetrieveRequest(BaseModel):
    """Request schema for retrieving memory entries."""
    
    session_id: UUID = Field(description="Session identifier")
    memory_ids: list[UUID] | None = Field(default=None, description="Specific memory IDs to retrieve")
    
    # Retrieval filters
    memory_type: MemoryType | None = Field(default=None, description="Filter by memory type")
    agent_id: str | None = Field(default=None, description="Filter by agent")
    tags: list[str] | None = Field(default=None, description="Filter by tags")
    
    # Temporal filters
    created_after: datetime | None = Field(default=None, description="Filter by creation date")
    created_before: datetime | None = Field(default=None, description="Filter by creation date")
    
    # Token range
    token_start: int | None = Field(default=None, ge=0, description="Start token position")
    token_end: int | None = Field(default=None, ge=0, description="End token position")
    
    # Pagination and ordering
    limit: int = Field(default=50, ge=1, le=1000, description="Maximum results")
    offset: int = Field(default=0, ge=0, description="Results offset")
    order_by: str = Field(default="created_at", description="Order field")
    order_direction: str = Field(default="desc", pattern="^(asc|desc)$", description="Order direction")
    
    # Content options
    include_content: bool = Field(default=True, description="Include memory content")
    include_embeddings: bool = Field(default=False, description="Include embeddings")
    include_metadata: bool = Field(default=True, description="Include metadata")


class MemorySearchRequest(BaseModel):
    """Request schema for searching memory entries."""
    
    query: str = Field(min_length=1, max_length=1000, description="Search query")
    session_id: UUID | None = Field(default=None, description="Optional session filter")
    
    # Search configuration
    retrieval_strategy: RetrievalStrategy = Field(default=RetrievalStrategy.HYBRID)
    limit: int = Field(default=10, ge=1, le=100, description="Maximum results")
    threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Similarity threshold")
    
    # Search filters
    memory_type: MemoryType | None = Field(default=None, description="Filter by memory type")
    agent_id: str | None = Field(default=None, description="Filter by agent")
    tags: list[str] | None = Field(default=None, description="Filter by tags")
    
    # Temporal constraints
    created_after: datetime | None = Field(default=None, description="Filter by creation date")
    created_before: datetime | None = Field(default=None, description="Filter by creation date")
    
    # Search options
    include_content: bool = Field(default=True, description="Include memory content")
    include_metadata: bool = Field(default=True, description="Include metadata")
    highlight_matches: bool = Field(default=False, description="Highlight query matches")


class MemoryUpdateRequest(BaseModel):
    """Request schema for updating memory entries."""
    
    memory_id: UUID = Field(description="Memory entry identifier")
    
    # Updatable fields
    content: str | None = Field(default=None, min_length=1, description="Updated content")
    memory_type: MemoryType | None = Field(default=None, description="Updated memory type")
    metadata: dict[str, Any] | None = Field(default=None, description="Updated metadata")
    tags: list[str] | None = Field(default=None, description="Updated tags")
    
    # Position updates
    token_start: int | None = Field(default=None, ge=0, description="Updated start position")
    token_end: int | None = Field(default=None, ge=0, description="Updated end position")
    
    # Relationship updates
    parent_id: UUID | None = Field(default=None, description="Updated parent")
    related_ids: list[UUID] | None = Field(default=None, description="Updated relationships")
    
    # Expiration
    expires_at: datetime | None = Field(default=None, description="Updated expiration")
    
    # Embedding options
    regenerate_embedding: bool = Field(default=False, description="Whether to regenerate embedding")
    embedding_model: str | None = Field(default=None, description="New embedding model")


class MemoryDeleteRequest(BaseModel):
    """Request schema for deleting memory entries."""
    
    memory_ids: list[UUID] = Field(min_items=1, description="Memory IDs to delete")
    soft_delete: bool = Field(default=True, description="Whether to soft delete")
    reason: str | None = Field(default=None, description="Deletion reason")


class ContextWindowRequest(BaseModel):
    """Request schema for context window operations."""
    
    session_id: UUID = Field(description="Session identifier")
    
    # Window configuration
    window_size: int = Field(default=1000, ge=1, le=10000, description="Window size in tokens")
    position: int | None = Field(default=None, ge=0, description="Center position for window")
    
    # Window type
    window_type: str = Field(default="sliding", pattern="^(sliding|fixed|expanding)$", description="Window type")
    
    # Content options
    include_embeddings: bool = Field(default=False, description="Include embeddings")
    include_metadata: bool = Field(default=True, description="Include metadata")
    compress_content: bool = Field(default=False, description="Compress window content")
    
    # Retrieval options
    retrieval_strategy: RetrievalStrategy = Field(default=RetrievalStrategy.TEMPORAL)
    memory_types: list[MemoryType] | None = Field(default=None, description="Memory types to include")


class MemoryCursorRequest(BaseModel):
    """Request schema for memory cursor operations."""
    
    session_id: UUID = Field(description="Session identifier")
    
    # Cursor operations
    operation: str = Field(pattern="^(get|set|move|reset)$", description="Cursor operation")
    position: int | None = Field(default=None, ge=0, description="Cursor position")
    anchor_token: int | None = Field(default=None, ge=0, description="Anchor token")
    
    # Context options
    context_window: int | None = Field(default=None, ge=1, le=10000, description="Context window size")
    retrieval_strategy: RetrievalStrategy = Field(default=RetrievalStrategy.TEMPORAL)
    
    # Movement parameters (for move operation)
    direction: str | None = Field(default=None, pattern="^(forward|backward)$", description="Move direction")
    distance: int | None = Field(default=None, ge=1, description="Move distance")


class MemoryStatsRequest(BaseModel):
    """Request schema for memory statistics."""
    
    session_id: UUID | None = Field(default=None, description="Optional session filter")
    
    # Statistics types
    include_counts: bool = Field(default=True, description="Include entry counts")
    include_sizes: bool = Field(default=True, description="Include size statistics")
    include_temporal: bool = Field(default=True, description="Include temporal statistics")
    
    # Filters
    memory_type: MemoryType | None = Field(default=None, description="Filter by memory type")
    agent_id: str | None = Field(default=None, description="Filter by agent")
    
    # Temporal range
    start_date: datetime | None = Field(default=None, description="Statistics start date")
    end_date: datetime | None = Field(default=None, description="Statistics end date")


class MemoryExportRequest(BaseModel):
    """Request schema for memory export operations."""
    
    session_id: UUID = Field(description="Session identifier")
    
    # Export configuration
    format: str = Field(default="json", pattern="^(json|csv|xml)$", description="Export format")
    include_content: bool = Field(default=True, description="Include memory content")
    include_embeddings: bool = Field(default=False, description="Include embeddings")
    include_metadata: bool = Field(default=True, description="Include metadata")
    
    # Export filters
    memory_type: MemoryType | None = Field(default=None, description="Filter by memory type")
    agent_id: str | None = Field(default=None, description="Filter by agent")
    tags: list[str] | None = Field(default=None, description="Filter by tags")
    
    # Temporal range
    created_after: datetime | None = Field(default=None, description="Filter by creation date")
    created_before: datetime | None = Field(default=None, description="Filter by creation date")


class MemoryImportRequest(BaseModel):
    """Request schema for memory import operations."""
    
    session_id: UUID = Field(description="Session identifier")
    data: str = Field(description="Import data (base64 encoded for binary formats)")
    format: str = Field(pattern="^(json|csv|xml)$", description="Import format")
    
    # Import options
    merge_strategy: str = Field(default="merge", pattern="^(merge|replace|skip)$", description="Merge strategy")
    generate_embeddings: bool = Field(default=True, description="Generate embeddings for imported data")
    validate_data: bool = Field(default=True, description="Validate imported data")
    
    # Mapping options (for CSV/JSON)
    field_mappings: dict[str, str] | None = Field(default=None, description="Field name mappings")
    default_memory_type: MemoryType = Field(default=MemoryType.EPISODIC, description="Default memory type")


# Export all request schemas
__all__ = [
    "MemoryStoreRequest",
    "MemoryRetrieveRequest",
    "MemorySearchRequest",
    "MemoryUpdateRequest",
    "MemoryDeleteRequest",
    "ContextWindowRequest",
    "MemoryCursorRequest",
    "MemoryStatsRequest",
    "MemoryExportRequest",
    "MemoryImportRequest",
]
