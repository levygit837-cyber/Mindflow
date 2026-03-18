"""Tests for trusted proxy client IP extraction."""

from __future__ import annotations

from types import SimpleNamespace

from starlette.requests import Request

from mindflow_backend.infra.config import Settings
from mindflow_backend.security.client_ip import get_client_ip


def _make_request(*, client_host: str, headers: dict[str, str]) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/health",
        "headers": [(key.lower().encode(), value.encode()) for key, value in headers.items()],
        "client": (client_host, 12345),
        "server": ("testserver", 80),
        "scheme": "http",
        "query_string": b"",
    }
    return Request(scope)


def test_uses_forwarded_for_only_from_trusted_proxy() -> None:
    settings = Settings(
        APP_ENV="production",
        SECURITY_TRUST_PROXY_HEADERS=True,
        SECURITY_TRUSTED_PROXY_IPS="127.0.0.1",
    )
    request = _make_request(
        client_host="127.0.0.1",
        headers={"X-Forwarded-For": "203.0.113.10, 127.0.0.1"},
    )

    assert get_client_ip(request, settings=settings) == "203.0.113.10"


def test_ignores_forwarded_for_from_untrusted_proxy() -> None:
    settings = Settings(
        APP_ENV="production",
        SECURITY_TRUST_PROXY_HEADERS=True,
        SECURITY_TRUSTED_PROXY_IPS="127.0.0.1",
    )
    request = _make_request(
        client_host="198.51.100.20",
        headers={"X-Forwarded-For": "203.0.113.10"},
    )

    assert get_client_ip(request, settings=settings) == "198.51.100.20"
