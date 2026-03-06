"""Tests for SecurityHeadersMiddleware."""

from __future__ import annotations

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from mindflow_backend.infra.middleware.security_headers import SecurityHeadersMiddleware


def _make_app(app_env: str = "development") -> TestClient:
    """Create a minimal FastAPI app with the middleware for testing."""
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    # Patch get_settings to control app_env
    from mindflow_backend.infra.config import Settings

    fake_settings = Settings(APP_ENV=app_env)

    with patch("mindflow_backend.infra.middleware.security_headers.get_settings", return_value=fake_settings):
        client = TestClient(app)
    return client, fake_settings


def test_common_security_headers_present():
    client, fake_settings = _make_app("development")
    with patch("mindflow_backend.infra.middleware.security_headers.get_settings", return_value=fake_settings):
        resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["X-XSS-Protection"] == "1; mode=block"
    assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert resp.headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"
    assert resp.headers["Content-Security-Policy"] == "default-src 'self'"


def test_hsts_absent_in_development():
    client, fake_settings = _make_app("development")
    with patch("mindflow_backend.infra.middleware.security_headers.get_settings", return_value=fake_settings):
        resp = client.get("/health")
    assert "Strict-Transport-Security" not in resp.headers


def test_hsts_present_in_production():
    client, fake_settings = _make_app("production")
    with patch("mindflow_backend.infra.middleware.security_headers.get_settings", return_value=fake_settings):
        resp = client.get("/health")
    assert resp.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
