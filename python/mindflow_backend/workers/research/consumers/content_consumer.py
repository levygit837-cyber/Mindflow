"""Research content queue consumer."""

from __future__ import annotations

from typing import Any

from mindflow_backend.workers.contracts.schemas.envelope import QueueMessageEnvelope
from mindflow_backend.workers.research.interfaces.content import ContentTaskExecutor
from mindflow_backend.workers.research.schemas.content_tasks import (
    ContentSynthesisPayload,
    build_content_synthesis_idempotency_key,
)


class ContentTaskConsumer:
    """Consumes queued content work and returns a queue-safe synthesis payload."""

    def __init__(self, content_executor: ContentTaskExecutor | None = None) -> None:
        self._content_executor = content_executor
        self._processed_idempotency_keys: set[str] = set()

    async def consume_content_synthesis(self, message_data: dict[str, Any]) -> dict[str, Any]:
        payload, idempotency_key = self._parse_message(message_data)

        if idempotency_key in self._processed_idempotency_keys:
            return {
                "status": "duplicate",
                "idempotency_key": idempotency_key,
                "session_id": payload.session_id,
                "task_type": payload.task_type,
            }

        if self._content_executor is not None:
            result = await self._content_executor.synthesize_content(payload)
        else:
            result = self._synthesize_locally(payload)

        self._processed_idempotency_keys.add(idempotency_key)
        return {
            "status": "processed",
            "idempotency_key": idempotency_key,
            "session_id": payload.session_id,
            "task_type": payload.task_type,
            **result,
        }

    def _parse_message(self, message_data: dict[str, Any]) -> tuple[ContentSynthesisPayload, str]:
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

        payload = ContentSynthesisPayload.model_validate(payload_data)
        idempotency_key = idempotency_key or build_content_synthesis_idempotency_key(
            session_id=payload.session_id,
            content_sources=payload.content_sources,
        )
        return payload, idempotency_key

    def _synthesize_locally(self, payload: ContentSynthesisPayload) -> dict[str, Any]:
        texts = [
            source.get("text", "").strip()
            for source in payload.content_sources
            if isinstance(source, dict) and source.get("text")
        ]
        summary = " ".join(texts).strip()
        if not summary:
            summary = f"{payload.synthesis_type} synthesis requested with {len(payload.content_sources)} source(s)."

        return {
            "session_id": payload.session_id,
            "source_count": len(payload.content_sources),
            "synthesized_content": summary,
            "synthesis_type": payload.synthesis_type,
            "target_audience": payload.target_audience,
            "synthesis_length": payload.synthesis_length,
        }
