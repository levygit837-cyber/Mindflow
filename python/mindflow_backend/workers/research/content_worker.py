"""Content worker for queued content processing and synthesis tasks."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.workers.base.worker import BaseWorker, WorkerResult
from mindflow_backend.workers.config.queues import QueueConfig
from mindflow_backend.workers.research.consumers.content_consumer import (
    ContentTaskConsumer,
)

_logger = get_logger(__name__)


class ContentWorker(BaseWorker):
    """Worker specialized for queued content synthesis and processing tasks."""

    def __init__(self, queue_config: QueueConfig) -> None:
        super().__init__(queue_config, worker_name="content_worker")
        self._content_consumer = ContentTaskConsumer()

    async def process_message(self, message_data: dict[str, Any]) -> WorkerResult:
        """Process content synthesis and related research tasks."""
        start_time = time.time()
        message_data = self._normalize_message_data(message_data)
        task_type = message_data.get("task_type", "unknown")
        task_id = message_data.get("task_id", "unknown")

        try:
            _logger.info(f"ContentWorker processing {task_type} task {task_id}")

            if task_type == "content_synthesis":
                result = await self._handle_content_synthesis(message_data)
            elif task_type in {
                "text_processing",
                "content_categorization",
                "summarization",
                "content_enrichment",
                "quality_assessment",
            }:
                result = await self._simulate_legacy_task(task_type, message_data)
            else:
                result = WorkerResult(
                    success=False,
                    message=f"Unsupported task type: {task_type}",
                    processing_time=time.time() - start_time,
                )

            _logger.info(
                f"ContentWorker completed {task_type} task {task_id} "
                f"({'SUCCESS' if result.success else 'FAILED'})"
            )
            return result

        except Exception as e:
            _logger.error(
                f"ContentWorker failed to process {task_type} task {task_id}: {e}",
                exc_info=True,
            )
            return WorkerResult(
                success=False,
                message=f"Task processing failed: {e}",
                error=e,
                processing_time=time.time() - start_time,
            )

    async def _handle_content_synthesis(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle the real queued content synthesis path."""
        result = await self._content_consumer.consume_content_synthesis(message_data)
        return WorkerResult(
            success=True,
            message="Content synthesis completed successfully",
            data=result,
        )

    async def _simulate_legacy_task(
        self,
        task_type: str,
        message_data: dict[str, Any],
    ) -> WorkerResult:
        """Keep lightweight compatibility for non-migrated content tasks."""
        await asyncio.sleep(0)
        return WorkerResult(
            success=True,
            message=f"Legacy content task completed: {task_type}",
            data={
                "task_type": task_type,
                "session_id": message_data.get("session_id"),
                "status": "processed",
            },
        )
