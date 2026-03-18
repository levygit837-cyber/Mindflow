"""RabbitMQ publisher for session review queue events."""

from __future__ import annotations

from mindflow_backend.workers.system.interfaces.session_review import SessionReviewPublisher
from mindflow_backend.workers.tasks.system_tasks import (
    SystemTaskDefinitions,
    get_system_task_publisher,
)


class RabbitMQSessionReviewTaskPublisher(SessionReviewPublisher):
    """Publish session review events through the system task publisher."""

    def __init__(self, task_publisher=None) -> None:
        self._task_publisher = task_publisher or get_system_task_publisher()

    async def publish_review_requested(
        self,
        *,
        session_id: str,
        window_index: int,
        window_range: tuple[int, int],
        trigger_type: str,
        priority: str,
        tokens_in_window: int,
        total_tokens_processed: int,
        threshold: int,
        origin: str = "session_review_service",
    ) -> bool:
        task = SystemTaskDefinitions.create_session_review_requested_task(
            session_id=session_id,
            window_index=window_index,
            window_range=window_range,
            trigger_type=trigger_type,
            review_priority=priority,
            tokens_in_window=tokens_in_window,
            total_tokens_processed=total_tokens_processed,
            threshold=threshold,
            origin=origin,
        )
        return await self._task_publisher.publish_task(task)
