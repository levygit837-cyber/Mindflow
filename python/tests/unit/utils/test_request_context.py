"""Tests for RequestContextMiddleware."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from mindflow_backend.infra.middleware.request_context import (
    RequestContextMiddleware,
    get_request_id,
)


def _make_app() -> TestClient:
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/health")
    def health():
        return {"status": "ok", "request_id": get_request_id()}

    return TestClient(app)


def test_auto_generates_request_id():
    client = _make_app()
    resp = client.get("/health")
    assert resp.status_code == 200
    rid = resp.headers.get("X-Request-ID")
    assert rid is not None
    assert rid.startswith("req-")


def test_echoes_incoming_request_id():
    client = _make_app()
    resp = client.get("/health", headers={"X-Request-ID": "custom-abc-123"})
    assert resp.status_code == 200
    assert resp.headers["X-Request-ID"] == "custom-abc-123"


def test_request_id_available_in_context():
    client = _make_app()
    resp = client.get("/health", headers={"X-Request-ID": "ctx-test-456"})
    body = resp.json()
    assert body["request_id"] == "ctx-test-456"
