from unittest.mock import AsyncMock

import pytest

from mindflow_backend.agents.tools.callable import web as callable_web
from mindflow_backend.schemas.tools.context import ToolContext


def _make_fake_legacy_builder(calls: dict[str, object], payload: dict[str, object]):
    class _FakeTool:
        async def execute(self, **kwargs):
            calls["kwargs"] = kwargs
            return {"success": True, "result": payload}

    def _builder(tool_cls, context):
        calls["tool_cls"] = tool_cls.__name__
        calls["context"] = context
        return _FakeTool()

    return _builder


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("impl_name", "input_name", "tool_name", "input_kwargs", "payload", "expected_kwargs"),
    [
        (
            "http_client_impl",
            "HttpClientInput",
            "HttpClientTool",
            {
                "method": "POST",
                "url": "https://example.com/api",
                "headers": {"X-Test": "1"},
                "params": {"mode": "test"},
                "data": {"name": "MindFlow"},
                "form_data": None,
                "timeout": 15,
                "verify_ssl": False,
                "follow_redirects": False,
                "max_redirects": 2,
            },
            {"marker": "http"},
            {
                "method": "POST",
                "url": "https://example.com/api",
                "headers": {"X-Test": "1"},
                "params": {"mode": "test"},
                "data": {"name": "MindFlow"},
                "form_data": None,
                "timeout": 15,
                "verify_ssl": False,
                "follow_redirects": False,
                "max_redirects": 2,
            },
        ),
        (
            "web_scraper_impl",
            "WebScraperInput",
            "WebScraperTool",
            {
                "url": "https://example.com",
                "selectors": ["main", "a.button"],
                "headers": {"User-Agent": "MindFlow"},
                "timeout": 10,
                "extract_links": True,
                "extract_images": True,
                "extract_text": False,
            },
            {"marker": "scrape"},
            {
                "url": "https://example.com",
                "selectors": ["main", "a.button"],
                "headers": {"User-Agent": "MindFlow"},
                "timeout": 10,
                "extract_links": True,
                "extract_images": True,
                "extract_text": False,
            },
        ),
        (
            "api_client_impl",
            "ApiClientInput",
            "ApiClientTool",
            {
                "api_url": "https://api.example.com",
                "endpoint": "v1/items",
                "method": "PATCH",
                "headers": {"X-Tenant": "mindflow"},
                "auth_type": "bearer",
                "auth_token": "secret-token",
                "username": None,
                "password": None,
                "api_key_header": "X-API-Key",
                "data": {"enabled": True},
                "params": {"dry_run": "1"},
                "timeout": 12,
            },
            {"marker": "api"},
            {
                "api_url": "https://api.example.com",
                "endpoint": "v1/items",
                "method": "PATCH",
                "headers": {"X-Tenant": "mindflow"},
                "auth_type": "bearer",
                "auth_token": "secret-token",
                "username": None,
                "password": None,
                "api_key_header": "X-API-Key",
                "data": {"enabled": True},
                "params": {"dry_run": "1"},
                "timeout": 12,
            },
        ),
    ],
)
async def test_callable_web_impls_delegate_to_canonical_tools(
    monkeypatch,
    impl_name,
    input_name,
    tool_name,
    input_kwargs,
    payload,
    expected_kwargs,
) -> None:
    calls: dict[str, object] = {}
    monkeypatch.setattr(
        callable_web,
        "build_legacy_tool",
        _make_fake_legacy_builder(calls, payload),
        raising=False,
    )
    monkeypatch.setattr(
        callable_web,
        "deny_if_permission_blocked",
        AsyncMock(return_value=None),
        raising=False,
    )

    impl = getattr(callable_web, impl_name)
    input_cls = getattr(callable_web, input_name)
    context = ToolContext(metadata={})

    result = await impl(input_cls(**input_kwargs), context)

    assert calls["tool_cls"] == tool_name
    assert calls["kwargs"] == expected_kwargs
    assert result.success is True
    for key, value in payload.items():
        assert result.data[key] == value
