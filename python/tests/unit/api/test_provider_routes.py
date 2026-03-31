from __future__ import annotations

import pytest
from starlette.requests import Request

from mindflow_backend.api.schemas.requests import ProviderConfigRequest, ProviderTestRequest
from mindflow_backend.api.v1 import providers as provider_routes


def _make_request(path: str, method: str = "GET") -> Request:
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "scheme": "http",
            "method": method,
            "path": path,
            "raw_path": path.encode("utf-8"),
            "query_string": b"",
            "headers": [],
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
            "root_path": "",
        }
    )


@pytest.mark.asyncio
async def test_list_providers_route_passes_request(monkeypatch) -> None:
    captured: dict[str, str] = {}

    async def _fake_list(req: Request) -> dict[str, object]:
        captured["path"] = req.url.path
        return {"success": True, "providers": [], "total": 0}

    monkeypatch.setattr(provider_routes.provider_controller, "list_providers", _fake_list)

    response = await provider_routes.list_providers(_make_request("/v1/providers/"))

    assert response["success"] is True
    assert captured["path"] == "/v1/providers/"


@pytest.mark.asyncio
async def test_provider_models_route_passes_request(monkeypatch) -> None:
    captured: dict[str, str] = {}

    async def _fake_models(provider_id: str, req: Request) -> dict[str, object]:
        captured["provider_id"] = provider_id
        captured["path"] = req.url.path
        return {"success": True, "models": []}

    monkeypatch.setattr(provider_routes.provider_controller, "get_provider_models", _fake_models)

    response = await provider_routes.get_provider_models(
        "google",
        _make_request("/v1/providers/google/models"),
    )

    assert response["success"] is True
    assert captured == {
        "provider_id": "google",
        "path": "/v1/providers/google/models",
    }


@pytest.mark.asyncio
async def test_provider_test_route_builds_default_request_and_passes_http_request(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def _fake_test(request: ProviderTestRequest, req: Request) -> dict[str, object]:
        captured["provider_id"] = request.provider_id
        captured["path"] = req.url.path
        return {"success": True}

    monkeypatch.setattr(provider_routes.provider_controller, "test_provider", _fake_test)

    response = await provider_routes.test_provider(
        "google",
        _make_request("/v1/providers/google/test", method="POST"),
    )

    assert response["success"] is True
    assert captured == {
        "provider_id": "google",
        "path": "/v1/providers/google/test",
    }


@pytest.mark.asyncio
async def test_provider_config_update_route_passes_request(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def _fake_update(provider_id: str, request: ProviderConfigRequest, req: Request) -> dict[str, object]:
        captured["provider_id"] = provider_id
        captured["timeout"] = request.timeout
        captured["path"] = req.url.path
        return {"success": True}

    monkeypatch.setattr(provider_routes.provider_controller, "update_provider_config", _fake_update)

    response = await provider_routes.update_provider_config(
        "google",
        ProviderConfigRequest(timeout=15),
        _make_request("/v1/providers/google/config", method="PUT"),
    )

    assert response["success"] is True
    assert captured == {
        "provider_id": "google",
        "timeout": 15,
        "path": "/v1/providers/google/config",
    }
