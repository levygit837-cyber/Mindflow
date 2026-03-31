"""Storage-specific memory schemas.

Extends global memory schemas with storage-specific contracts
and data structures.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# Import global schemas to extend
from mindflow_backend.schemas.memory.contracts import (
    ContextWindow,
    MemoryEntry,
)


class StorageMemoryEntry(MemoryEntry):
    """Storage-specific memory entry with additional fields."""
    
    # Storage-specific fields
    storage_backend: str = Field(description="Storage backend used")
    storage_location: str | None = Field(default=None, description="Storage location identifier")
    
    # Persistence metadata
    is_persistent: bool = Field(default=True, description="Is persistent storage")
    backup_count: int = Field(default=0, description="Number of backups")
    last_backup: str | None = Field(default=None, description="Last backup timestamp")
    
    # Compression and optimization
    is_compressed: bool = Field(default=False, description="Is compressed")
    compression_algorithm: str | None = Field(default=None, description="Compression algorithm")
    is_encrypted: bool = Field(default=False, description="Is encrypted")
    encryption_key_id: str | None = Field(default=None, description="Encryption key identifier")
    
    # Versioning
    version: int = Field(default=1, description="Entry version")
    parent_version: int | None = Field(default=None, description="Parent version")
    change_log: list[dict[str, Any]] = Field(default_factory=list, description="Change log")


class StorageMemoryWindow(ContextWindow):
    """Storage-specific context window with additional metadata."""
    
    # Storage-specific fields
    storage_backend: str = Field(description="Storage backend used")
    storage_path: str | None = Field(default=None, description="Storage path")
    
    # Window optimization
    is_optimized: bool = Field(default=False, description="Is optimized")
    optimization_score: float = Field(default=0.0, description="Optimization score")
    compression_ratio: float | None = Field(default=None, description="Compression ratio")
    
    # Persistence
    is_persistent: bool = Field(default=True, description="Is persistent")
    auto_refresh: bool = Field(default=False, description="Auto-refresh enabled")
    refresh_interval: int | None = Field(default=None, description="Refresh interval in seconds")
    
    # Index information
    is_indexed: bool = Field(default=False, description="Is indexed")
    index_type: str | None = Field(default=None, description="Index type")
    index_size: int | None = Field(default=None, description="Index size")


class StorageMemoryStats(BaseModel):
    """Storage memory statistics."""
    
    # Basic counts
    total_entries: int = Field(default=0, description="Total memory entries")
    active_entries: int = Field(default=0, description="Active entries")
    archived_entries: int = Field(default=0, description="Archived entries")
    
    # Memory usage
    memory_usage_mb: float = Field(default=0.0, description="Memory usage in MB")
    storage_usage_mb: float = Field(default=0.0, description="Storage usage in MB")
    
    # Performance metrics
    avg_retrieval_time_ms: float = Field(default=0.0, description="Average retrieval time")
    avg_storage_time_ms: float = Field(default=0.0, description="Average storage time")
    operations_per_sec: float = Field(default=0.0, description="Operations per second")
    
    # Type distribution
    entries_by_type: dict[str, int] = Field(default_factory=dict, description="Entries by type")
    entries_by_status: dict[str, int] = Field(default_factory=dict, description="Entries by status")
    
    # Session distribution
    active_sessions: int = Field(default=0, description="Active sessions")
    total_sessions: int = Field(default=0, description="Total sessions")
    
    # Storage backend info
    backends_in_use: list[str] = Field(default_factory=list, description="Storage backends in use")
    primary_backend: str = Field(description="Primary storage backend")
    
    # Timestamps
    last_cleanup: str | None = Field(default=None, description="Last cleanup")
    last_optimization: str | None = Field(default=None, description="Last optimization")
    last_backup: str | None = Field(default=None, description="Last backup")


class MemoryStorageConfig(BaseModel):
    """Memory storage configuration."""
    
    # Storage backends
    primary_backend: str = Field(description="Primary storage backend")
    fallback_backends: list[str] = Field(default_factory=list, description="Fallback backends")
    
    # Performance configuration
    cache_enabled: bool = Field(default=True, description="Enable caching")
    cache_ttl: int = Field(default=3600, description="Cache TTL in seconds")
    cache_size_mb: int = Field(default=512, description="Cache size in MB")
    
    # Persistence configuration
    auto_backup: bool = Field(default=True, description="Automatic backup")
    backup_interval_hours: int = Field(default=24, description="Backup interval in hours")
    backup_retention_days: int = Field(default=30, description="Backup retention days")
    
    # Optimization
    auto_optimize: bool = Field(default=True, description="Automatic optimization")
    optimize_interval_hours: int = Field(default=6, description="Optimization interval")
    optimization_threshold: float = Field(default=0.8, description="Optimization threshold")
    
    # Compression
    compression_enabled: bool = Field(default=False, description="Enable compression")
    compression_algorithm: str = Field(default="lz4", description="Compression algorithm")
    compression_level: int = Field(default=6, description="Compression level")
    
    # Encryption
    encryption_enabled: bool = Field(default=False, description="Enable encryption")
    encryption_algorithm: str = Field(default="aes256", description="Encryption algorithm")
    key_rotation_days: int = Field(default=90, description="Key rotation interval")


class MemoryMigrationRequest(BaseModel):
    """Memory migration request."""
    
    # Migration details
    source_backend: str = Field(description="Source storage backend")
    target_backend: str = Field(description="Target storage backend")
    
    # Scope
    session_ids: list[str] | None = Field(default=None, description="Specific session IDs")
    date_range: dict[str, str] | None = Field(default=None, description="Date range filter")
    memory_types: list[str] | None = Field(default=None, description="Memory types to migrate")
    
    # Migration options
    dry_run: bool = Field(default=False, description="Dry run mode")
    batch_size: int = Field(default=1000, description="Batch size")
    parallel_workers: int = Field(default=4, description="Parallel workers")
    continue_on_error: bool = Field(default=True, description="Continue on error")
    
    # Validation
    verify_integrity: bool = Field(default=True, description="Verify integrity")
    verify_count: bool = Field(default=True, description="Verify entry count")
    
    # Performance
    timeout_seconds: int = Field(default=3600, description="Migration timeout")
    progress_interval: int = Field(default=100, description="Progress report interval")


class MemoryMigrationResponse(BaseModel):
    """Memory migration response."""
    
    # Migration results
    status: str = Field(description="Migration status")
    entries_migrated: int = Field(default=0, description="Entries migrated")
    entries_failed: int = Field(default=0, description="Entries failed")
    entries_skipped: int = Field(default=0, description="Entries skipped")
    
    # Performance info
    migration_time_seconds: float = Field(description="Migration time in seconds")
    throughput_entries_per_sec: float = Field(description="Migration throughput")
    
    # Data integrity
    checksum_matched: bool = Field(default=True, description="Checksum verification passed")
    count_matched: bool = Field(default=True, description="Count verification passed")
    
    # Error information
    errors: list[dict[str, Any]] = Field(default_factory=list, description="Migration errors")
    warnings: list[dict[str, Any]] = Field(default_factory=list, description="Migration warnings")
    
    # Request info
    migration_id: str | None = Field(default=None, description="Migration ID")
    source_backend: str = Field(description="Source backend")
    target_backend: str = Field(description="Target backend")


class MemoryCleanupRequest(BaseModel):
    """Memory cleanup request."""
    
    # Cleanup scope
    cleanup_type: str = Field(description="Cleanup type: expired/duplicates/orphaned")
    target_backends: list[str] | None = Field(default=None, description="Target backends")
    
    # Filtering
    older_than_days: int | None = Field(default=None, description="Older than N days")
    memory_types: list[str] | None = Field(default=None, description="Memory types")
    session_ids: list[str] | None = Field(default=None, description="Specific sessions")
    
    # Cleanup options
    dry_run: bool = Field(default=False, description="Dry run mode")
    batch_size: int = Field(default=1000, description="Batch size")
    archive_before_delete: bool = Field(default=True, description="Archive before delete")
    
    # Safety
    confirm_destructive: bool = Field(default=False, description="Confirm destructive operations")
    backup_before_cleanup: bool = Field(default=True, description="Backup before cleanup")


class MemoryCleanupResponse(BaseModel):
    """Memory cleanup response."""
    
    # Cleanup results
    status: str = Field(description="Cleanup status")
    entries_processed: int = Field(default=0, description="Entries processed")
    entries_deleted: int = Field(default=0, description="Entries deleted")
    entries_archived: int = Field(default=0, description="Entries archived")
    
    # Space recovered
    space_recovered_mb: float = Field(default=0.0, description="Space recovered in MB")
    compression_ratio: float | None = Field(default=None, description="Achieved compression ratio")
    
    # Performance info
    cleanup_time_seconds: float = Field(description="Cleanup time in seconds")
    throughput_entries_per_sec: float = Field(description="Cleanup throughput")
    
    # Safety info
    backup_created: bool = Field(default=False, description="Backup created")
    backup_location: str | None = Field(default=None, description="Backup location")
    
    # Request info
    cleanup_id: str | None = Field(default=None, description="Cleanup ID")
    warnings: list[dict[str, Any]] = Field(default_factory=list, description="Cleanup warnings")
