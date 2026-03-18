"""Browser worker for queued browser automation and web research tasks."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.workers.base.worker import BaseWorker, WorkerResult
from mindflow_backend.workers.config.queues import QueueConfig
from mindflow_backend.workers.research.consumers.browser_consumer import (
    BrowserTaskConsumer,
)

_logger = get_logger(__name__)


class BrowserWorker(BaseWorker):
    """Worker specialized for browser automation and web research tasks."""

    def __init__(self, queue_config: QueueConfig) -> None:
        super().__init__(queue_config, worker_name="browser_worker")
        self._browser_consumer = BrowserTaskConsumer()
        self._concurrency_limiter = asyncio.Semaphore(max(1, self.queue_config.concurrency))

    async def process_message(self, message_data: Dict[str, Any]) -> WorkerResult:
        """Process browser automation and web research tasks."""
        start_time = time.time()
        message_data = self._normalize_message_data(message_data)
        task_type = message_data.get("task_type", "unknown")
        task_id = message_data.get("task_id", "unknown")

        try:
            async with self._concurrency_limiter:
                _logger.info(f"BrowserWorker processing {task_type} task {task_id}")

                if task_type in {"web_search", "page_scraping"}:
                    result = await self._handle_browser_pipeline(message_data)
                elif task_type in {
                    "screenshot_capture",
                    "form_interaction",
                    "link_extraction",
                    "content_validation",
                }:
                    result = await self._simulate_legacy_task(task_type, message_data)
                else:
                    result = WorkerResult(
                        success=False,
                        message=f"Unsupported task type: {task_type}",
                        processing_time=time.time() - start_time,
                    )

            _logger.info(
                f"BrowserWorker completed {task_type} task {task_id} "
                f"({'SUCCESS' if result.success else 'FAILED'})"
            )
            return result

        except Exception as e:
            _logger.error(
                f"BrowserWorker failed to process {task_type} task {task_id}: {e}",
                exc_info=True,
            )
            return WorkerResult(
                success=False,
                message=f"Task processing failed: {e}",
                error=e,
                processing_time=time.time() - start_time,
            )

    async def _handle_browser_pipeline(self, message_data: Dict[str, Any]) -> WorkerResult:
        """Handle the real queued browser execution path."""
        result = await self._browser_consumer.consume_browser_task(message_data)
        return WorkerResult(
            success=True,
            message=f"Browser task processed successfully: {result['task_type']}",
            data=result,
        )

    async def _simulate_legacy_task(
        self,
        task_type: str,
        message_data: Dict[str, Any],
    ) -> WorkerResult:
        """Keep lightweight compatibility for non-migrated research tasks."""
        await asyncio.sleep(0)
        return WorkerResult(
            success=True,
            message=f"Legacy browser task completed: {task_type}",
            data={
                "task_type": task_type,
                "session_id": message_data.get("session_id"),
                "status": "processed",
            },
        )
