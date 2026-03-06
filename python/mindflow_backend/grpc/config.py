"""gRPC configuration management with dynamic configuration support.

Handles gRPC-specific configuration including connection pooling,
timeouts, retry policies, and other gRPC settings with hot reload
and environment profile support.
"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import Field, BaseModel

from mindflow_backend.infra.config import get_settings


class GrpcConfig(BaseModel):
    """gRPC configuration settings with dynamic configuration support."""
    
    # Server settings
    enabled: bool = Field(default=True, description="Enable gRPC server")
    auto_start: bool = Field(default=True, description="Auto-start gRPC server on application startup")
    host: str = Field(default="0.0.0.0", description="gRPC server host")
    port: int = Field(default=50051, description="gRPC server port")
    
    # Security settings
    secure: bool = Field(default=False, description="Use secure connection")
    tls_cert_path: str | None = Field(default=None, description="TLS certificate path")
    tls_key_path: str | None = Field(default=None, description="TLS private key path")
    tls_ca_path: str | None = Field(default=None, description="TLS CA certificate path")
    
    # Connection settings
    max_connections: int = Field(default=100, description="Maximum concurrent connections")
    connection_timeout_seconds: int = Field(default=30, description="Connection timeout")
    keepalive_time_seconds: int = Field(default=60, description="Keepalive time")
    keepalive_timeout_seconds: int = Field(default=5, description="Keepalive timeout")
    
    # Retry settings
    max_attempts: int = Field(default=3, description="Maximum retry attempts")
    retry_backoff_multiplier: float = Field(default=2.0, description="Retry backoff multiplier")
    initial_retry_delay_ms: int = Field(default=100, description="Initial retry delay in milliseconds")
    max_retry_delay_ms: int = Field(default=1000, description="Maximum retry delay in milliseconds")
    
    # Request settings
    default_timeout_seconds: int = Field(default=300, description="Default request timeout")
    max_receive_message_length: int = Field(default=4 * 1024 * 1024, description="Max receive message size (4MB)")
    max_send_message_length: int = Field(default=4 * 1024 * 1024, description="Max send message size (4MB)")
    
    # Monitoring settings
    enable_metrics: bool = Field(default=True, description="Enable gRPC metrics collection")
    enable_health_check: bool = Field(default=True, description="Enable health check service")
    health_check_interval_seconds: int = Field(default=30, description="Health check interval")
    
    # Development settings
    debug_mode: bool = Field(default=False, description="Enable debug mode")
    reflection_enabled: bool = Field(default=False, description="Enable gRPC reflection")
    
    # Dynamic configuration settings
    profile: str = Field(default="development", description="Configuration profile")
    auto_reload: bool = Field(default=True, description="Enable automatic config reload")
    reload_interval_seconds: int = Field(default=30, description="Config reload interval")
    config_storage_backend: str = Field(default="memory", description="Storage backend")
    
    # Monitoring and resilience settings
    grpc_prometheus_port: int = Field(default=9090, description="Prometheus metrics port")
    metrics_history_size: int = Field(default=1000, description="Metrics history size")
    system_metrics_interval: int = Field(default=5, description="System metrics interval")
    circuit_breaker_enabled: bool = Field(default=True, description="Enable circuit breaker")
    circuit_breaker_threshold: int = Field(default=5, description="Circuit breaker failure threshold")
    circuit_breaker_recovery_timeout: int = Field(default=60, description="Circuit breaker recovery timeout")
    circuit_breaker_success_threshold: int = Field(default=3, description="Circuit breaker success threshold")
    retry_jitter: bool = Field(default=True, description="Enable retry jitter")
    retry_max_delay: int = Field(default=10, description="Maximum retry delay in seconds")
    timeout_adaptive: bool = Field(default=True, description="Enable adaptive timeouts")
    timeout_deadline_propagation: bool = Field(default=True, description="Enable deadline propagation")
    
    @classmethod
    def from_settings(cls) -> GrpcConfig:
        """Create GrpcConfig from application settings."""
        settings = get_settings()
        
        return cls(
            enabled=getattr(settings, 'grpc_enabled', True),
            auto_start=getattr(settings, 'grpc_auto_start', True),
            host=settings.grpc_host,
            port=settings.grpc_port,
            secure=getattr(settings, 'grpc_secure', False),
            tls_cert_path=settings.grpc_tls_cert_path,
            tls_key_path=settings.grpc_tls_key_path,
            tls_ca_path=getattr(settings, 'grpc_tls_ca_path', None),
            max_connections=getattr(settings, 'grpc_max_connections', 100),
            connection_timeout_seconds=getattr(settings, 'grpc_connection_timeout_seconds', 30),
            keepalive_time_seconds=60,  # Default value
            keepalive_timeout_seconds=5,  # Default value
            max_attempts=getattr(settings, 'grpc_max_attempts', 3),
            retry_backoff_multiplier=2.0,  # Default value
            initial_retry_delay_ms=100,  # Default value
            max_retry_delay_ms=getattr(settings, 'grpc_retry_max_delay', 10000),
            default_timeout_seconds=getattr(settings, 'grpc_default_timeout_seconds', 300),
            max_receive_message_length=4 * 1024 * 1024,  # 4MB default
            max_send_message_length=4 * 1024 * 1024,  # 4MB default
            enable_metrics=getattr(settings, 'grpc_enable_metrics', True),
            enable_health_check=getattr(settings, 'grpc_enable_health_check', True),
            health_check_interval_seconds=getattr(settings, 'grpc_health_check_interval_seconds', 30),
            debug_mode=settings.app_env == "development",
            reflection_enabled=getattr(settings, 'grpc_reflection_enabled', False),
            grpc_prometheus_port=getattr(settings, 'grpc_prometheus_port', 9090),
            metrics_history_size=getattr(settings, 'grpc_metrics_history_size', 1000),
            system_metrics_interval=getattr(settings, 'grpc_system_metrics_interval', 5),
            circuit_breaker_enabled=getattr(settings, 'grpc_circuit_breaker_enabled', True),
            circuit_breaker_threshold=getattr(settings, 'grpc_circuit_breaker_threshold', 5),
            circuit_breaker_recovery_timeout=getattr(settings, 'grpc_circuit_breaker_recovery_timeout', 60),
            circuit_breaker_success_threshold=getattr(settings, 'grpc_circuit_breaker_success_threshold', 3),
            retry_jitter=getattr(settings, 'grpc_retry_jitter', True),
            retry_max_delay=getattr(settings, 'grpc_retry_max_delay', 10),
            timeout_adaptive=getattr(settings, 'grpc_timeout_adaptive', True),
            timeout_deadline_propagation=getattr(settings, 'grpc_timeout_deadline_propagation', True),
        )
    
    @classmethod
    async def load_dynamic(cls, profile: Optional[str] = None) -> GrpcConfig:
        """Load configuration with dynamic overrides and profile support."""
        try:
            # Load base configuration
            base_config = cls.from_settings()
            
            # Apply profile if specified
            if profile:
                from mindflow_backend.grpc.config.profiles import get_environment_loader
                env_loader = get_environment_loader()
                base_config = await env_loader.load_profile_config(profile, base_config)
            
            # Apply feature flags
            from mindflow_backend.grpc.config.features import get_feature_toggles
            feature_toggles = await get_feature_toggles()
            feature_overrides = await feature_toggles.get_config_overrides()
            
            # Merge configurations
            config_dict = base_config.dict()
            config_dict.update(feature_overrides)
            
            return cls(**config_dict)
            
        except Exception as exc:
            # Fallback to static configuration
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("dynamic_config_load_failed", error=str(exc), fallback="static")
            return cls.from_settings()
    
    def apply_feature_overrides(self, overrides: Dict[str, Any]) -> GrpcConfig:
        """Apply feature flag overrides to configuration."""
        config_dict = self.dict()
        config_dict.update(overrides)
        return GrpcConfig(**config_dict)
    
    def get_effective_config(self) -> Dict[str, Any]:
        """Get effective configuration including all overrides."""
        return self.dict()
    
    def is_production_ready(self) -> bool:
        """Check if configuration is production-ready."""
        return (
            not self.debug_mode and
            not self.reflection_enabled and
            self.secure and
            self.enable_metrics and
            self.enable_health_check
        )
    
    def validate_for_environment(self, environment: str) -> List[str]:
        """Validate configuration for specific environment."""
        issues = []
        
        if environment == "production":
            if self.debug_mode:
                issues.append("Debug mode should be disabled in production")
            if self.reflection_enabled:
                issues.append("gRPC reflection should be disabled in production")
            if not self.secure:
                issues.append("TLS should be enabled in production")
            if self.max_connections < 100:
                issues.append("Max connections should be >= 100 in production")
        
        elif environment == "development":
            if self.secure and not self.tls_cert_path:
                issues.append("TLS enabled but certificate path not specified")
        
        return issues


class GrpcClientConfig(BaseModel):
    """gRPC client configuration."""
    
    # Connection settings
    host: str = Field(default="localhost", description="gRPC server host")
    port: int = Field(default=50051, description="gRPC server port")
    secure: bool = Field(default=False, description="Use secure connection")
    
    # Pool settings
    pool_size: int = Field(default=10, description="Connection pool size")
    max_pool_size: int = Field(default=50, description="Maximum connection pool size")
    pool_timeout_seconds: int = Field(default=30, description="Pool acquisition timeout")
    
    # Retry settings
    max_attempts: int = Field(default=3, description="Maximum retry attempts")
    retry_backoff_multiplier: float = Field(default=2.0, description="Retry backoff multiplier")
    initial_retry_delay_ms: int = Field(default=100, description="Initial retry delay in milliseconds")
    max_retry_delay_ms: int = Field(default=1000, description="Maximum retry delay in milliseconds")
    
    # Timeout settings
    connection_timeout_seconds: int = Field(default=30, description="Connection timeout")
    request_timeout_seconds: int = Field(default=300, description="Default request timeout")
    
    # Load balancing
    load_balancing_policy: Literal["round_robin", "pick_first", "random"] = Field(
        default="pick_first", description="Load balancing policy"
    )
    
    # Compression
    compression_algorithm: Literal["none", "gzip", "deflate"] = Field(
        default="none", description="Compression algorithm"
    )
    
    @classmethod
    def from_server_config(cls, server_config: GrpcConfig) -> GrpcClientConfig:
        """Create client config from server config."""
        return cls(
            host=server_config.host,
            port=server_config.port,
            secure=server_config.secure,
            max_attempts=server_config.max_attempts,
            retry_backoff_multiplier=server_config.retry_backoff_multiplier,
            initial_retry_delay_ms=server_config.initial_retry_delay_ms,
            max_retry_delay_ms=server_config.max_retry_delay_ms,
            connection_timeout_seconds=server_config.connection_timeout_seconds,
            request_timeout_seconds=server_config.default_timeout_seconds,
        )
