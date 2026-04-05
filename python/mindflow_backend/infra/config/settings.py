"""Main application settings and configuration.

Centralized configuration management with Pydantic validation,
environment variable support, and modular organization.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

import pydantic
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from mindflow_backend.infra.config.cache import CacheConfig
from mindflow_backend.infra.config.database import DatabaseConfig
from mindflow_backend.infra.config.monitoring import MonitoringConfig


class SecurityConfig(BaseSettings):
    """Security configuration for secure storage and encryption.

    Features:
    - Secret pepper for key derivation
    - Environment variable support
    - Validation for production environments
    """

    model_config = SettingsConfigDict(
        env_prefix="MINDFLOW_",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    secret_pepper: str | None = Field(
        default=None,
        alias="SECRET_PEPPER",
        description="Random pepper for secret storage encryption (required in production)",
    )

    @field_validator("secret_pepper")
    @classmethod
    def validate_pepper(cls, v: str | None, info: pydantic.FieldValidationInfo) -> str | None:
        """Validate that pepper is set in production."""
        # Get app_env from parent Settings if available
        app_env = info.data.get("app_env", "development")
        if app_env == "production" and not v:
            raise ValueError(
                "SECRET_PEPPER must be set in production environment. "
                "Generate a random value: python -c 'import secrets; print(secrets.token_hex(32))'"
            )
        return v


class Settings(BaseSettings):
    """Main application settings with comprehensive configuration.
    
    Features:
    - Environment variable support with aliases
    - Pydantic validation
    - Modular configuration sections
    - Environment-specific defaults
    """
    
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env"),
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
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_global: int = Field(default=100, alias="RATE_LIMIT_GLOBAL")
    rate_limit_chat_stream: int = Field(default=20, alias="RATE_LIMIT_CHAT_STREAM")
    rate_limit_shell: int = Field(default=5, alias="RATE_LIMIT_SHELL")
    rate_limit_window_seconds: int = Field(default=60, alias="RATE_LIMIT_WINDOW_SECONDS")

    # Authentication Configuration
    auth_enabled: bool = Field(default=False, alias="AUTH_ENABLED")
    auth_master_key: str | None = Field(default=None, alias="AUTH_MASTER_KEY", repr=False)
    auth_token_expiry_hours: int = Field(default=24, alias="AUTH_TOKEN_EXPIRY_HOURS")
    security_trusted_hosts: str = Field(default="", alias="SECURITY_TRUSTED_HOSTS")
    security_trust_proxy_headers: bool = Field(default=False, alias="SECURITY_TRUST_PROXY_HEADERS")
    security_trusted_proxy_ips: str = Field(default="", alias="SECURITY_TRUSTED_PROXY_IPS")
    security_require_json_content_type: bool = Field(
        default=True, alias="SECURITY_REQUIRE_JSON_CONTENT_TYPE"
    )
    security_enforce_accept_header: bool = Field(
        default=True, alias="SECURITY_ENFORCE_ACCEPT_HEADER"
    )

    # Filesystem sandbox configuration
    working_path: str | None = Field(default=None, alias="WORKING_PATH")

    # AI/ML Configuration
    default_provider: str = Field(default="google", alias="DEFAULT_PROVIDER")
    default_model: str = Field(default="gemini-3.1-flash-lite-preview", alias="DEFAULT_MODEL")
    enable_decomposition_thinking: bool = Field(default=False, alias="ENABLE_DECOMPOSITION_THINKING")
    agent_stream_timeout_seconds: float = Field(default=180.0, alias="AGENT_STREAM_TIMEOUT_SECONDS")
    agent_stream_initial_timeout_seconds: float = Field(
        default=300.0,
        alias="AGENT_STREAM_INITIAL_TIMEOUT_SECONDS",
    )
    agent_stream_tool_progress_timeout_seconds: float = Field(
        default=300.0,
        alias="AGENT_STREAM_TOOL_PROGRESS_TIMEOUT_SECONDS",
    )
    agent_stream_progress_heartbeat_seconds: float = Field(
        default=5.0,
        alias="AGENT_STREAM_PROGRESS_HEARTBEAT_SECONDS",
    )
    
    # Memory Configuration
    memory_enabled: bool = Field(default=True, alias="MEMORY_ENABLED")
    memory_summary_window_tokens: int = Field(default=300000, alias="MEMORY_SUMMARY_WINDOW_TOKENS")
    memory_retrieval_top_k: int = Field(default=4, alias="MEMORY_RETRIEVAL_TOP_K")
    # DEPRECATED — use embedding_dims (EMBEDDING_DIMS) instead
    memory_embedding_dims: int = Field(default=768, alias="MEMORY_EMBEDDING_DIMS")

    # Embedding Provider Configuration (EmbeddingProviderFactory)
    embedding_backend: str = Field(default="ollama", alias="EMBEDDING_BACKEND")
    embedding_model_name: str = Field(default="qwen3-embedding:8b", alias="EMBEDDING_MODEL_NAME")
    embedding_dims: int = Field(default=768, alias="EMBEDDING_DIMS")
    memory_block_max_messages: int = Field(default=8, alias="MEMORY_BLOCK_MAX_MESSAGES")
    memory_block_max_tokens: int = Field(default=1200, alias="MEMORY_BLOCK_MAX_TOKENS")
    memory_block_topic_shift_threshold: float = Field(
        default=0.45,
        alias="MEMORY_BLOCK_TOPIC_SHIFT_THRESHOLD",
    )

    # AI Provider Configuration
    # repr=False prevents API keys from appearing in repr() / logs / error tracebacks
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY", repr=False)
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY", repr=False)
    google_api_key: str | None = Field(default=None, alias="GOOGLE_API_KEY", repr=False)
    google_application_credentials: str | None = Field(
        default=None, alias="GOOGLE_APPLICATION_CREDENTIALS", repr=False
    )
    vertexai_credentials_path: str | None = Field(default=None, alias="VERTEXAI_CREDENTIALS_PATH", repr=False)
    google_cloud_project: str | None = Field(default=None, alias="GOOGLE_CLOUD_PROJECT")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    kuzudb_url: str = Field(default="http://localhost:8001", alias="KUZUDB_URL")

    # Context Governance Configuration
    enable_input_normalization: bool = Field(default=False, alias="ENABLE_INPUT_NORMALIZATION")
    enable_context_governance: bool = Field(default=False, alias="ENABLE_CONTEXT_GOVERNANCE")
    enable_session_chunks: bool = Field(default=False, alias="ENABLE_SESSION_CHUNKS")
    chunk_target_tokens: int = Field(default=3000, alias="CHUNK_TARGET_TOKENS")
    
    # Planning Configuration
    enable_llm_planning_trigger: bool = Field(
        default=False,
        alias="ENABLE_LLM_PLANNING_TRIGGER",
        description="Enable LLM-based semantic planning trigger (replaces keyword matching)"
    )

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
    # DEPRECATED — use embedding_dims (EMBEDDING_DIMS) instead
    vector_db_dimensions: int = Field(default=768, alias="VECTOR_DB_DIMENSIONS")
    vector_db_api_key: str | None = Field(default=None, alias="VECTOR_DB_API_KEY")

    # Task Configuration
    enable_tasks_v2: bool = Field(default=False, alias="ENABLE_TASKS_V2")

    # RabbitMQ Configuration
    rabbitmq_url: str = Field(default="amqp://guest:guest@127.0.0.1:5672/", alias="RABBITMQ_URL")

    # XMPP / SPADE Communication Configuration (Fase 4)
    use_xmpp_transport: bool = Field(default=False, alias="USE_XMPP_TRANSPORT")
    # DEPRECATED — use routing_mode="hybrid" instead; kept for backward compatibility
    use_decentralized_router: bool = Field(default=False, alias="USE_DECENTRALIZED_ROUTER")
    proposal_timeout: float = Field(default=5.0, alias="PROPOSAL_TIMEOUT")
    xmpp_server: str = Field(default="localhost", alias="XMPP_SERVER")
    xmpp_port: int = Field(default=5222, alias="XMPP_PORT")
    xmpp_domain: str = Field(default="mindflow.local", alias="XMPP_DOMAIN")
    xmpp_use_tls: bool = Field(default=False, alias="XMPP_USE_TLS")
    xmpp_admin: str = Field(default="admin@mindflow.local", alias="XMPP_ADMIN")
    xmpp_admin_password: str = Field(default="mindflow_dev_pass", alias="XMPP_ADMIN_PASSWORD", repr=False)
    rabbitmq_host: str = Field(default="127.0.0.1", alias="RABBITMQ_HOST")
    rabbitmq_port: int = Field(default=5672, alias="RABBITMQ_PORT")
    rabbitmq_username: str = Field(default="guest", alias="RABBITMQ_USERNAME")
    rabbitmq_password: str = Field(default="guest", alias="RABBITMQ_PASSWORD")
    rabbitmq_virtual_host: str = Field(default="/", alias="RABBITMQ_VIRTUAL_HOST")
    enable_rabbitmq: bool = Field(default=False, alias="ENABLE_RABBITMQ")
    queue_memory_pipeline: bool = Field(default=False, alias="QUEUE_MEMORY_PIPELINE")
    queue_session_review: bool = Field(default=False, alias="QUEUE_SESSION_REVIEW")
    queue_research_pipeline: bool = Field(default=False, alias="QUEUE_RESEARCH_PIPELINE")

    # Hybrid Routing Configuration (Two-Tier Router)
    # Confidence threshold: requests above this skip the auction and delegate directly
    hybrid_confidence_threshold: float = Field(
        default=0.6, alias="HYBRID_CONFIDENCE_THRESHOLD"
    )
    # Timeout for targeted auction (Tier 2 with hint_agents — shorter due to pre-filtering)
    hybrid_auction_timeout: float = Field(
        default=3.0, alias="HYBRID_AUCTION_TIMEOUT"
    )
    # Whether to use squad templates for known multi-agent patterns
    hybrid_squad_templates_enabled: bool = Field(
        default=True, alias="HYBRID_SQUAD_TEMPLATES_ENABLED"
    )


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
    grpc_transport_mode: str = Field(default="local", alias="GRPC_TRANSPORT_MODE")

    # Feature Flags
    feature_flags: dict[str, bool] = Field(default_factory=dict)

    # PinchTab browser fleet
    pinchtab_browser_image: str = Field(
        default="mindflow/pinchtab-browser:latest",
        alias="PINCHTAB_BROWSER_IMAGE",
    )
    pinchtab_docker_network: str = Field(
        default="mindflow_default",
        alias="PINCHTAB_DOCKER_NETWORK",
    )
    pinchtab_default_economy_mode: str = Field(
        default="warm_paused",
        alias="PINCHTAB_DEFAULT_ECONOMY_MODE",
    )
    pinchtab_idle_timeout_seconds: int = Field(
        default=120,
        alias="PINCHTAB_IDLE_TIMEOUT_SECONDS",
    )
    pinchtab_max_browsers_per_session: int = Field(
        default=5,
        alias="PINCHTAB_MAX_BROWSERS_PER_SESSION",
    )
    pinchtab_reconcile_on_startup: bool = Field(
        default=True,
        alias="PINCHTAB_RECONCILE_ON_STARTUP",
    )
    
    # Modular Configuration Sections
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)

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
    def canonical_embedding_dims(self) -> int:
        """Canonical embedding dimension — single source of truth (768)."""
        return self.embedding_dims

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
        queue_flag_mapping = {
            "rabbitmq_enabled": self.enable_rabbitmq,
            "rabbitmq_memory_pipeline_enabled": self.enable_rabbitmq and self.queue_memory_pipeline,
            "rabbitmq_session_review_pipeline_enabled": self.enable_rabbitmq and self.queue_session_review,
            "rabbitmq_research_pipeline_enabled": self.enable_rabbitmq and self.queue_research_pipeline,
        }
        if flag_name in queue_flag_mapping:
            return queue_flag_mapping[flag_name]
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

    def get_trusted_hosts_list(self) -> list[str]:
        """Get trusted hosts as list."""
        return [host.strip() for host in self.security_trusted_hosts.split(",") if host.strip()]

    def get_trusted_proxy_ips_list(self) -> list[str]:
        """Get trusted proxy IPs/networks as list."""
        return [item.strip() for item in self.security_trusted_proxy_ips.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance.
    
    Returns:
        Settings instance with configuration loaded.
    """
    return Settings()


def load_hooks_on_startup(settings_path: str, plugin_dirs: list[str] | None = None) -> int:
    """Carrega todos os hooks na inicialização do sistema.

    Ordem de carregamento:
    1. Builtin hooks (format, lint, test, git safety)
    2. Config hooks (settings.yaml)
    3. Plugin hooks (plugins/*/hooks.json)

    Returns:
        Número total de hooks registrados.
    """
    from pathlib import Path

    from mindflow_backend.hooks.builtin import register_builtin_hooks
    from mindflow_backend.hooks.config_loader import load_hooks_from_settings
    from mindflow_backend.hooks.plugin_loader import load_plugin_hooks
    from mindflow_backend.infra.logging import get_logger

    logger = get_logger(__name__)
    total = 0

    # 1. Builtin hooks
    total += register_builtin_hooks()

    # 2. Config hooks (settings.yaml)
    total += load_hooks_from_settings(settings_path)

    # 3. Plugin hooks
    if plugin_dirs:
        for plugin_dir in plugin_dirs:
            plugin_name = Path(plugin_dir).name
            total += load_plugin_hooks(plugin_name, plugin_dir)

    logger.info("all_hooks_loaded", total=total)
    return total
