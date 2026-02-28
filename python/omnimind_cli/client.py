from __future__ import annotations

import json
import os
from collections.abc import Iterator
from typing import Any, cast

import httpx

from omnimind_backend.schemas.agent import StreamEvent
from omnimind_cli.sse import iter_sse_payloads


class OmniMindCliClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("OMNIMIND_API_URL") or "http://127.0.0.1:8000").rstrip("/")

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def get_health(self) -> dict[str, Any]:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(self._url("/health"))
            response.raise_for_status()
            return cast(dict[str, Any], response.json())

    def stream_chat(
        self,
        *,
        message: str,
        provider: str | None = None,
        model: str | None = None,
        debug_steps: bool = False,
    ) -> Iterator[StreamEvent]:
        payload: dict[str, Any] = {
            "message": message,
            "debugSteps": debug_steps,
        }
        if provider:
            payload["provider"] = provider
        if model:
            payload["model"] = model

        with (
            httpx.Client(timeout=None) as client,
            client.stream(
                "POST",
                self._url("/v1/agent/chat/stream"),
                json=payload,
                headers={"Accept": "text/event-stream"},
            ) as response,
        ):
            response.raise_for_status()
            for payload_json in iter_sse_payloads(response.iter_lines()):
                try:
                    raw = json.loads(payload_json)
                except json.JSONDecodeError:
                    continue
                yield StreamEvent.model_validate(raw)
