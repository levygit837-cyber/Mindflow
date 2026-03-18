"""RabbitMQ publisher for memory queue events."""

from __future__ import annotations

from mindflow_backend.workers.infrastructure.queue_manager import get_queue_manager
from mindflow_backend.workers.system.interfaces.memory import MemoryPublisher
from mindflow_backend.workers.system.schemas.memory_tasks import (
    build_memory_message_recorded_envelope,
)


class RabbitMQMemoryTaskPublisher(MemoryPublisher):
    """Publish memory events to the RabbitMQ system queue."""

    def __init__(self, queue_manager=None) -> None:
        self._queue_manager = queue_manager or get_queue_manager()

    async def publish_message_recorded(
        self,
        *,
        session_id: str,
        agent_id: str,
        role: str,
        content: str,
        source_message_id: int | None = None,
        source_status: str = "final",
        derived_from_recall: bool = False,
        origin: str = "stream_runtime",
    ) -> bool:
        envelope = build_memory_message_recorded_envelope(
            session_id=session_id,
            agent_id=agent_id,
            role=role,
            content=content,
            source_message_id=source_message_id,
            source_status=source_status,
            derived_from_recall=derived_from_recall,
            origin=origin,
        )

        return await self._queue_manager.publish_message(
            queue_name="memory_low",
            message_data=envelope.model_dump(mode="json"),
            priority=5,
        )
