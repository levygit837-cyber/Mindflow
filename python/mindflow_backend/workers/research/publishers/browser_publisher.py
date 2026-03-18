"""RabbitMQ publisher for research browser queue events."""

from __future__ import annotations

from mindflow_backend.workers.infrastructure.queue_manager import get_queue_manager
from mindflow_backend.workers.research.interfaces.browser import BrowserTaskPublisher
from mindflow_backend.workers.research.schemas.browser_tasks import (
    build_web_search_envelope,
)


class RabbitMQBrowserTaskPublisher(BrowserTaskPublisher):
    """Publish browser tasks through the research queue manager."""

    def __init__(self, queue_manager=None) -> None:
        self._queue_manager = queue_manager or get_queue_manager()

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
    ) -> bool:
        envelope = build_web_search_envelope(
            session_id=session_id,
            query=query,
            search_engine=search_engine,
            max_results=max_results,
            search_depth=search_depth,
            origin=origin,
        )
        return await self._queue_manager.publish_message(
            queue_name="browser_high",
            message_data=envelope.model_dump(mode="json"),
            priority=priority if priority is not None else 7,
        )
