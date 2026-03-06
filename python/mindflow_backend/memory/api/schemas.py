"""Memory API schemas."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MemorySearchRequest(BaseModel):
    """Request for memory search."""
    session_id: str = Field(description="Session ID")
    agent_id: Optional[str] = Field(default=None, description="Agent ID filter")
    query: str = Field(description="Search query")
    top_k: int = Field(default=5, description="Maximum results")
    min_score: float = Field(default=0.3, description="Minimum similarity score")


class MemorySummaryRequest(BaseModel):
    """Request for memory summary."""
    session_id: str = Field(description="Session ID")
    agent_id: str = Field(description="Agent ID")
    window_start: int = Field(description="Window start token")
    window_end: int = Field(description="Window end token")


class ContextWindowRequest(BaseModel):
    """Request for context window."""
    session_id: str = Field(description="Session ID")
    window_start: int = Field(description="Window start token")
    window_end: int = Field(description="Window end token")


class MemoryEventRequest(BaseModel):
    """Request for adding memory event."""
    session_id: str = Field(description="Session ID")
    agent_id: str = Field(description="Agent ID")
    role: str = Field(description="Event role")
    content: str = Field(description="Event content")
    token_count: Optional[int] = Field(default=None, description="Token count")
    source_message_id: Optional[int] = Field(default=None, description="Source message ID")


class MemoryCursorRequest(BaseModel):
    """Request for updating memory cursor."""
    session_id: str = Field(description="Session ID")
    agent_id: str = Field(description="Agent ID")
    token_total: int = Field(description="Total token count")
    tokens_since_summary: int = Field(description="Tokens since summary")


class MemoryResponse(BaseModel):
    """Memory response."""
    success: bool = Field(description="Operation success")
    message: Optional[str] = Field(default=None, description="Response message")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Response data")
    agent_id: Optional[str] = Field(default=None, description="Agent ID")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    memory_events: Optional[List[Dict[str, Any]]] = Field(default=None, description="Memory events")
    token_count: Optional[int] = Field(default=None, description="Total token count")
    window_index: Optional[int] = Field(default=None, description="Current window index")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Memory metadata")


class MemorySearchResponse(MemoryResponse):
    """Memory search response."""
    results: List[Dict[str, Any]] = Field(default=[], description="Search results")
    query: str = Field(description="Search query")
    total_results: int = Field(default=0, description="Total results found")


class MemorySummaryResponse(MemoryResponse):
    """Memory summary response."""
    summary: str = Field(description="Memory summary")
    window_range: List[int] = Field(description="Token window range")
    event_count: int = Field(description="Number of events summarized")


class ContextWindowResponse(MemoryResponse):
    """Context window response."""
    context: str = Field(description="Context content")
    window_start: int = Field(description="Window start token")
    window_end: int = Field(description="Window end token")
    event_count: int = Field(description="Number of events in window")
    total_tokens: int = Field(description="Total tokens in window")


class BaseResponse(BaseModel):
    """Base response model."""
    success: bool = Field(description="Operation success")
    message: Optional[str] = Field(default=None, description="Response message")
    timestamp: Optional[str] = Field(default=None, description="Response timestamp")
