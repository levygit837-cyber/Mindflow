"""Memory API schemas for MindFlow backend.

Provides request/response schemas for memory operations including
search, summary, context management, and event tracking.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    """Base response schema for all memory operations."""
    
    success: bool = Field(description="Whether the operation was successful")
    message: Optional[str] = Field(default=None, description="Optional message")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class MemorySearchRequest(BaseModel):
    """Request schema for memory search operations."""
    
    query: str = Field(min_length=1, description="Search query")
    session_id: Optional[UUID] = Field(default=None, description="Optional session filter")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum results to return")
    threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Similarity threshold")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Additional filters")


class MemorySearchResponse(BaseResponse):
    """Response schema for memory search operations."""
    
    results: List[Dict[str, Any]] = Field(description="Search results")
    total_found: int = Field(description="Total number of results found")
    query: str = Field(description="Original search query")
    session_id: Optional[UUID] = Field(default=None, description="Session filter used")


class MemorySummaryRequest(BaseModel):
    """Request schema for memory summary operations."""
    
    session_id: UUID = Field(description="Session ID to summarize")
    start_token: Optional[int] = Field(default=None, description="Start token position")
    end_token: Optional[int] = Field(default=None, description="End token position")
    summary_type: str = Field(default="comprehensive", description="Type of summary")
    include_metadata: bool = Field(default=True, description="Include metadata in summary")


class MemorySummaryResponse(BaseResponse):
    """Response schema for memory summary operations."""
    
    session_id: UUID = Field(description="Session ID that was summarized")
    summary: str = Field(description="Generated summary")
    key_points: List[str] = Field(default_factory=list, description="Key points from summary")
    token_count: int = Field(description="Number of tokens summarized")
    compression_ratio: float = Field(description="Compression ratio achieved")


class ContextWindowRequest(BaseModel):
    """Request schema for context window operations."""
    
    session_id: UUID = Field(description="Session ID")
    window_size: int = Field(default=1000, ge=1, le=10000, description="Window size in tokens")
    position: Optional[int] = Field(default=None, description="Specific position to center window")
    include_embeddings: bool = Field(default=False, description="Include embeddings in response")


class ContextWindowResponse(BaseResponse):
    """Response schema for context window operations."""
    
    session_id: UUID = Field(description="Session ID")
    window: List[Dict[str, Any]] = Field(description="Context window data")
    window_size: int = Field(description="Actual window size")
    start_position: int = Field(description="Start token position")
    end_position: int = Field(description="End token position")
    embeddings: Optional[List[List[float]]] = Field(default=None, description="Embeddings if requested")


class MemoryEventRequest(BaseModel):
    """Request schema for memory event operations."""
    
    session_id: UUID = Field(description="Session ID")
    event_type: str = Field(description="Type of event")
    content: str = Field(min_length=1, description="Event content")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Event metadata")
    timestamp: Optional[datetime] = Field(default=None, description="Event timestamp")


class MemoryCursorRequest(BaseModel):
    """Request schema for memory cursor operations."""
    
    session_id: UUID = Field(description="Session ID")
    cursor_position: int = Field(ge=0, description="Cursor position")
    operation: str = Field(description="Cursor operation (move, set, reset)")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Operation parameters")


class MemoryResponse(BaseResponse):
    """Generic memory response schema."""
    
    session_id: Optional[UUID] = Field(default=None, description="Session ID if applicable")
    operation: str = Field(description="Operation performed")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Operation data")
    affected_count: Optional[int] = Field(default=None, description="Number of items affected")


# Export all schemas
__all__ = [
    "BaseResponse",
    "MemorySearchRequest",
    "MemorySearchResponse", 
    "MemorySummaryRequest",
    "MemorySummaryResponse",
    "ContextWindowRequest",
    "ContextWindowResponse",
    "MemoryEventRequest",
    "MemoryCursorRequest",
    "MemoryResponse",
]
