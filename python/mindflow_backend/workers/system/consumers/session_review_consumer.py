"""Session review queue consumer for the system-domain worker pipeline."""

from __future__ import annotations

import asyncio
from typing import Any

from mindflow_backend.workers.contracts.schemas.envelope import QueueMessageEnvelope
from mindflow_backend.workers.system.interfaces.session_review import (
    SessionReviewExecutor,
    SessionReviewResultPersister,
)
from mindflow_backend.workers.system.schemas.session_review_tasks import (
    SessionReviewRequestedPayload,
    build_session_review_idempotency_key,
)


class SessionReviewTaskConsumer:
    """Consumes queued session review requests and persists completed results."""

    def __init__(
        self,
        *,
        review_executor: SessionReviewExecutor | None = None,
        result_persister: SessionReviewResultPersister | None = None,
        timeout_seconds: float = 120.0,
    ) -> None:
        self._service = None
        if review_executor is None or result_persister is None:
            from mindflow_backend.services.session_review_service import SessionReviewService

            self._service = SessionReviewService()
        self._review_executor = review_executor or self._service.execute_requested_review
        self._result_persister = result_persister or self._service.persist_review_result
        self._timeout_seconds = timeout_seconds
        self._processed_idempotency_keys: set[str] = set()

    async def consume_requested_review(self, message_data: dict[str, Any]) -> dict[str, Any]:
        payload, idempotency_key = self._parse_message(message_data)

        if idempotency_key in self._processed_idempotency_keys:
            return {
                "status": "duplicate",
                "idempotency_key": idempotency_key,
                "window_index": payload.window_index,
            }

        result = await asyncio.wait_for(
            self._review_executor(payload),
            timeout=self._timeout_seconds,
        )
        review_id = await self._result_persister(result)
        self._processed_idempotency_keys.add(idempotency_key)

        return {
            "status": "processed",
            "idempotency_key": idempotency_key,
            "review_id": review_id or result.review_id,
            "window_index": payload.window_index,
        }

    def _parse_message(
        self,
        message_data: dict[str, Any],
    ) -> tuple[SessionReviewRequestedPayload, str]:
        if "schema_version" in message_data and "payload" in message_data:
            envelope = QueueMessageEnvelope.model_validate(message_data)
            payload = SessionReviewRequestedPayload.model_validate(envelope.payload)
            idempotency_key = envelope.idempotency_key
        else:
            payload_data = {
                field_name: message_data[field_name]
                for field_name in SessionReviewRequestedPayload.model_fields
                if field_name in message_data
            }
            payload = SessionReviewRequestedPayload.model_validate(payload_data)
            idempotency_key = message_data.get("idempotency_key") or build_session_review_idempotency_key(
                session_id=payload.session_id,
                window_index=payload.window_index,
                trigger_type=payload.trigger_type,
            )

        return payload, idempotency_key
