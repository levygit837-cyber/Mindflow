"""Cache storage schemas.

Provides schemas for cache operations and configuration.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from enum import StrEnum

from pydantic import BaseModel, Field


class CacheType(StrEnum):
    """Supported cache types."""
    
    REDIS = "redis"
    MEMCACHED = "memcached"
    MEMORY = "memory"
    DISK = "disk"
    CUSTOM = "custom"


class EvictionPolicy(StrEnum):
    """Cache eviction policies."""
    
    LRU = "lru"
    LFU = "lfu"
    FIFO = "fifo"
    LIFO = "lifo"
    TTL = "ttl"
    RANDOM = "random"


class CacheConfig(BaseModel):
    """Cache configuration."""
    
    # Basic configuration
    cache_type: CacheType = Field(description="Cache type")
    connection_string: str = Field(description="Cache connection string")
    
    # Performance configuration
    max_memory_mb: int = Field(default=1024, description="Maximum memory in MB")
    max_connections: int = Field(default=100, description="Maximum connections")
    connection_timeout: int = Field(default=5, description="Connection timeout in seconds")
    
    # Eviction policy
    eviction_policy: EvictionPolicy = Field(default=EvictionPolicy.LRU, description="Eviction policy")
    default_ttl: int = Field(default=3600, description="Default TTL in seconds")
    max_ttl: int = Field(default=86400, description="Maximum TTL in seconds")
    
    # Serialization
    serializer: str = Field(default="json", description="Serializer type")
    compression: bool = Field(default=False, description="Enable compression")
    
    # Persistence
    persist_to_disk: bool = Field(default=False, description="Persist to disk")
    disk_path: Optional[str] = Field(default=None, description="Disk persistence path")
    
    # Monitoring
    metrics_enabled: bool = Field(default=True, description="Enable metrics")
    slow_log_threshold_ms: float = Field(default=100.0, description="Slow operation threshold")


class CacheEntry(BaseModel):
    """Single cache entry."""
    
    key: str = Field(description="Cache key")
    value: Any = Field(description="Cache value")
    
    # TTL information
    ttl: Optional[int] = Field(default=None, description="Time to live in seconds")
    expires_at: Optional[str] = Field(default=None, description="Expiration timestamp")
    created_at: Optional[str] = Field(default=None, description="Creation timestamp")
    accessed_at: Optional[str] = Field(default=None, description="Last access timestamp")
    
    # Size information
    size_bytes: Optional[int] = Field(default=None, description="Size in bytes")
    compressed: bool = Field(default=False, description="Is compressed")
    
    # Metadata
    tags: List[str] = Field(default_factory=list, description="Entry tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")


class CacheStats(BaseModel):
    """Cache statistics."""
    
    # Basic stats
    total_entries: int = Field(default=0, description="Total entries")
    memory_usage_mb: float = Field(default=0.0, description="Memory usage in MB")
    hit_rate: float = Field(default=0.0, description="Hit rate")
    miss_rate: float = Field(default=0.0, description="Miss rate")
    
    # Performance stats
    avg_get_time_ms: float = Field(default=0.0, description="Average get time")
    avg_set_time_ms: float = Field(default=0.0, description="Average set time")
    operations_per_sec: float = Field(default=0.0, description="Operations per second")
    
    # Eviction stats
    evictions: int = Field(default=0, description="Total evictions")
    eviction_rate: float = Field(default=0.0, description="Eviction rate")
    
    # Connection stats
    active_connections: int = Field(default=0, description="Active connections")
    connection_errors: int = Field(default=0, description="Connection errors")
    
    # Timestamps
    last_reset: Optional[str] = Field(default=None, description="Last stats reset")
    last_cleanup: Optional[str] = Field(default=None, description="Last cleanup")


class CacheBatchRequest(BaseModel):
    """Batch cache operation request."""
    
    operations: List[Dict[str, Any]] = Field(description="Batch operations")
    operation_type: str = Field(description="Operation type: get/set/delete")
    
    # Batch options
    atomic: bool = Field(default=False, description="Atomic execution")
    continue_on_error: bool = Field(default=True, description="Continue on error")
    
    # Performance
    timeout_ms: int = Field(default=5000, description="Batch timeout in milliseconds")
    parallel: bool = Field(default=False, description="Parallel execution")


class CacheBatchResponse(BaseModel):
    """Batch cache operation response."""
    
    successful_operations: int = Field(description="Successful operations")
    failed_operations: List[Dict[str, Any]] = Field(description="Failed operations")
    
    # Performance info
    processing_time_ms: float = Field(description="Processing time in milliseconds")
    operations_per_sec: float = Field(description="Operations per second")
    
    # Request info
    request_id: Optional[str] = Field(default=None, description="Request ID")


class CacheHealthCheck(BaseModel):
    """Cache health check result."""
    
    status: str = Field(description="Health status: healthy/unhealthy/degraded")
    response_time_ms: float = Field(description="Response time in milliseconds")
    
    # Connection info
    active_connections: int = Field(description="Active connections")
    max_connections: int = Field(description="Maximum connections")
    
    # Memory info
    memory_usage_mb: float = Field(description="Memory usage in MB")
    memory_utilization: float = Field(description="Memory utilization rate")
    
    # Performance info
    hit_rate: float = Field(description="Current hit rate")
    operations_per_sec: float = Field(description="Current operations per second")
    
    # Timestamp
    checked_at: str = Field(description="Health check timestamp")


class CacheConfigRedis(CacheConfig):
    """Redis-specific cache configuration."""
    
    # Redis configuration
    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    database: int = Field(default=0, description="Redis database number")
    
    # Authentication
    password: Optional[str] = Field(default=None, description="Redis password")
    username: Optional[str] = Field(default=None, description="Redis username")
    
    # Redis-specific options
    max_connections_per_cpu: int = Field(default=10, description="Max connections per CPU")
    tcp_keepalive: int = Field(default=300, description="TCP keepalive")
    socket_timeout: int = Field(default=30, description="Socket timeout")
    
    # Cluster configuration
    cluster_nodes: Optional[List[str]] = Field(default=None, description="Cluster nodes")
    cluster_password: Optional[str] = Field(default=None, description="Cluster password")
    
    # Persistence
    save_enabled: bool = Field(default=False, description="Enable RDB saves")
    save_interval_sec: int = Field(default=300, description="Save interval in seconds")
    rdb_path: Optional[str] = Field(default=None, description="RDB file path")


class CacheConfigMemory(CacheConfig):
    """In-memory cache configuration."""
    
    # Memory configuration
    max_entries: int = Field(default=10000, description="Maximum entries")
    shard_count: int = Field(default=1, description="Number of shards")
    
    # Memory management
    gc_threshold: float = Field(default=0.8, description="GC threshold")
    gc_interval_sec: int = Field(default=60, description="GC interval in seconds")
    
    # Thread safety
    lock_free: bool = Field(default=False, description="Lock-free implementation")
    concurrent_readers: bool = Field(default=True, description="Concurrent readers")
