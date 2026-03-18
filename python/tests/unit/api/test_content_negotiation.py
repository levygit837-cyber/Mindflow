"""Tests for HTTP content negotiation middleware."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

from mindflow_backend.api.middleware.content_negotiation import ContentNegotiationMiddleware


async def _sse_stream() -> AsyncGenerator[str, None]:
    yield "data: hello\n\n"


def _make_app() -> TestClient:
    app = FastAPI()
    app.add_middleware(ContentNegotiationMiddleware)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/json")
    async def create_json(payload: dict) -> dict[str, bool]:
        return {"ok": bool(payload)}

    @app.get("/stream")
    async def stream() -> StreamingResponse:
        return StreamingResponse(_sse_stream(), media_type="text/event-stream")

    @app.post("/agent/chat/stream/legacy")
    async def legacy_stream() -> StreamingResponse:
        return StreamingResponse(_sse_stream(), media_type="text/event-stream")

    return TestClient(app)


def test_rejects_invalid_content_type_for_json_request() -> None:
    client = _make_app()

    response = client.post(
        "/json",
        content="plain text",
        headers={"Content-Type": "text/plain", "Accept": "application/json"},
    )

    assert response.status_code == 415


def test_rejects_incompatible_accept_header_for_json_response() -> None:
    client = _make_app()

    response = client.get("/health", headers={"Accept": "text/event-stream"})

    assert response.status_code == 406


def test_allows_sse_when_accept_header_matches() -> None:
    client = _make_app()

    response = client.get("/stream", headers={"Accept": "text/event-stream"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")


def test_allows_sse_for_legacy_stream_path() -> None:
    client = _make_app()

    response = client.post(
        "/agent/chat/stream/legacy",
        json={"message": "hi"},
        headers={"Accept": "text/event-stream", "Content-Type": "application/json"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
