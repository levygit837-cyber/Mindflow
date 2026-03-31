"""Database configuration settings.

Provides comprehensive database configuration with connection pooling,
health monitoring, and performance optimization settings.
"""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class DatabaseConfig(BaseSettings):
    """Database configuration with comprehensive settings.
    
    Features:
    - Connection pooling configuration
    - Health check settings
    - Performance optimization
    - Security settings
    - Migration configuration
    """
    
    # Connection Configuration
    url: str = Field(
        default="postgresql+psycopg://mindflow_app:mindflow_dev_local_2026@localhost:5433/mindflow_v1",
        description="Database connection URL",
    )
    pool_size: int = Field(default=20, description="Base connection pool size")
    max_overflow: int = Field(default=30, description="Additional connections under load")
    pool_recycle: int = Field(default=3600, description="Connection recycling time in seconds")
    pool_pre_ping: bool = Field(default=True, description="Validate connections before use")
    pool_timeout: int = Field(default=30, description="Timeout for getting connection from pool")
    
    # Connection Limits
    max_connections: int = Field(default=100, description="Maximum total connections")
    min_connections: int = Field(default=5, description="Minimum connections to maintain")
    
    # Health Check Configuration
    health_check_enabled: bool = Field(default=True, description="Enable database health checks")
    health_check_interval: int = Field(default=30, description="Health check interval in seconds")
    health_check_timeout: int = Field(default=5, description="Health check timeout in seconds")
    health_check_query: str = Field(default="SELECT 1", description="Health check query")
    
    # Performance Configuration
    statement_timeout: int = Field(default=30000, description="Statement timeout in milliseconds")
    query_timeout: int = Field(default=60000, description="Query timeout in milliseconds")
    idle_in_transaction_session_timeout: int = Field(
        default=300000, 
        description="Idle transaction timeout in milliseconds"
    )
    
    # Connection Retry Configuration
    retry_attempts: int = Field(default=3, description="Maximum retry attempts")
    retry_delay: float = Field(default=1.0, description="Initial retry delay in seconds")
    retry_backoff_multiplier: float = Field(default=2.0, description="Retry backoff multiplier")
    retry_max_delay: float = Field(default=30.0, description="Maximum retry delay in seconds")
    
    # SSL Configuration
    ssl_mode: str = Field(default="prefer", description="SSL mode for connections")
    ssl_cert_file: str | None = Field(default=None, description="SSL certificate file path")
    ssl_key_file: str | None = Field(default=None, description="SSL key file path")
    ssl_ca_file: str | None = Field(default=None, description="SSL CA file path")
    
    # Logging Configuration
    echo: bool = Field(default=False, description="Enable SQL query logging")
    echo_pool: bool = Field(default=False, description="Enable connection pool logging")
    
    # Migration Configuration
    auto_migrate: bool = Field(default=False, description="Enable automatic migrations")
    migration_timeout: int = Field(default=300, description="Migration timeout in seconds")
    
    # Backup Configuration
    backup_enabled: bool = Field(default=False, description="Enable automatic backups")
    backup_interval_hours: int = Field(default=24, description="Backup interval in hours")
    backup_retention_days: int = Field(default=7, description="Backup retention period in days")
    
    # Monitoring Configuration
    metrics_enabled: bool = Field(default=True, description="Enable database metrics")
    slow_query_threshold_ms: float = Field(default=1000.0, description="Slow query threshold in milliseconds")
    
    # Security Configuration
    encrypt_connection: bool = Field(default=False, description="Encrypt database connections")
    require_ssl: bool = Field(default=False, description="Require SSL for all connections")
    
    # Connection String Components (for backward compatibility)
    host: str | None = Field(default=None, description="Database host")
    port: int | None = Field(default=None, description="Database port")
    database: str | None = Field(default=None, description="Database name")
    username: str | None = Field(default=None, description="Database username")
    password: str | None = Field(default=None, description="Database password")

    @field_validator("url", mode="before")
    @classmethod
    def build_url_from_components(cls, v: str, info: pydantic.ValidationInfo) -> str:
        """Build database URL from individual components if URL not provided."""
        if v:
            return v
            
        # Build URL from components
        data = info.data if hasattr(info, 'data') else {}
        host = data.get("host") or "localhost"
        port = data.get("port") or 5432
        database = data.get("database") or "mindflow_v1"
        username = data.get("username") or "mindflow_app"
        password = data.get("password") or "mindflow_dev_local_2026"
        
        return f"postgresql+psycopg://{username}:{password}@{host}:{port}/{database}"

    @field_validator("max_overflow")
    @classmethod
    def validate_max_overflow(cls, v: int, info: pydantic.ValidationInfo) -> int:
        """Validate max_overflow against max_connections."""
        data = info.data if hasattr(info, 'data') else {}
        max_connections = data.get("max_connections", 100)
        pool_size = data.get("pool_size", 20)
        
        if pool_size + v > max_connections:
            raise ValueError(
                f"pool_size ({pool_size}) + max_overflow ({v}) cannot exceed max_connections ({max_connections})"
            )
            
        return v

    @field_validator("min_connections")
    @classmethod
    def validate_min_connections(cls, v: int, info: pydantic.ValidationInfo) -> int:
        """Validate min_connections against max_connections."""
        data = info.data if hasattr(info, 'data') else {}
        max_connections = data.get("max_connections", 100)
        
        if v > max_connections:
            raise ValueError(
                f"min_connections ({v}) cannot exceed max_connections ({max_connections})"
            )
            
        return v

    @field_validator("retry_delay", "retry_max_delay")
    @classmethod
    def validate_retry_delays(cls, v: float) -> float:
        """Validate retry delay values."""
        if v <= 0:
            raise ValueError("Retry delays must be positive")
        return v

    @field_validator("retry_backoff_multiplier")
    def validate_backoff_multiplier(cls, v: float) -> float:
        """Validate retry backoff multiplier."""
        if v <= 1.0:
            raise ValueError("Retry backoff multiplier must be greater than 1.0")
        return v

    @field_validator("ssl_mode")
    def validate_ssl_mode(cls, v: str) -> str:
        """Validate SSL mode."""
        valid_modes = ["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]
        if v not in valid_modes:
            raise ValueError(f"SSL mode must be one of: {valid_modes}")
        return v

    @field_validator("slow_query_threshold_ms")
    def validate_slow_query_threshold(cls, v: float) -> float:
        """Validate slow query threshold."""
        if v <= 0:
            raise ValueError("Slow query threshold must be positive")
        return v

    def get_connection_string(self) -> str:
        """Get complete database connection string.
        
        Returns:
            Database connection string.
        """
        return self.url

    def get_pool_config(self) -> dict[str, any]:
        """Get connection pool configuration.
        
        Returns:
            Dictionary with pool configuration.
        """
        return {
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "pool_recycle": self.pool_recycle,
            "pool_pre_ping": self.pool_pre_ping,
            "pool_timeout": self.pool_timeout,
        }

    def get_health_check_config(self) -> dict[str, any]:
        """Get health check configuration.
        
        Returns:
            Dictionary with health check configuration.
        """
        return {
            "enabled": self.health_check_enabled,
            "interval": self.health_check_interval,
            "timeout": self.health_check_timeout,
            "query": self.health_check_query,
        }

    def get_retry_config(self) -> dict[str, any]:
        """Get retry configuration.
        
        Returns:
            Dictionary with retry configuration.
        """
        return {
            "attempts": self.retry_attempts,
            "delay": self.retry_delay,
            "backoff_multiplier": self.retry_backoff_multiplier,
            "max_delay": self.retry_max_delay,
        }

    def get_ssl_config(self) -> dict[str, any]:
        """Get SSL configuration.
        
        Returns:
            Dictionary with SSL configuration.
        """
        return {
            "mode": self.ssl_mode,
            "cert_file": self.ssl_cert_file,
            "key_file": self.ssl_key_file,
            "ca_file": self.ssl_ca_file,
            "encrypt": self.encrypt_connection,
            "require": self.require_ssl,
        }
