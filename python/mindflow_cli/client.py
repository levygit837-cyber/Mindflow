from __future__ import annotations

import json
import os
from collections.abc import Iterator
from typing import Any, cast

import httpx

from mindflow_backend.schemas.agent import StreamEvent
from mindflow_cli.sse import iter_sse_payloads


class MindFlowCliClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("MINDFLOW_API_URL") or "http://127.0.0.1:8000").rstrip("/")
        # API key resolution order: explicit arg → env var → settings file
        self._api_key = api_key or os.getenv("MINDFLOW_API_KEY") or ""

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _auth_headers(self) -> dict[str, str]:
        """Return Authorization header if an API key is configured."""
        if self._api_key:
            return {"Authorization": f"Bearer {self._api_key}"}
        return {}

    def get_health(self) -> dict[str, Any]:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(self._url("/health"), headers=self._auth_headers())
            response.raise_for_status()
            return cast(dict[str, Any], response.json())

    def stream_chat(
        self,
        *,
        message: str,
        provider: str | None = None,
        model: str | None = None,
        debug_steps: bool = False,
        agent_type: str | None = None,
        orchestrate: bool = False,
    ) -> Iterator[StreamEvent]:
        payload: dict[str, Any] = {
            "message": message,
            "debugSteps": debug_steps,
            "orchestrate": orchestrate,
        }
        if provider:
            payload["provider"] = provider
        if model:
            payload["model"] = model
        if agent_type:
            payload["agent_type"] = agent_type

        headers = {"Accept": "text/event-stream", **self._auth_headers()}

        with (
            httpx.Client(timeout=None) as client,
            client.stream(
                "POST",
                self._url("/v1/agent/chat/stream"),
                json=payload,
                headers=headers,
            ) as response,
        ):
            response.raise_for_status()
            for payload_json in iter_sse_payloads(response.iter_lines()):
                try:
                    raw = json.loads(payload_json)
                except json.JSONDecodeError:
                    continue
                yield StreamEvent.model_validate(raw)
