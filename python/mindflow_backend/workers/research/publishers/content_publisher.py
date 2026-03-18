"""RabbitMQ publisher for research content queue events."""

from __future__ import annotations

from typing import Any

from mindflow_backend.workers.infrastructure.queue_manager import get_queue_manager
from mindflow_backend.workers.research.interfaces.content import ContentTaskPublisher
from mindflow_backend.workers.research.schemas.content_tasks import (
    build_content_synthesis_envelope,
)


class RabbitMQContentTaskPublisher(ContentTaskPublisher):
    """Publish content tasks through the research queue manager."""

    def __init__(self, queue_manager=None) -> None:
        self._queue_manager = queue_manager or get_queue_manager()

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
    ) -> bool:
        envelope = build_content_synthesis_envelope(
            session_id=session_id,
            content_sources=content_sources,
            synthesis_type=synthesis_type,
            target_audience=target_audience,
            synthesis_length=synthesis_length,
            origin=origin,
        )
        return await self._queue_manager.publish_message(
            queue_name="content_medium",
            message_data=envelope.model_dump(mode="json"),
            priority=priority if priority is not None else 5,
        )
