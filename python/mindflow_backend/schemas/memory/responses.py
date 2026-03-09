"""Memory response schemas for MindFlow backend.

Provides response schemas for all memory operations including storage,
retrieval, search, and management operations.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .contracts import MemoryEntry, ContextWindow, MemoryCursor, MemoryEvent


class BaseMemoryResponse(BaseModel):
    """Base response schema for all memory operations."""
    
    success: bool = Field(description="Whether the operation was successful")
    message: Optional[str] = Field(default=None, description="Response message")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    operation_id: Optional[UUID] = Field(default=None, description="Operation identifier")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class MemoryStoreResponse(BaseMemoryResponse):
    """Response schema for memory store operations."""
    
    memory_id: UUID = Field(description="Stored memory entry ID")
    session_id: UUID = Field(description="Session ID")
    token_count: int = Field(description="Number of tokens stored")
    embedding_generated: bool = Field(description="Whether embedding was generated")
    embedding_dimension: Optional[int] = Field(default=None, description="Embedding dimension if generated")
    processing_time_ms: Optional[int] = Field(default=None, description="Processing time in milliseconds")


class MemoryRetrieveResponse(BaseMemoryResponse):
    """Response schema for memory retrieve operations."""
    
    session_id: UUID = Field(description="Session ID")
    entries: List[MemoryEntry] = Field(description="Retrieved memory entries")
    total_count: int = Field(description="Total number of entries found")
    returned_count: int = Field(description="Number of entries returned")
    has_more: bool = Field(description="Whether more entries are available")
    processing_time_ms: Optional[int] = Field(default=None, description="Processing time in milliseconds")


class MemorySearchResponse(BaseMemoryResponse):
    """Response schema for memory search operations."""
    
    query: str = Field(description="Original search query")
    session_id: Optional[UUID] = Field(default=None, description="Session ID if filtered")
    results: List[Dict[str, Any]] = Field(description="Search results with scores")
    total_found: int = Field(description="Total number of results found")
    returned_count: int = Field(description="Number of results returned")
    search_strategy: str = Field(description="Search strategy used")
    processing_time_ms: Optional[int] = Field(default=None, description="Processing time in milliseconds")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class SearchResult(BaseModel):
    """Individual search result."""
    
    memory_id: UUID = Field(description="Memory entry ID")
    content: str = Field(description="Memory content")
    score: float = Field(description="Relevance score")
    highlights: Optional[List[str]] = Field(default=None, description="Highlighted matches")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Entry metadata")


class MemoryUpdateResponse(BaseMemoryResponse):
    """Response schema for memory update operations."""
    
    memory_id: UUID = Field(description="Updated memory entry ID")
    fields_updated: List[str] = Field(description="List of updated fields")
    embedding_regenerated: bool = Field(description="Whether embedding was regenerated")
    processing_time_ms: Optional[int] = Field(default=None, description="Processing time in milliseconds")


class MemoryDeleteResponse(BaseMemoryResponse):
    """Response schema for memory delete operations."""
    
    deleted_count: int = Field(description="Number of entries deleted")
    memory_ids: List[UUID] = Field(description="IDs of deleted entries")
    soft_deleted: bool = Field(description="Whether soft delete was used")
    processing_time_ms: Optional[int] = Field(default=None, description="Processing time in milliseconds")


class ContextWindowResponse(BaseMemoryResponse):
    """Response schema for context window operations."""
    
    session_id: UUID = Field(description="Session ID")
    window: ContextWindow = Field(description="Context window data")
    window_size: int = Field(description="Actual window size")
    start_position: int = Field(description="Start token position")
    end_position: int = Field(description="End token position")
    compression_ratio: Optional[float] = Field(default=None, description="Compression ratio if compressed")
    processing_time_ms: Optional[int] = Field(default=None, description="Processing time in milliseconds")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class MemoryCursorResponse(BaseMemoryResponse):
    """Response schema for memory cursor operations."""
    
    session_id: UUID = Field(description="Session ID")
    cursor: MemoryCursor = Field(description="Memory cursor data")
    context_entries: List[MemoryEntry] = Field(description="Entries in cursor context")
    context_size: int = Field(description="Size of context window")
    processing_time_ms: Optional[int] = Field(default=None, description="Processing time in milliseconds")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class MemoryStatsResponse(BaseMemoryResponse):
    """Response schema for memory statistics."""
    
    session_id: Optional[UUID] = Field(default=None, description="Session ID if filtered")
    
    # Count statistics
    total_entries: int = Field(description="Total number of memory entries")
    entries_by_type: Dict[str, int] = Field(description="Entries grouped by type")
    entries_by_agent: Dict[str, int] = Field(description="Entries grouped by agent")
    
    # Size statistics
    total_tokens: int = Field(description="Total number of tokens")
    average_tokens_per_entry: float = Field(description="Average tokens per entry")
    total_embeddings: int = Field(description="Total number of embeddings")
    storage_size_bytes: Optional[int] = Field(default=None, description="Storage size in bytes")
    
    # Temporal statistics
    oldest_entry: Optional[datetime] = Field(default=None, description="Oldest entry timestamp")
    newest_entry: Optional[datetime] = Field(default=None, description="Newest entry timestamp")
    entries_per_day: Dict[str, int] = Field(default_factory=dict, description="Entries per day")
    
    # Performance statistics
    average_retrieval_time_ms: Optional[float] = Field(default=None, description="Average retrieval time")
    cache_hit_rate: Optional[float] = Field(default=None, description="Cache hit rate")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class MemoryExportResponse(BaseMemoryResponse):
    """Response schema for memory export operations."""
    
    session_id: UUID = Field(description="Session ID")
    export_id: UUID = Field(description="Export operation ID")
    format: str = Field(description="Export format")
    entries_exported: int = Field(description="Number of entries exported")
    file_size_bytes: int = Field(description="Export file size in bytes")
    download_url: Optional[str] = Field(default=None, description="Download URL if available")
    expires_at: Optional[datetime] = Field(default=None, description="Export expiration time")
    processing_time_ms: Optional[int] = Field(default=None, description="Processing time in milliseconds")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class MemoryImportResponse(BaseMemoryResponse):
    """Response schema for memory import operations."""
    
    session_id: UUID = Field(description="Session ID")
    import_id: UUID = Field(description="Import operation ID")
    format: str = Field(description="Import format")
    
    # Import statistics
    total_processed: int = Field(description="Total entries processed")
    entries_imported: int = Field(description="Number of entries imported")
    entries_skipped: int = Field(description="Number of entries skipped")
    entries_failed: int = Field(description="Number of entries that failed")
    
    # Validation results
    validation_errors: List[str] = Field(default_factory=list, description="Validation errors")
    duplicates_found: int = Field(default=0, description="Number of duplicates found")
    
    # Embedding statistics
    embeddings_generated: int = Field(description="Number of embeddings generated")
    processing_time_ms: Optional[int] = Field(default=None, description="Processing time in milliseconds")


class MemoryBatchResponse(BaseMemoryResponse):
    """Response schema for batch memory operations."""
    
    operation: str = Field(description="Batch operation type")
    total_requested: int = Field(description="Total number of operations requested")
    successful_operations: int = Field(description="Number of successful operations")
    failed_operations: int = Field(description="Number of failed operations")
    
    # Detailed results
    results: List[Dict[str, Any]] = Field(description="Individual operation results")
    errors: List[str] = Field(default_factory=list, description="Operation errors")
    
    processing_time_ms: Optional[int] = Field(default=None, description="Total processing time")


class MemoryHealthResponse(BaseMemoryResponse):
    """Response schema for memory health checks."""
    
    status: str = Field(description="Overall health status")
    checks: Dict[str, Dict[str, Any]] = Field(description="Individual health checks")
    
    # Storage health
    storage_status: str = Field(description="Storage system status")
    available_space_bytes: Optional[int] = Field(default=None, description="Available storage space")
    storage_utilization: Optional[float] = Field(default=None, description="Storage utilization percentage")
    
    # Performance health
    response_time_ms: Optional[float] = Field(default=None, description="Average response time")
    error_rate: Optional[float] = Field(default=None, description="Current error rate")
    
    # Connection health
    database_connected: bool = Field(description="Database connection status")
    embedding_service_connected: bool = Field(description="Embedding service connection status")


# Export all response schemas
__all__ = [
    "BaseMemoryResponse",
    "MemoryStoreResponse",
    "MemoryRetrieveResponse",
    "MemorySearchResponse",
    "SearchResult",
    "MemoryUpdateResponse",
    "MemoryDeleteResponse",
    "ContextWindowResponse",
    "MemoryCursorResponse",
    "MemoryStatsResponse",
    "MemoryExportResponse",
    "MemoryImportResponse",
    "MemoryBatchResponse",
    "MemoryHealthResponse",
]
