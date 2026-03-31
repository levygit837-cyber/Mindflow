"""Vector storage schemas.

Provides schemas for vector database operations, integrating
with global memory and embedding schemas.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class VectorDistance(StrEnum):
    """Distance metrics for vector similarity."""
    
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT_PRODUCT = "dot_product"
    MANHATTAN = "manhattan"


class VectorIndex(StrEnum):
    """Vector indexing strategies."""
    
    HNSW = "hnsw"
    IVF_FLAT = "ivf_flat"
    IVF_PQ = "ivf_pq"
    FLAT = "flat"


class VectorMetadata(BaseModel):
    """Metadata for vector entries."""
    
    document_id: str | None = Field(default=None, description="Document identifier")
    session_id: str | None = Field(default=None, description="Session identifier")
    agent_id: str | None = Field(default=None, description="Agent identifier")
    content_type: str | None = Field(default=None, description="Content type")
    source_type: str | None = Field(default=None, description="Source type")
    timestamp: str | None = Field(default=None, description="Creation timestamp")
    
    # Custom metadata
    custom: dict[str, Any] = Field(default_factory=dict, description="Custom metadata")


class VectorConfig(BaseModel):
    """Vector database configuration."""
    
    # Database configuration
    database_type: str = Field(description="Vector database type")
    connection_string: str = Field(description="Database connection string")
    
    # Vector configuration
    dimension: int = Field(default=768, description="Vector dimension")
    distance_metric: VectorDistance = Field(default=VectorDistance.COSINE, description="Distance metric")
    index_type: VectorIndex = Field(default=VectorIndex.HNSW, description="Index type")
    
    # Performance configuration
    ef_construction: int = Field(default=200, description="HNSW ef construction")
    ef_search: int = Field(default=50, description="HNSW ef search")
    max_connections: int = Field(default=32, description="Max connections per vector")
    
    # Collection configuration
    default_collection: str = Field(default="default", description="Default collection name")
    auto_create_collection: bool = Field(default=True, description="Auto-create collections")
    
    # Batch configuration
    batch_size: int = Field(default=1000, description="Batch insert size")
    max_batch_size: int = Field(default=10000, description="Maximum batch size")


class VectorCollection(BaseModel):
    """Vector collection information."""
    
    name: str = Field(description="Collection name")
    dimension: int = Field(description="Vector dimension")
    count: int = Field(default=0, description="Vector count")
    
    # Index information
    index_type: VectorIndex = Field(description="Index type")
    distance_metric: VectorDistance = Field(description="Distance metric")
    
    # Configuration
    ef_construction: int | None = Field(default=None, description="HNSW ef construction")
    ef_search: int | None = Field(default=None, description="HNSW ef search")
    
    # Timestamps
    created_at: str | None = Field(default=None, description="Creation timestamp")
    updated_at: str | None = Field(default=None, description="Last update timestamp")


class VectorEntry(BaseModel):
    """Single vector entry."""
    
    id: str = Field(description="Vector ID")
    vector: list[float] = Field(description="Vector values")
    metadata: VectorMetadata = Field(description="Vector metadata")
    
    # Optional content
    content: str | None = Field(default=None, description="Original content")
    content_hash: str | None = Field(default=None, description="Content hash")
    
    # Timestamps
    created_at: str | None = Field(default=None, description="Creation timestamp")
    updated_at: str | None = Field(default=None, description="Last update timestamp")


class VectorSearchRequest(BaseModel):
    """Vector search request."""
    
    collection_name: str = Field(description="Target collection")
    query_vector: list[float] = Field(description="Query vector")
    
    # Search parameters
    limit: int = Field(default=10, description="Maximum results")
    score_threshold: float = Field(default=0.0, description="Minimum similarity score")
    
    # Filtering
    filters: dict[str, Any] | None = Field(default=None, description="Metadata filters")
    include_metadata: bool = Field(default=True, description="Include metadata in results")
    
    # Search options
    search_params: dict[str, Any] | None = Field(default=None, description="Search parameters")
    exact_search: bool = Field(default=False, description="Exact match search")


class VectorSearchResult(BaseModel):
    """Single vector search result."""
    
    id: str = Field(description="Vector ID")
    score: float = Field(description="Similarity score")
    distance: float = Field(description="Distance value")
    
    # Vector data
    vector: list[float] | None = Field(default=None, description="Vector values")
    metadata: VectorMetadata | None = Field(default=None, description="Vector metadata")
    content: str | None = Field(default=None, description="Original content")
    
    # Additional info
    rank: int = Field(description="Result rank")
    collection: str = Field(description="Collection name")


class VectorSearchResponse(BaseModel):
    """Vector search response."""
    
    results: list[VectorSearchResult] = Field(description="Search results")
    total_found: int = Field(description="Total results found")
    search_time_ms: float = Field(description="Search time in milliseconds")
    
    # Request info
    request_id: str | None = Field(default=None, description="Request ID")
    collection: str = Field(description="Collection name")
    query_vector_hash: str | None = Field(default=None, description="Query vector hash")


class VectorBatchRequest(BaseModel):
    """Batch vector operation request."""
    
    collection_name: str = Field(description="Target collection")
    vectors: list[VectorEntry] = Field(description="Vectors to insert")
    
    # Batch options
    batch_size: int = Field(default=1000, description="Batch size")
    parallel: bool = Field(default=False, description="Parallel processing")
    skip_duplicates: bool = Field(default=True, description="Skip duplicate vectors")
    
    # Validation
    validate_dimension: bool = Field(default=True, description="Validate vector dimensions")
    validate_metadata: bool = Field(default=True, description="Validate metadata")


class VectorBatchResponse(BaseModel):
    """Batch vector operation response."""
    
    successful_ids: list[str] = Field(description="Successfully inserted IDs")
    failed_entries: list[dict[str, Any]] = Field(description="Failed entries")
    duplicates_skipped: int = Field(default=0, description="Duplicates skipped")
    
    # Performance info
    processing_time_ms: float = Field(description="Processing time in milliseconds")
    throughput_vectors_per_sec: float = Field(description="Processing throughput")
    
    # Request info
    request_id: str | None = Field(default=None, description="Request ID")
    collection: str = Field(description="Collection name")


class VectorStats(BaseModel):
    """Vector database statistics."""
    
    collection_name: str = Field(description="Collection name")
    vector_count: int = Field(description="Total vectors")
    dimension: int = Field(description="Vector dimension")
    
    # Index stats
    index_type: VectorIndex = Field(description="Index type")
    index_size_mb: float = Field(description="Index size in MB")
    index_build_time: str | None = Field(default=None, description="Index build time")
    
    # Performance stats
    avg_search_time_ms: float = Field(description="Average search time")
    avg_insert_time_ms: float = Field(description="Average insert time")
    
    # Storage stats
    storage_size_mb: float = Field(description="Storage size in MB")
    compression_ratio: float | None = Field(default=None, description="Compression ratio")
    
    # Timestamps
    last_optimized: str | None = Field(default=None, description="Last optimization")
    last_compacted: str | None = Field(default=None, description="Last compaction")
