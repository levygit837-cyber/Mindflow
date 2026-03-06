"""Tests for RateLimiterMiddleware."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from mindflow_backend.infra.config import Settings
from mindflow_backend.infra.middleware.rate_limiter import RateLimiterMiddleware


def _make_app(rate_limit_enabled: bool = True, limit: int = 3) -> TestClient:
    app = FastAPI()
    app.add_middleware(RateLimiterMiddleware)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/v1/agent/chat/stream")
    def chat_stream():
        return {"status": "streaming"}

    fake_settings = Settings(
        RATE_LIMIT_ENABLED=rate_limit_enabled,
        RATE_LIMIT_GLOBAL=limit,
        RATE_LIMIT_CHAT_STREAM=limit,
        RATE_LIMIT_WINDOW_SECONDS=60,
    )

    client = TestClient(app)
    return client, fake_settings


def test_rate_limiter_disabled_passes_through():
    client, fake_settings = _make_app(rate_limit_enabled=False)
    with patch("mindflow_backend.infra.middleware.rate_limiter.get_settings", return_value=fake_settings):
        resp = client.get("/health")
    assert resp.status_code == 200
    assert "X-RateLimit-Limit" not in resp.headers


def test_rate_limiter_allows_within_limit():
    client, fake_settings = _make_app(rate_limit_enabled=True, limit=10)

    with (
        patch("mindflow_backend.infra.middleware.rate_limiter.get_settings", return_value=fake_settings),
        patch(
            "mindflow_backend.infra.middleware.rate_limiter._check_rate_limit",
            new_callable=AsyncMock,
            return_value=(True, 9),
        ),
        patch("mindflow_backend.infra.middleware.rate_limiter._get_redis", return_value=AsyncMock()),
    ):
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.headers["X-RateLimit-Limit"] == "10"
    assert resp.headers["X-RateLimit-Remaining"] == "9"


def test_rate_limiter_returns_429_when_exceeded():
    client, fake_settings = _make_app(rate_limit_enabled=True, limit=2)

    with (
        patch("mindflow_backend.infra.middleware.rate_limiter.get_settings", return_value=fake_settings),
        patch(
            "mindflow_backend.infra.middleware.rate_limiter._check_rate_limit",
            new_callable=AsyncMock,
            return_value=(False, 0),
        ),
        patch("mindflow_backend.infra.middleware.rate_limiter._get_redis", return_value=AsyncMock()),
    ):
        resp = client.get("/health")
    assert resp.status_code == 429
    assert resp.json()["detail"] == "Rate limit exceeded. Try again later."
    assert resp.headers["Retry-After"] == "60"


def test_rate_limiter_fails_open_on_redis_error():
    """If Redis is unavailable, requests should still be allowed."""
    client, fake_settings = _make_app(rate_limit_enabled=True, limit=2)

    with (
        patch("mindflow_backend.infra.middleware.rate_limiter.get_settings", return_value=fake_settings),
        patch(
            "mindflow_backend.infra.middleware.rate_limiter._get_redis",
            side_effect=ConnectionError("Redis down"),
        ),
    ):
        resp = client.get("/health")
    assert resp.status_code == 200
