"""Security routing integration tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

from mindflow_backend.api.v1.agent import router as agent_router
from mindflow_backend.infra.config import Settings


async def _empty_stream() -> AsyncGenerator[str, None]:
    if False:
        yield ""


def _make_app() -> TestClient:
    app = FastAPI()

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(agent_router, prefix="/v1")
    return TestClient(app)


def test_protected_router_requires_authentication_when_enabled() -> None:
    client = _make_app()
    fake_settings = Settings(AUTH_ENABLED=True, AUTH_MASTER_KEY="test-master-key")
    stream_mock = AsyncMock(
        return_value=StreamingResponse(_empty_stream(), media_type="text/event-stream")
    )

    with (
        patch("mindflow_backend.infra.middleware.auth.get_settings", return_value=fake_settings),
        patch("mindflow_backend.api.v1.agent.agent_controller.stream_chat", stream_mock),
    ):
        response = client.post("/v1/agent/chat/stream", json={"message": "hello"})

    assert response.status_code == 401
    stream_mock.assert_not_awaited()


def test_protected_router_allows_valid_api_key_when_enabled() -> None:
    client = _make_app()
    fake_settings = Settings(AUTH_ENABLED=True, AUTH_MASTER_KEY="test-master-key")
    stream_mock = AsyncMock(
        return_value=StreamingResponse(_empty_stream(), media_type="text/event-stream")
    )

    with (
        patch("mindflow_backend.infra.middleware.auth.get_settings", return_value=fake_settings),
        patch(
            "mindflow_backend.infra.middleware.auth._validate_key",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch("mindflow_backend.api.v1.agent.agent_controller.stream_chat", stream_mock),
    ):
        response = client.post(
            "/v1/agent/chat/stream",
            json={"message": "hello"},
            headers={"Authorization": "Bearer test-master-key"},
        )

    assert response.status_code == 200
    stream_mock.assert_awaited_once()


def test_health_route_remains_public() -> None:
    client = _make_app()
    fake_settings = Settings(AUTH_ENABLED=True, AUTH_MASTER_KEY="test-master-key")

    with patch("mindflow_backend.infra.middleware.auth.get_settings", return_value=fake_settings):
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
