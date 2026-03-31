"""Storage-specific schemas.

Provides schemas for storage operations, configuration,
and data structures, integrating with global schema system.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class StorageType(StrEnum):
    """Storage backend types."""
    
    POSTGRESQL = "postgresql"
    KUZUDB = "kuzudb"
    REDIS = "redis"
    MEMORY = "memory"
    DISK = "disk"


class StorageConfig(BaseModel):
    """Storage configuration."""
    
    storage_type: StorageType = Field(description="Storage type")
    connection_string: str = Field(description="Connection string")
    
    # Performance settings
    max_connections: int = Field(default=100, description="Maximum connections")
    timeout_seconds: int = Field(default=30, description="Operation timeout")
    retry_attempts: int = Field(default=3, description="Retry attempts")
    
    # Persistence settings
    persist_to_disk: bool = Field(default=True, description="Persist to disk")
    backup_enabled: bool = Field(default=True, description="Enable backups")
    
    # Monitoring
    metrics_enabled: bool = Field(default=True, description="Enable metrics")
    health_check_interval: int = Field(default=60, description="Health check interval")


class StorageOperation(BaseModel):
    """Storage operation metadata."""
    
    operation_type: str = Field(description="Operation type")
    storage_backend: str = Field(description="Storage backend")
    
    # Timing
    started_at: str = Field(description="Start timestamp")
    completed_at: str | None = Field(default=None, description="Completion timestamp")
    duration_ms: float | None = Field(default=None, description="Duration in milliseconds")
    
    # Status
    status: str = Field(description="Operation status")
    success: bool = Field(description="Operation success")
    
    # Data info
    items_processed: int = Field(default=0, description="Items processed")
    items_affected: int = Field(default=0, description="Items affected")
    
    # Error info
    error_code: str | None = Field(default=None, description="Error code")
    error_message: str | None = Field(default=None, description="Error message")
    

class StorageStats(BaseModel):
    """Storage statistics."""
    
    storage_backend: str = Field(description="Storage backend")
    storage_type: StorageType = Field(description="Storage type")
    
    # Usage stats
    total_items: int = Field(default=0, description="Total items")
    active_items: int = Field(default=0, description="Active items")
    storage_size_mb: float = Field(default=0.0, description="Storage size in MB")
    
    # Performance stats
    operations_per_second: float = Field(default=0.0, description="Operations per second")
    avg_response_time_ms: float = Field(default=0.0, description="Average response time")
    
    # Connection stats
    active_connections: int = Field(default=0, description="Active connections")
    total_connections: int = Field(default=0, description="Total connections")
    
    # Health status
    is_healthy: bool = Field(default=True, description="Storage health")
    last_health_check: str | None = Field(default=None, description="Last health check")
    
    # Timestamps
    last_updated: str = Field(description="Last update timestamp")
    uptime_seconds: float | None = Field(default=None, description="Uptime in seconds")


class StorageHealthCheck(BaseModel):
    """Storage health check result."""
    
    storage_backend: str = Field(description="Storage backend")
    status: str = Field(description="Health status")
    
    # Check results
    connection_ok: bool = Field(description="Connection test")
    performance_ok: bool = Field(description="Performance test")
    integrity_ok: bool = Field(description="Integrity test")
    
    # Metrics
    response_time_ms: float = Field(description="Response time")
    throughput_ops_per_sec: float = Field(description="Throughput")
    
    # Issues found
    issues: list[str] = Field(default_factory=list, description="Issues found")
    warnings: list[str] = Field(default_factory=list, description="Warnings found")
    
    # Timestamp
    checked_at: str = Field(description="Health check timestamp")


class StorageMigration(BaseModel):
    """Storage migration information."""
    
    migration_id: str = Field(description="Migration ID")
    source_backend: str = Field(description="Source backend")
    target_backend: str = Field(description="Target backend")
    
    # Migration scope
    items_count: int = Field(description="Items to migrate")
    items_migrated: int = Field(default=0, description="Items migrated")
    items_failed: int = Field(default=0, description="Items failed")
    
    # Timing
    started_at: str = Field(description="Start timestamp")
    estimated_completion: str | None = Field(default=None, description="Estimated completion")
    actual_completion: str | None = Field(default=None, description="Actual completion")
    
    # Status
    status: str = Field(description="Migration status")
    progress_percentage: float = Field(default=0.0, description="Progress percentage")
    
    # Error info
    errors: list[dict[str, Any]] = Field(default_factory=list, description="Migration errors")


class StorageBackup(BaseModel):
    """Storage backup information."""
    
    backup_id: str = Field(description="Backup ID")
    storage_backend: str = Field(description="Storage backend")
    
    # Backup scope
    backup_type: str = Field(description="Backup type: full/incremental")
    items_count: int = Field(description="Items backed up")
    compression_enabled: bool = Field(description="Compression enabled")
    
    # Storage info
    backup_size_mb: float = Field(description="Backup size in MB")
    compression_ratio: float | None = Field(default=None, description="Compression ratio")
    
    # Timing
    started_at: str = Field(description="Start timestamp")
    completed_at: str | None = Field(default=None, description="Completion timestamp")
    duration_seconds: float | None = Field(default=None, description="Duration in seconds")
    
    # Status
    status: str = Field(description="Backup status")
    location: str = Field(description="Backup location")
    
    # Verification
    checksum: str | None = Field(default=None, description="Backup checksum")
    verified: bool = Field(default=False, description="Backup verified")


class StorageRequest(BaseModel):
    """Generic storage request."""
    
    request_id: str = Field(description="Request ID")
    operation: str = Field(description="Operation type")
    storage_backend: str | None = Field(default=None, description="Target storage backend")
    
    # Request data
    payload: dict[str, Any] = Field(description="Request payload")
    filters: dict[str, Any] | None = Field(default=None, description="Request filters")
    
    # Options
    timeout_seconds: int = Field(default=30, description="Request timeout")
    retry_attempts: int = Field(default=3, description="Retry attempts")
    dry_run: bool = Field(default=False, description="Dry run mode")
    
    # Timestamp
    created_at: str = Field(description="Request timestamp")


class StorageResponse(BaseModel):
    """Generic storage response."""
    
    request_id: str = Field(description="Request ID")
    operation: str = Field(description="Operation type")
    storage_backend: str = Field(description="Storage backend")
    
    # Response data
    success: bool = Field(description="Operation success")
    data: dict[str, Any] | None = Field(default=None, description="Response data")
    items: list[Any] = Field(default_factory=list, description="Response items")
    
    # Performance info
    processing_time_ms: float = Field(description="Processing time in milliseconds")
    items_processed: int = Field(default=0, description="Items processed")
    
    # Status info
    status_code: str | None = Field(default=None, description="Status code")
    message: str = Field(description="Response message")
    
    # Error info
    error_code: str | None = Field(default=None, description="Error code")
    error_details: dict[str, Any] | None = Field(default=None, description="Error details")
    
    # Timestamp
    responded_at: str = Field(description="Response timestamp")
