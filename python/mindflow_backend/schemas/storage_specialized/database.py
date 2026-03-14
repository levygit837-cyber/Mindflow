"""Database storage schemas.

Provides configuration and contract schemas for database operations,
integrating with global configuration system.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from enum import StrEnum

from pydantic import BaseModel, Field


class DatabaseType(StrEnum):
    """Supported database types."""
    
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    KUZUDB = "kuzudb"
    QDRANT = "qdrant"
    CHROMA = "chroma"


class ConnectionConfig(BaseModel):
    """Database connection configuration."""
    
    host: str = Field(description="Database host")
    port: int = Field(default=5432, description="Database port")
    database: str = Field(description="Database name")
    username: str = Field(description="Database username")
    password: str = Field(description="Database password")
    
    # SSL configuration
    ssl_mode: str = Field(default="prefer", description="SSL mode")
    ssl_cert: Optional[str] = Field(default=None, description="SSL certificate path")
    ssl_key: Optional[str] = Field(default=None, description="SSL key path")
    ssl_ca: Optional[str] = Field(default=None, description="SSL CA path")
    
    # Connection options
    connect_timeout: int = Field(default=30, description="Connection timeout in seconds")
    command_timeout: int = Field(default=30000, description="Command timeout in milliseconds")
    idle_in_transaction_session_timeout: int = Field(
        default=300000, 
        description="Idle transaction timeout in milliseconds"
    )


class PoolConfig(BaseModel):
    """Connection pool configuration."""
    
    pool_size: int = Field(default=20, description="Base pool size")
    max_overflow: int = Field(default=30, description="Maximum overflow connections")
    pool_recycle: int = Field(default=3600, description="Connection recycle time in seconds")
    pool_pre_ping: bool = Field(default=True, description="Pre-ping connections")
    pool_timeout: int = Field(default=30, description="Pool timeout in seconds")
    
    # Pool limits
    max_connections: int = Field(default=100, description="Maximum total connections")
    min_connections: int = Field(default=5, description="Minimum connections")


class HealthCheckConfig(BaseModel):
    """Database health check configuration."""
    
    enabled: bool = Field(default=True, description="Enable health checks")
    interval: int = Field(default=30, description="Health check interval in seconds")
    timeout: int = Field(default=5, description="Health check timeout in seconds")
    query: str = Field(default="SELECT 1", description="Health check query")
    
    # Alert thresholds
    connection_time_threshold_ms: float = Field(default=1000.0, description="Connection time threshold")
    error_rate_threshold: float = Field(default=0.1, description="Error rate threshold")
    pool_utilization_threshold: float = Field(default=0.8, description="Pool utilization threshold")


class MigrationConfig(BaseModel):
    """Database migration configuration."""
    
    auto_migrate: bool = Field(default=False, description="Enable automatic migrations")
    timeout: int = Field(default=300, description="Migration timeout in seconds")
    backup_before_migrate: bool = Field(default=True, description="Backup before migration")
    
    # Version management
    target_version: Optional[str] = Field(default=None, description="Target migration version")
    allow_downgrade: bool = Field(default=False, description="Allow downgrade migrations")


class DatabaseConfig(BaseModel):
    """Complete database configuration."""
    
    # Database type and connection
    database_type: DatabaseType = Field(description="Database type")
    connection: ConnectionConfig = Field(description="Connection configuration")
    
    # Pool configuration
    pool: PoolConfig = Field(description="Connection pool configuration")
    
    # Health check configuration
    health_check: HealthCheckConfig = Field(description="Health check configuration")
    
    # Migration configuration
    migration: MigrationConfig = Field(description="Migration configuration")
    
    # Performance settings
    echo: bool = Field(default=False, description="Enable query logging")
    slow_query_threshold_ms: float = Field(default=1000.0, description="Slow query threshold")
    
    # Backup settings
    backup_enabled: bool = Field(default=False, description="Enable automatic backups")
    backup_interval_hours: int = Field(default=24, description="Backup interval in hours")
    backup_retention_days: int = Field(default=7, description="Backup retention days")


class DatabaseStats(BaseModel):
    """Database statistics."""
    
    # Connection stats
    total_connections: int = Field(default=0, description="Total connections")
    active_connections: int = Field(default=0, description="Active connections")
    idle_connections: int = Field(default=0, description="Idle connections")
    
    # Performance stats
    avg_connection_time_ms: float = Field(default=0.0, description="Average connection time")
    connection_errors: int = Field(default=0, description="Connection errors")
    slow_queries: int = Field(default=0, description="Slow query count")
    
    # Pool stats
    pool_utilization: float = Field(default=0.0, description="Pool utilization")
    pool_hit_rate: float = Field(default=0.0, description="Pool hit rate")
    pool_miss_rate: float = Field(default=0.0, description="Pool miss rate")
    
    # Timestamps
    last_health_check: Optional[str] = Field(default=None, description="Last health check")
    last_error: Optional[str] = Field(default=None, description="Last error timestamp")


class TransactionConfig(BaseModel):
    """Transaction configuration."""
    
    isolation_level: str = Field(default="READ_COMMITTED", description="Transaction isolation level")
    timeout: int = Field(default=30000, description="Transaction timeout in milliseconds")
    retry_attempts: int = Field(default=3, description="Retry attempts")
    retry_delay: float = Field(default=1.0, description="Retry delay in seconds")
    
    # Deadlock handling
    deadlock_timeout: int = Field(default=5000, description="Deadlock timeout in milliseconds")
    deadlock_retry_attempts: int = Field(default=3, description="Deadlock retry attempts")
