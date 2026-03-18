"""Interfaces for the research-domain browser queue pipeline."""

from __future__ import annotations

from typing import Any, Protocol

from mindflow_backend.workers.research.schemas.browser_tasks import (
    BrowserTaskPayload,
)


class BrowserTaskPublisher(Protocol):
    """Publisher contract for queued browser work."""

    async def publish_web_search(
        self,
        *,
        session_id: str,
        query: str,
        search_engine: str = "google",
        max_results: int = 10,
        search_depth: str = "standard",
        priority: int | None = None,
        origin: str = "pinchtab_fleet_service",
    ) -> bool: ...


class BrowserTaskExecutor(Protocol):
    """Executor contract consumed by the browser worker."""

    async def execute_browser_task(self, payload: BrowserTaskPayload) -> dict[str, Any]: ...
