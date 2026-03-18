"""HTTP client for a single PinchTab runtime endpoint."""

from __future__ import annotations

from typing import Any

import httpx

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class PinchTabBrowserService:
    """Encapsulate HTTP commands against a running PinchTab browser runtime."""

    def __init__(self, default_timeout: int = 30) -> None:
        self.default_timeout = default_timeout

    async def health_check(self, runtime_endpoint: str) -> bool:
        """Return whether the runtime endpoint responds successfully."""
        try:
            await self._request(runtime_endpoint, "GET", "/health")
            return True
        except Exception:
            try:
                await self._request(runtime_endpoint, "GET", "/instances")
                return True
            except Exception:
                return False

    async def navigate(
        self,
        runtime_endpoint: str,
        tab_id: str,
        url: str,
        timeout_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Navigate a browser tab to a URL."""
        return await self._action(
            runtime_endpoint,
            tab_id,
            {"action": "navigate", "url": url},
            timeout_seconds=timeout_seconds,
        )

    async def get_snapshot(
        self,
        runtime_endpoint: str,
        tab_id: str,
        filter_interactive: bool = True,
        timeout_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Get a page snapshot."""
        params = {"filter": "interactive"} if filter_interactive else None
        return await self._request(
            runtime_endpoint,
            "GET",
            f"/instances/{tab_id}/snapshot",
            params=params,
            timeout_seconds=timeout_seconds,
        )

    async def extract_text(
        self,
        runtime_endpoint: str,
        tab_id: str,
        timeout_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Extract clean text from the active page."""
        return await self._action(
            runtime_endpoint,
            tab_id,
            {"action": "text"},
            timeout_seconds=timeout_seconds,
        )

    async def click_element(
        self,
        runtime_endpoint: str,
        tab_id: str,
        element_ref: str,
        timeout_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Click an element reference."""
        return await self._action(
            runtime_endpoint,
            tab_id,
            {"action": "click", "ref": element_ref},
            timeout_seconds=timeout_seconds,
        )

    async def fill_input(
        self,
        runtime_endpoint: str,
        tab_id: str,
        element_ref: str,
        value: str,
        timeout_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Fill a text input."""
        return await self._action(
            runtime_endpoint,
            tab_id,
            {"action": "fill", "ref": element_ref, "value": value},
            timeout_seconds=timeout_seconds,
        )

    async def press_key(
        self,
        runtime_endpoint: str,
        tab_id: str,
        element_ref: str,
        key: str,
        timeout_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Press a key on an element."""
        return await self._action(
            runtime_endpoint,
            tab_id,
            {"action": "press", "ref": element_ref, "key": key},
            timeout_seconds=timeout_seconds,
        )

    async def get_state(self, runtime_endpoint: str, tab_id: str) -> dict[str, Any]:
        """Fetch generic runtime state for a managed tab."""
        try:
            return await self._request(runtime_endpoint, "GET", f"/instances/{tab_id}")
        except Exception:
            return await self._request(runtime_endpoint, "GET", "/instances")

    async def _action(
        self,
        runtime_endpoint: str,
        tab_id: str,
        payload: dict[str, Any],
        timeout_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Execute a generic PinchTab action payload."""
        return await self._request(
            runtime_endpoint,
            "POST",
            f"/instances/{tab_id}/action",
            json=payload,
            timeout_seconds=timeout_seconds,
        )

    async def _request(
        self,
        runtime_endpoint: str,
        method: str,
        path: str,
        timeout_seconds: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute an HTTP request against the PinchTab runtime."""
        timeout = timeout_seconds or self.default_timeout
        async with httpx.AsyncClient(base_url=runtime_endpoint.rstrip("/"), timeout=timeout) as client:
            response = await client.request(method, path, **kwargs)
            response.raise_for_status()
            if not response.content:
                return {}
            return response.json()


__all__ = ["PinchTabBrowserService"]
