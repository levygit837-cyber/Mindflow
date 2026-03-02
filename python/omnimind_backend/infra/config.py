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

    app_name: str = Field(default="OmniMind Python Backend", alias="APP_NAME")
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
        default="postgresql+psycopg://postgres:postgres@localhost:5432/omnimind",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

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

    searxng_url: str = Field(default="http://localhost:8080", alias="SEARXNG_URL")

    # Phase 1 - Agent Contract Parity
    enable_creative_agent: bool = Field(default=False, alias="ENABLE_CREATIVE_AGENT")
    enable_security_guard_agent: bool = Field(default=False, alias="ENABLE_SECURITY_GUARD_AGENT")

    # Phase 2 - Context Governance and Input Normalization
    enable_input_normalization: bool = Field(default=False, alias="ENABLE_INPUT_NORMALIZATION")
    enable_context_governance: bool = Field(default=False, alias="ENABLE_CONTEXT_GOVERNANCE")
    enable_session_chunks: bool = Field(default=False, alias="ENABLE_SESSION_CHUNKS")

    # Phase 3 - Async Workflow Caller
    enable_async_workflows: bool = Field(default=False, alias="ENABLE_ASYNC_WORKFLOWS")
    enable_workflow_registry: bool = Field(default=False, alias="ENABLE_WORKFLOW_REGISTRY")

    # Phase 4 - DT v2
    enable_dt_v2: bool = Field(default=False, alias="ENABLE_DT_V2")

    grpc_host: str = Field(default="0.0.0.0", alias="GRPC_HOST")
    grpc_port: int = Field(default=50051, alias="GRPC_PORT")
    grpc_tls_cert_path: str | None = Field(default=None, alias="GRPC_TLS_CERT_PATH")
    grpc_tls_key_path: str | None = Field(default=None, alias="GRPC_TLS_KEY_PATH")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
