"""Main application settings and configuration.

Centralized configuration management with Pydantic validation,
environment variable support, and modular organization.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator,  Field, validator, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from mindflow_backend.infra.config.database import DatabaseConfig
from mindflow_backend.infra.config.cache import CacheConfig
from mindflow_backend.infra.config.monitoring import MonitoringConfig


class Settings(BaseSettings):
    """Main application settings with comprehensive configuration.
    
    Features:
    - Environment variable support with aliases
    - Pydantic validation
    - Modular configuration sections
    - Environment-specific defaults
    """
    
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8", 
        extra="ignore",
        case_sensitive=False,
    )

    # Core Application Settings
    app_name: str = Field(default="MindFlow Python Backend", alias="APP_NAME")
    app_env: Literal["development", "production", "test"] = Field(
        default="development", alias="APP_ENV"
    )
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    
    # CORS Configuration
    cors_allow_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
        alias="CORS_ALLOW_ORIGINS",
    )
    cors_allow_methods: str = Field(default="*", alias="CORS_ALLOW_METHODS")
    cors_allow_headers: str = Field(default="*", alias="CORS_ALLOW_HEADERS")
    cors_allow_credentials: bool = Field(default=False, alias="CORS_ALLOW_CREDENTIALS")
    cors_expose_headers: str = Field(default="", alias="CORS_EXPOSE_HEADERS")

    # Logging Configuration
    log_format: Literal["json", "console"] = Field(default="console", alias="LOG_FORMAT")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", alias="LOG_LEVEL"
    )
    log_sampling_rate: float = Field(default=1.0, alias="LOG_SAMPLING_RATE")
    
    # Rate Limiting Configuration
    rate_limit_enabled: bool = Field(default=False, alias="RATE_LIMIT_ENABLED")
    rate_limit_global: int = Field(default=100, alias="RATE_LIMIT_GLOBAL")
    rate_limit_chat_stream: int = Field(default=20, alias="RATE_LIMIT_CHAT_STREAM")
    rate_limit_window_seconds: int = Field(default=60, alias="RATE_LIMIT_WINDOW_SECONDS")

    # Authentication Configuration
    auth_enabled: bool = Field(default=False, alias="AUTH_ENABLED")
    auth_master_key: str | None = Field(default=None, alias="AUTH_MASTER_KEY")
    auth_token_expiry_hours: int = Field(default=24, alias="AUTH_TOKEN_EXPIRY_HOURS")

    # AI/ML Configuration
    default_provider: str = Field(default="vertexai", alias="DEFAULT_PROVIDER")
    default_model: str = Field(default="gemini-3-flash-preview", alias="DEFAULT_MODEL")
    enable_decomposition_thinking: bool = Field(default=False, alias="ENABLE_DECOMPOSITION_THINKING")
    
    # Memory Configuration
    memory_enabled: bool = Field(default=True, alias="MEMORY_ENABLED")
    memory_summary_window_tokens: int = Field(default=300000, alias="MEMORY_SUMMARY_WINDOW_TOKENS")
    memory_retrieval_top_k: int = Field(default=4, alias="MEMORY_RETRIEVAL_TOP_K")
    memory_embedding_dims: int = Field(default=256, alias="MEMORY_EMBEDDING_DIMS")

    # Embedding Provider Configuration (EmbeddingProviderFactory)
    embedding_backend: str = Field(default="gemini", alias="EMBEDDING_BACKEND")
    embedding_model_name: str = Field(default="models/text-embedding-004", alias="EMBEDDING_MODEL_NAME")
    embedding_dims: int = Field(default=768, alias="EMBEDDING_DIMS")

    # AI Provider Configuration
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    google_api_key: str | None = Field(default=None, alias="GOOGLE_API_KEY")
    google_application_credentials: str | None = Field(
        default=None, alias="GOOGLE_APPLICATION_CREDENTIALS"
    )
    vertexai_credentials_path: str | None = Field(default=None, alias="VERTEXAI_CREDENTIALS_PATH")
    google_cloud_project: str | None = Field(default=None, alias="GOOGLE_CLOUD_PROJECT")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")

    # Context Governance Configuration
    enable_input_normalization: bool = Field(default=False, alias="ENABLE_INPUT_NORMALIZATION")
    enable_context_governance: bool = Field(default=False, alias="ENABLE_CONTEXT_GOVERNANCE")
    enable_session_chunks: bool = Field(default=False, alias="ENABLE_SESSION_CHUNKS")
    chunk_target_tokens: int = Field(default=3000, alias="CHUNK_TARGET_TOKENS")

    # Execution Window Configuration
    execution_window_size: int = Field(default=10000, alias="EXECUTION_WINDOW_SIZE")
    execution_window_tracking: bool = Field(default=True, alias="EXECUTION_WINDOW_TRACKING")
    context_analysis_window: int = Field(default=100000, alias="CONTEXT_ANALYSIS_WINDOW")
    context_analysis_max_window: int = Field(default=200000, alias="CONTEXT_ANALYSIS_MAX_WINDOW")

    # Vector Database Configuration
    vector_db_provider: Literal["pgvector", "qdrant", "chroma"] = Field(
        default="pgvector", alias="VECTOR_DB_PROVIDER"
    )
    vector_db_url: str | None = Field(default=None, alias="VECTOR_DB_URL")
    vector_db_dimensions: int = Field(default=256, alias="VECTOR_DB_DIMENSIONS")
    vector_db_api_key: str | None = Field(default=None, alias="VECTOR_DB_API_KEY")

    # Task Configuration
    enable_tasks_v2: bool = Field(default=False, alias="ENABLE_TASKS_V2")

    # Semantic Search Configuration
    enable_semantic_search: bool = Field(default=True, alias="ENABLE_SEMANTIC_SEARCH")
    multilingual_embedding_model: str = Field(
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", 
        alias="MULTILINGUAL_EMBEDDING_MODEL"
    )
    context_similarity_threshold: float = Field(default=0.7, alias="CONTEXT_SIMILARITY_THRESHOLD")
    max_context_wait_time: int = Field(default=30, alias="MAX_CONTEXT_WAIT_TIME")
    enable_context_caching: bool = Field(default=True, alias="ENABLE_CONTEXT_CACHING")
    context_cache_ttl: int = Field(default=3600, alias="CONTEXT_CACHE_TTL")
    embedding_batch_size: int = Field(default=32, alias="EMBEDDING_BATCH_SIZE")
    semantic_context_limit: int = Field(default=10, alias="SEMANTIC_CONTEXT_LIMIT")

    # gRPC Configuration
    grpc_enabled: bool = Field(default=True, alias="GRPC_ENABLED")
    grpc_auto_start: bool = Field(default=True, alias="GRPC_AUTO_START")
    grpc_host: str = Field(default="0.0.0.0", alias="GRPC_HOST")
    grpc_port: int = Field(default=50051, alias="GRPC_PORT")
    grpc_tls_cert_path: str | None = Field(default=None, alias="GRPC_TLS_CERT_PATH")
    grpc_tls_key_path: str | None = Field(default=None, alias="GRPC_TLS_KEY_PATH")
    grpc_tls_ca_path: str | None = Field(default=None, alias="GRPC_TLS_CA_PATH")
    grpc_secure: bool = Field(default=False, alias="GRPC_SECURE")
    grpc_max_connections: int = Field(default=100, alias="GRPC_MAX_CONNECTIONS")
    grpc_connection_timeout_seconds: int = Field(default=30, alias="GRPC_CONNECTION_TIMEOUT_SECONDS")
    grpc_max_attempts: int = Field(default=3, alias="GRPC_MAX_ATTEMPTS")
    grpc_default_timeout_seconds: int = Field(default=300, alias="GRPC_DEFAULT_TIMEOUT_SECONDS")
    grpc_enable_metrics: bool = Field(default=True, alias="GRPC_ENABLE_METRICS")
    grpc_enable_health_check: bool = Field(default=True, alias="GRPC_ENABLE_HEALTH_CHECK")
    grpc_health_check_interval_seconds: int = Field(default=30, alias="GRPC_HEALTH_CHECK_INTERVAL_SECONDS")
    grpc_reflection_enabled: bool = Field(default=False, alias="GRPC_REFLECTION_ENABLED")
    
    # gRPC Monitoring Configuration
    grpc_prometheus_port: int = Field(default=9090, alias="GRPC_PROMETHEUS_PORT")
    grpc_metrics_history_size: int = Field(default=1000, alias="GRPC_METRICS_HISTORY_SIZE")
    grpc_system_metrics_interval: int = Field(default=5, alias="GRPC_SYSTEM_METRICS_INTERVAL")
    
    # gRPC Resilience Configuration
    grpc_circuit_breaker_enabled: bool = Field(default=True, alias="GRPC_CIRCUIT_BREAKER_ENABLED")
    grpc_circuit_breaker_threshold: int = Field(default=5, alias="GRPC_CIRCUIT_BREAKER_THRESHOLD")
    grpc_circuit_breaker_recovery_timeout: int = Field(default=60, alias="GRPC_CIRCUIT_BREAKER_RECOVERY_TIMEOUT")
    grpc_circuit_breaker_success_threshold: int = Field(default=3, alias="GRPC_CIRCUIT_BREAKER_SUCCESS_THRESHOLD")
    grpc_retry_jitter: bool = Field(default=True, alias="GRPC_RETRY_JITTER")
    grpc_retry_max_delay: int = Field(default=10, alias="GRPC_RETRY_MAX_DELAY")
    grpc_timeout_adaptive: bool = Field(default=True, alias="GRPC_TIMEOUT_ADAPTIVE")
    grpc_timeout_deadline_propagation: bool = Field(default=True, alias="GRPC_TIMEOUT_DEADLINE_PROPAGATION")

    # Feature Flags
    feature_flags: dict[str, bool] = Field(default_factory=dict)
    
    # Modular Configuration Sections
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)

    @field_validator("database", mode="before", check_fields=False)
    def assemble_database_config(cls, v: DatabaseConfig | dict | None, info: pydantic.ValidationInfo) -> DatabaseConfig:
        """Assemble database configuration from environment variables."""
        if isinstance(v, DatabaseConfig):
            return v
            
        # Extract database URL from main settings for backward compatibility
        database_url = info.parent.database_url
        if database_url:
            if v is None:
                v = {}
            v["url"] = database_url
            
        return DatabaseConfig(**(v or {}))

    @field_validator("cache", mode="before", check_fields=False)
    def assemble_cache_config(cls, v: CacheConfig | dict | None, info: pydantic.ValidationInfo) -> CacheConfig:
        """Assemble cache configuration from environment variables."""
        if isinstance(v, CacheConfig):
            return v
            
        # Extract Redis configuration from main settings for backward compatibility
        redis_url = info.parent.redis_url
        if redis_url:
            if v is None:
                v = {}
            v["redis_url"] = redis_url
            
        return CacheConfig(**(v or {}))

    @field_validator("monitoring", mode="before", check_fields=False)
    def assemble_monitoring_config(cls, v: MonitoringConfig | dict | None, info: pydantic.ValidationInfo) -> MonitoringConfig:
        """Assemble monitoring configuration from environment variables."""
        if isinstance(v, MonitoringConfig):
            return v
        return MonitoringConfig(**(v or {}))

    @field_validator("feature_flags", mode="before")
    def parse_feature_flags(cls, v: str | dict[str, bool] | None, info: pydantic.ValidationInfo) -> dict[str, bool]:
        """Parse feature flags from environment variables."""
        if isinstance(v, dict):
            return v
            
        if isinstance(v, str):
            # Parse comma-separated key=value pairs
            flags = {}
            for pair in v.split(","):
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    flags[key.strip()] = value.strip().lower() in ("true", "1", "yes", "on")
            return flags
            
        return {}

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env == "production"

    @property
    def is_test(self) -> bool:
        """Check if running in test environment."""
        return self.app_env == "test"

    def get_feature_flag(self, flag_name: str, default: bool = False) -> bool:
        """Get feature flag value.
        
        Args:
            flag_name: Name of the feature flag
            default: Default value if flag not found
            
        Returns:
            Feature flag value.
        """
        return self.feature_flags.get(flag_name, default)

    def set_feature_flag(self, flag_name: str, value: bool) -> None:
        """Set feature flag value.
        
        Args:
            flag_name: Name of the feature flag
            value: Feature flag value
        """
        self.feature_flags[flag_name] = value

    def get_cors_origins_list(self) -> list[str]:
        """Get CORS origins as list.
        
        Returns:
            List of CORS origins.
        """
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]

    def get_cors_methods_list(self) -> list[str]:
        """Get CORS methods as list.
        
        Returns:
            List of CORS methods.
        """
        return [method.strip() for method in self.cors_allow_methods.split(",") if method.strip()]

    def get_cors_headers_list(self) -> list[str]:
        """Get CORS headers as list.
        
        Returns:
            List of CORS headers.
        """
        return [header.strip() for header in self.cors_allow_headers.split(",") if header.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance.
    
    Returns:
        Settings instance with configuration loaded.
    """
    return Settings()
