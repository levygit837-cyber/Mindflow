"""Tests for API Key authentication dependency."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from mindflow_backend.infra.config import Settings
from mindflow_backend.infra.middleware.auth import require_api_key


def _make_app(auth_enabled: bool = True, master_key: str | None = "test-master-key") -> TestClient:
    app = FastAPI()

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/v1/agent/chat/stream")
    def chat_stream(api_key: str | None = Depends(require_api_key)):
        return {"status": "streaming", "authenticated": api_key is not None}

    fake_settings = Settings(AUTH_ENABLED=auth_enabled, AUTH_MASTER_KEY=master_key)
    client = TestClient(app)
    return client, fake_settings


def test_auth_disabled_allows_all():
    client, fake_settings = _make_app(auth_enabled=False)
    with patch("mindflow_backend.infra.middleware.auth.get_settings", return_value=fake_settings):
        resp = client.post("/v1/agent/chat/stream")
    assert resp.status_code == 200


def test_auth_enabled_rejects_without_key():
    client, fake_settings = _make_app(auth_enabled=True)
    with patch("mindflow_backend.infra.middleware.auth.get_settings", return_value=fake_settings):
        resp = client.post("/v1/agent/chat/stream")
    assert resp.status_code == 401
    assert "Missing API key" in resp.json()["detail"]


def test_auth_enabled_accepts_master_key():
    client, fake_settings = _make_app(auth_enabled=True, master_key="test-master-key")

    with (
        patch("mindflow_backend.infra.middleware.auth.get_settings", return_value=fake_settings),
        patch("mindflow_backend.infra.middleware.auth._validate_key", new_callable=AsyncMock, return_value=True),
    ):
        resp = client.post(
            "/v1/agent/chat/stream",
            headers={"Authorization": "Bearer test-master-key"},
        )
    assert resp.status_code == 200


def test_auth_enabled_rejects_invalid_key():
    client, fake_settings = _make_app(auth_enabled=True)

    with (
        patch("mindflow_backend.infra.middleware.auth.get_settings", return_value=fake_settings),
        patch("mindflow_backend.infra.middleware.auth._validate_key", new_callable=AsyncMock, return_value=False),
    ):
        resp = client.post(
            "/v1/agent/chat/stream",
            headers={"Authorization": "Bearer invalid-key"},
        )
    assert resp.status_code == 401
    assert "Invalid API key" in resp.json()["detail"]


def test_health_endpoint_always_open():
    """The /health endpoint should not require authentication."""
    client, fake_settings = _make_app(auth_enabled=True)
    # /health doesn't use the auth dependency in this test app,
    # so it should always be accessible.
    with patch("mindflow_backend.infra.middleware.auth.get_settings", return_value=fake_settings):
        resp = client.get("/health")
    assert resp.status_code == 200
