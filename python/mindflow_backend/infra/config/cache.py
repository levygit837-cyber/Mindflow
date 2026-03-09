"""Cache configuration settings.

Provides comprehensive cache configuration with Redis settings,
cache hierarchy, and performance optimization.
"""

from __future__ import annotations

from typing import Optional, Dict, Any
from pydantic import field_validator,  Field, validator
from pydantic_settings import BaseSettings


class CacheConfig(BaseSettings):
    """Cache configuration with comprehensive settings.
    
    Features:
    - Redis configuration
    - Cache hierarchy settings
    - Performance optimization
    - Cache invalidation
    - Monitoring and metrics
    """
    
    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    redis_username: Optional[str] = Field(default=None, description="Redis username")
    
    # Connection Pool Configuration
    redis_pool_size: int = Field(default=10, description="Redis connection pool size")
    redis_max_connections: int = Field(default=50, description="Maximum Redis connections")
    redis_timeout: int = Field(default=5, description="Redis connection timeout in seconds")
    redis_socket_timeout: int = Field(default=5, description="Redis socket timeout in seconds")
    redis_socket_connect_timeout: int = Field(default=5, description="Redis connect timeout in seconds")
    
    # SSL Configuration
    redis_ssl: bool = Field(default=False, description="Enable Redis SSL")
    redis_ssl_cert_reqs: str = Field(default="required", description="Redis SSL certificate requirements")
    redis_ssl_ca_certs: Optional[str] = Field(default=None, description="Redis SSL CA certificates path")
    redis_ssl_certfile: Optional[str] = Field(default=None, description="Redis SSL certificate file path")
    redis_ssl_keyfile: Optional[str] = Field(default=None, description="Redis SSL key file path")
    
    # Cache Hierarchy Configuration
    enable_l1_cache: bool = Field(default=True, description="Enable L1 (memory) cache")
    enable_l2_cache: bool = Field(default=True, description="Enable L2 (Redis) cache")
    l1_cache_size: int = Field(default=1000, description="L1 cache maximum items")
    l1_cache_ttl: int = Field(default=300, description="L1 cache TTL in seconds")
    l2_cache_ttl: int = Field(default=3600, description="L2 cache TTL in seconds")
    
    # Cache Performance Configuration
    default_ttl: int = Field(default=3600, description="Default cache TTL in seconds")
    max_ttl: int = Field(default=86400, description="Maximum cache TTL in seconds")
    min_ttl: int = Field(default=60, description="Minimum cache TTL in seconds")
    
    # Cache Key Configuration
    key_prefix: str = Field(default="mindflow:", description="Cache key prefix")
    key_separator: str = Field(default=":", description="Cache key separator")
    max_key_length: int = Field(default=250, description="Maximum cache key length")
    
    # Cache Invalidation Configuration
    enable_auto_invalidation: bool = Field(default=True, description="Enable automatic cache invalidation")
    invalidation_batch_size: int = Field(default=100, description="Invalidation batch size")
    invalidation_delay: float = Field(default=0.1, description="Invalidation delay in seconds")
    
    # Cache Warming Configuration
    enable_cache_warming: bool = Field(default=False, description="Enable cache warming")
    warming_batch_size: int = Field(default=50, description="Cache warming batch size")
    warming_interval: int = Field(default=3600, description="Cache warming interval in seconds")
    
    # Cache Monitoring Configuration
    enable_metrics: bool = Field(default=True, description="Enable cache metrics")
    metrics_interval: int = Field(default=60, description="Metrics collection interval in seconds")
    slow_query_threshold_ms: float = Field(default=100.0, description="Slow cache query threshold in milliseconds")
    
    # Cache Compression Configuration
    enable_compression: bool = Field(default=False, description="Enable cache compression")
    compression_threshold: int = Field(default=1024, description="Compression threshold in bytes")
    compression_algorithm: str = Field(default="gzip", description="Compression algorithm")
    
    # Cache Serialization Configuration
    enable_pickle: bool = Field(default=True, description="Enable pickle serialization")
    enable_json: bool = Field(default=True, description="Enable JSON serialization")
    default_serializer: str = Field(default="pickle", description="Default serializer")
    
    # Redis Cluster Configuration
    enable_cluster: bool = Field(default=False, description="Enable Redis cluster")
    cluster_nodes: str = Field(default="", description="Redis cluster nodes (comma-separated)")
    cluster_max_connections_per_node: int = Field(default=16, description="Max connections per cluster node")
    
    # Redis Sentinel Configuration
    enable_sentinel: bool = Field(default=False, description="Enable Redis sentinel")
    sentinel_hosts: str = Field(default="", description="Redis sentinel hosts (comma-separated)")
    sentinel_service_name: str = Field(default="mymaster", description="Redis sentinel service name")
    
    # Cache Health Configuration
    health_check_enabled: bool = Field(default=True, description="Enable cache health checks")
    health_check_interval: int = Field(default=30, description="Health check interval in seconds")
    health_check_timeout: int = Field(default=5, description="Health check timeout in seconds")
    
    # Cache Debugging Configuration
    debug_mode: bool = Field(default=False, description="Enable cache debugging")
    log_cache_operations: bool = Field(default=False, description="Log cache operations")
    log_cache_keys: bool = Field(default=False, description="Log cache keys (security risk)")

    @field_validator("redis_url", mode="before")
    def build_redis_url_from_components(cls, v: str, info: pydantic.ValidationInfo) -> str:
        """Build Redis URL from individual components if URL not provided."""
        if v:
            return v
            
        # Build URL from components
        host = values.get("redis_host") or "localhost"
        port = values.get("redis_port") or 6379
        db = values.get("redis_db") or 0
        password = values.get("redis_password")
        username = values.get("redis_username")
        
        # Build URL
        if username:
            auth_part = f"{username}:{password}@" if password else f"{username}@"
        else:
            auth_part = f":{password}@" if password else ""
            
        url = f"redis://{auth_part}{host}:{port}/{db}"
        return url

    @field_validator("redis_ssl_cert_reqs")
    def validate_ssl_cert_reqs(cls, v: str) -> str:
        """Validate SSL certificate requirements."""
        valid_options = ["none", "optional", "required"]
        if v not in valid_options:
            raise ValueError(f"SSL cert_reqs must be one of: {valid_options}")
        return v

    @field_validator("compression_algorithm")
    def validate_compression_algorithm(cls, v: str) -> str:
        """Validate compression algorithm."""
        valid_algorithms = ["gzip", "lz4", "brotli", "zlib"]
        if v not in valid_algorithms:
            raise ValueError(f"Compression algorithm must be one of: {valid_algorithms}")
        return v

    @field_validator("default_serializer")
    def validate_default_serializer(cls, v: str) -> str:
        """Validate default serializer."""
        valid_serializers = ["pickle", "json", "msgpack", "marshal"]
        if v not in valid_serializers:
            raise ValueError(f"Default serializer must be one of: {valid_serializers}")
        return v

    @field_validator("l1_cache_ttl", "l2_cache_ttl", "default_ttl", "max_ttl", "min_ttl")
    def validate_ttl_values(cls, v: int) -> int:
        """Validate TTL values."""
        if v <= 0:
            raise ValueError("TTL values must be positive")
        return v

    @field_validator("max_ttl")
    def validate_max_ttl_greater_than_min(cls, v: int, info: pydantic.ValidationInfo) -> int:
        """Validate max_ttl is greater than min_ttl."""
        min_ttl = values.get("min_ttl", 60)
        if v <= min_ttl:
            raise ValueError(f"max_ttl ({v}) must be greater than min_ttl ({min_ttl})")
        return v

    @field_validator("default_ttl")
    def validate_default_ttl_range(cls, v: int, info: pydantic.ValidationInfo) -> int:
        """Validate default_ttl is within min/max range."""
        min_ttl = values.get("min_ttl", 60)
        max_ttl = values.get("max_ttl", 86400)
        
        if not (min_ttl <= v <= max_ttl):
            raise ValueError(f"default_ttl ({v}) must be between min_ttl ({min_ttl}) and max_ttl ({max_ttl})")
        return v

    @field_validator("l1_cache_ttl")
    def validate_l1_ttl_less_than_l2(cls, v: int, info: pydantic.ValidationInfo) -> int:
        """Validate L1 cache TTL is less than L2 cache TTL."""
        l2_ttl = values.get("l2_cache_ttl", 3600)
        if v >= l2_ttl:
            raise ValueError(f"l1_cache_ttl ({v}) should be less than l2_cache_ttl ({l2_ttl})")
        return v

    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis connection configuration.
        
        Returns:
            Dictionary with Redis configuration.
        """
        return {
            "url": self.redis_url,
            "host": self.redis_host,
            "port": self.redis_port,
            "db": self.redis_db,
            "password": self.redis_password,
            "username": self.redis_username,
            "pool_size": self.redis_pool_size,
            "max_connections": self.redis_max_connections,
            "timeout": self.redis_timeout,
            "socket_timeout": self.redis_socket_timeout,
            "socket_connect_timeout": self.redis_socket_connect_timeout,
            "ssl": self.redis_ssl,
            "ssl_cert_reqs": self.redis_ssl_cert_reqs,
            "ssl_ca_certs": self.redis_ssl_ca_certs,
            "ssl_certfile": self.redis_ssl_certfile,
            "ssl_keyfile": self.redis_ssl_keyfile,
        }

    def get_cache_hierarchy_config(self) -> Dict[str, Any]:
        """Get cache hierarchy configuration.
        
        Returns:
            Dictionary with cache hierarchy configuration.
        """
        return {
            "enable_l1": self.enable_l1_cache,
            "enable_l2": self.enable_l2_cache,
            "l1_size": self.l1_cache_size,
            "l1_ttl": self.l1_cache_ttl,
            "l2_ttl": self.l2_cache_ttl,
            "default_ttl": self.default_ttl,
            "max_ttl": self.max_ttl,
            "min_ttl": self.min_ttl,
        }

    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance optimization configuration.
        
        Returns:
            Dictionary with performance configuration.
        """
        return {
            "enable_compression": self.enable_compression,
            "compression_threshold": self.compression_threshold,
            "compression_algorithm": self.compression_algorithm,
            "enable_pickle": self.enable_pickle,
            "enable_json": self.enable_json,
            "default_serializer": self.default_serializer,
        }

    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration.
        
        Returns:
            Dictionary with monitoring configuration.
        """
        return {
            "enable_metrics": self.enable_metrics,
            "metrics_interval": self.metrics_interval,
            "slow_query_threshold_ms": self.slow_query_threshold_ms,
            "health_check_enabled": self.health_check_enabled,
            "health_check_interval": self.health_check_interval,
            "health_check_timeout": self.health_check_timeout,
            "debug_mode": self.debug_mode,
            "log_cache_operations": self.log_cache_operations,
            "log_cache_keys": self.log_cache_keys,
        }

    def get_cluster_config(self) -> Dict[str, Any]:
        """Get cluster configuration.
        
        Returns:
            Dictionary with cluster configuration.
        """
        return {
            "enable_cluster": self.enable_cluster,
            "cluster_nodes": self.cluster_nodes,
            "cluster_max_connections_per_node": self.cluster_max_connections_per_node,
            "enable_sentinel": self.enable_sentinel,
            "sentinel_hosts": self.sentinel_hosts,
            "sentinel_service_name": self.sentinel_service_name,
        }

    def build_cache_key(self, *parts: str) -> str:
        """Build cache key from parts.
        
        Args:
            *parts: Key parts to combine
            
        Returns:
            Complete cache key.
        """
        key_parts = [self.key_prefix] + list(str(part) for part in parts)
        key = self.key_separator.join(key_parts)
        
        # Truncate if too long
        if len(key) > self.max_key_length:
            # Keep prefix and add hash of full key
            prefix = key[:self.max_key_length - 33]  # Leave space for hash
            hash_part = str(hash(key))[:32]
            key = f"{prefix}{hash_part}"
            
        return key
