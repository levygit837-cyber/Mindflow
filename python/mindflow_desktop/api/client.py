from __future__ import annotations

import os
from typing import Any

import httpx


class MindFlowApiClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("MINDFLOW_API_URL") or "http://127.0.0.1:8000").rstrip("/")

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(self._url(path), params=params)
            response.raise_for_status()
            return response.json()

    def post(self, path: str, payload: dict[str, Any]) -> Any:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(self._url(path), json=payload)
            response.raise_for_status()
            return response.json()

    def patch(self, path: str, payload: dict[str, Any]) -> Any:
        with httpx.Client(timeout=30.0) as client:
            response = client.patch(self._url(path), json=payload)
            response.raise_for_status()
            return response.json()

    def delete(self, path: str) -> Any:
        with httpx.Client(timeout=30.0) as client:
            response = client.delete(self._url(path))
            response.raise_for_status()
            if response.content:
                return response.json()
            return {"ok": True}
