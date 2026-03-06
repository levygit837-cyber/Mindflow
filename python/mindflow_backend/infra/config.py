import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8", 
        extra="ignore"
    )

    app_name: str = Field(default="MindFlow Python Backend", alias="APP_NAME")
    app_env: Literal["development", "production", "test"] = Field(
        default="development", alias="APP_ENV"
    )
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    log_format: Literal["json", "console"] = Field(default="console", alias="LOG_FORMAT")
    cors_allow_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
        alias="CORS_ALLOW_ORIGINS",
    )
    cors_allow_methods: str = Field(default="*", alias="CORS_ALLOW_METHODS")
    cors_allow_headers: str = Field(default="*", alias="CORS_ALLOW_HEADERS")
    cors_allow_credentials: bool = Field(default=False, alias="CORS_ALLOW_CREDENTIALS")
    cors_expose_headers: str = Field(default="", alias="CORS_EXPOSE_HEADERS")

    database_url: str = Field(
        default="postgresql+psycopg://mindflow_app:mindflow_dev_local_2026@localhost:5433/mindflow_v1",
        alias="DATABASE_URL",
    )
    kuzudb_url: str = Field(
        default="http://localhost:8000",
        alias="KUZUDB_URL",
    )
    kuzudb_database: str = Field(
        default="mindflow_vectors",
        alias="KUZUDB_DATABASE",
    )

    # Rate limiting (feature-flagged)
    rate_limit_enabled: bool = Field(default=False, alias="RATE_LIMIT_ENABLED")
    rate_limit_global: int = Field(default=100, alias="RATE_LIMIT_GLOBAL")
    rate_limit_chat_stream: int = Field(default=20, alias="RATE_LIMIT_CHAT_STREAM")
    rate_limit_window_seconds: int = Field(default=60, alias="RATE_LIMIT_WINDOW_SECONDS")

    # Authentication (feature-flagged)
    auth_enabled: bool = Field(default=False, alias="AUTH_ENABLED")
    auth_master_key: str | None = Field(default=None, alias="AUTH_MASTER_KEY")

    default_provider: str = Field(default="vertexai", alias="DEFAULT_PROVIDER")
    default_model: str = Field(default="gemini-3-flash-preview", alias="DEFAULT_MODEL")
    enable_decomposition_thinking: bool = Field(default=False, alias="ENABLE_DECOMPOSITION_THINKING")
    memory_enabled: bool = Field(default=True, alias="MEMORY_ENABLED")
    memory_summary_window_tokens: int = Field(default=300000, alias="MEMORY_SUMMARY_WINDOW_TOKENS")
    memory_retrieval_top_k: int = Field(default=4, alias="MEMORY_RETRIEVAL_TOP_K")
    memory_embedding_dims: int = Field(default=256, alias="MEMORY_EMBEDDING_DIMS")

    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    google_api_key: str | None = Field(default=None, alias="GOOGLE_API_KEY")
    google_application_credentials: str | None = Field(
        default=None, alias="GOOGLE_APPLICATION_CREDENTIALS"
    )
    vertexai_credentials_path: str | None = Field(default=None, alias="VERTEXAI_CREDENTIALS_PATH")
    google_cloud_project: str | None = Field(default=None, alias="GOOGLE_CLOUD_PROJECT")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")

    # Phase 2 - Context Governance and Input Normalization
    enable_input_normalization: bool = Field(default=False, alias="ENABLE_INPUT_NORMALIZATION")
    enable_context_governance: bool = Field(default=False, alias="ENABLE_CONTEXT_GOVERNANCE")
    enable_session_chunks: bool = Field(default=False, alias="ENABLE_SESSION_CHUNKS")
    chunk_target_tokens: int = Field(default=3000, alias="CHUNK_TARGET_TOKENS")

    # Context Governance - Execution Window Control
    execution_window_size: int = Field(default=10000, alias="EXECUTION_WINDOW_SIZE")
    execution_window_tracking: bool = Field(default=True, alias="EXECUTION_WINDOW_TRACKING")

    # Context Governance - Context Definition Window
    context_analysis_window: int = Field(default=100000, alias="CONTEXT_ANALYSIS_WINDOW")
    context_analysis_max_window: int = Field(default=200000, alias="CONTEXT_ANALYSIS_MAX_WINDOW")

    # Vector Database Integration
    vector_db_provider: Literal["pgvector", "qdrant", "chroma"] = Field(
        default="pgvector", alias="VECTOR_DB_PROVIDER"
    )
    vector_db_url: str | None = Field(default=None, alias="VECTOR_DB_URL")
    vector_db_dimensions: int = Field(default=256, alias="VECTOR_DB_DIMENSIONS")
    vector_db_api_key: str | None = Field(default=None, alias="VECTOR_DB_API_KEY")

    # Phase 4 - Task v2
    enable_tasks_v2: bool = Field(default=False, alias="ENABLE_TASKS_V2")

    # Semantic Context and Multilingual Embeddings
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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
