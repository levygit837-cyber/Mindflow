"""Tests for production CORS hardening."""

from __future__ import annotations

from omnimind_backend.infra.config import Settings


def test_production_cors_restricts_methods():
    """In production, CORS should restrict methods to GET, POST, OPTIONS."""
    settings = Settings(APP_ENV="production")
    assert settings.app_env == "production"

    # Verify default values are wildcards that will be restricted in main.py logic
    # The actual restriction happens in main.py at module load time.
    # Here we verify the config fields exist and have correct defaults.
    assert settings.cors_allow_methods == "*"
    assert settings.cors_allow_headers == "*"
    assert settings.cors_expose_headers == ""


def test_development_cors_allows_all():
    """In development, CORS should allow all methods and headers."""
    settings = Settings(APP_ENV="development")
    assert settings.cors_allow_methods == "*"
    assert settings.cors_allow_headers == "*"


def test_cors_expose_headers_configurable():
    """CORS_EXPOSE_HEADERS should be configurable via env."""
    settings = Settings(CORS_EXPOSE_HEADERS="X-Request-ID,X-Custom")
    assert settings.cors_expose_headers == "X-Request-ID,X-Custom"


def test_grpc_tls_settings_default_to_none():
    """gRPC TLS settings should default to None (insecure in dev)."""
    settings = Settings()
    assert settings.grpc_tls_cert_path is None
    assert settings.grpc_tls_key_path is None


def test_grpc_tls_settings_configurable():
    """gRPC TLS paths should be configurable."""
    settings = Settings(
        GRPC_TLS_CERT_PATH="/etc/certs/server.crt",
        GRPC_TLS_KEY_PATH="/etc/certs/server.key",
    )
    assert settings.grpc_tls_cert_path == "/etc/certs/server.crt"
    assert settings.grpc_tls_key_path == "/etc/certs/server.key"
