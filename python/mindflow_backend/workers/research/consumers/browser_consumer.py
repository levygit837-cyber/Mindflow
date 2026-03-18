"""Research browser queue consumer."""

from __future__ import annotations

from typing import Any

from mindflow_backend.workers.contracts.schemas.envelope import QueueMessageEnvelope
from mindflow_backend.workers.research.interfaces.browser import BrowserTaskExecutor
from mindflow_backend.workers.research.schemas.browser_tasks import (
    BrowserTaskPayload,
    PageScrapingPayload,
    WebSearchPayload,
    build_page_scraping_idempotency_key,
    build_web_search_idempotency_key,
)


class BrowserTaskConsumer:
    """Consumes queued browser work and delegates execution to the fleet service."""

    def __init__(self, browser_executor: BrowserTaskExecutor | None = None) -> None:
        self._service = None
        if browser_executor is None:
            from mindflow_backend.services.core.pinchtab_fleet_service import PinchTabFleetService

            self._service = PinchTabFleetService()
        self._browser_executor = browser_executor or self._service
        self._processed_idempotency_keys: set[str] = set()

    async def consume_browser_task(self, message_data: dict[str, Any]) -> dict[str, Any]:
        payload, idempotency_key = self._parse_message(message_data)

        if idempotency_key in self._processed_idempotency_keys:
            return {
                "status": "duplicate",
                "idempotency_key": idempotency_key,
                "session_id": payload.session_id,
                "task_type": payload.task_type,
            }

        result = await self._browser_executor.execute_browser_task(payload)
        self._processed_idempotency_keys.add(idempotency_key)
        return {
            "status": "processed",
            "idempotency_key": idempotency_key,
            "session_id": payload.session_id,
            "task_type": payload.task_type,
            **result,
        }

    def _parse_message(self, message_data: dict[str, Any]) -> tuple[BrowserTaskPayload, str]:
        if "schema_version" in message_data and "payload" in message_data:
            envelope = QueueMessageEnvelope.model_validate(message_data)
            payload_data = {
                **envelope.payload,
                "session_id": envelope.session_id,
                "task_type": envelope.task_type,
            }
            idempotency_key = envelope.idempotency_key
        else:
            payload_data = dict(message_data)
            idempotency_key = message_data.get("idempotency_key")

        task_type = payload_data.get("task_type")
        if task_type == "web_search":
            payload = WebSearchPayload.model_validate(payload_data)
            idempotency_key = idempotency_key or build_web_search_idempotency_key(
                session_id=payload.session_id,
                query=payload.query,
            )
            return payload, idempotency_key
        if task_type == "page_scraping":
            payload = PageScrapingPayload.model_validate(payload_data)
            idempotency_key = idempotency_key or build_page_scraping_idempotency_key(
                session_id=payload.session_id,
                target_url=payload.target_url,
            )
            return payload, idempotency_key

        raise ValueError(f"Unsupported browser task type: {task_type}")
