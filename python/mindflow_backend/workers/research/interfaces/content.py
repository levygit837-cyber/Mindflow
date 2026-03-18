"""Interfaces for the research-domain content queue pipeline."""

from __future__ import annotations

from typing import Any, Protocol

from mindflow_backend.workers.research.schemas.content_tasks import (
    ContentSynthesisPayload,
)


class ContentTaskPublisher(Protocol):
    """Publisher contract for queued content work."""

    async def publish_content_synthesis(
        self,
        *,
        session_id: str,
        content_sources: list[dict[str, Any]],
        synthesis_type: str = "comprehensive",
        target_audience: str = "technical",
        synthesis_length: str = "medium",
        priority: int | None = None,
        origin: str = "pinchtab_fleet_service",
    ) -> bool: ...


class ContentTaskExecutor(Protocol):
    """Executor contract consumed by the content worker."""

    async def synthesize_content(self, payload: ContentSynthesisPayload) -> dict[str, Any]: ...
