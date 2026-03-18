"""Memory queue consumer for the system-domain worker pipeline."""

from __future__ import annotations

from typing import Any

from mindflow_backend.schemas.memory.contracts import MemoryPersistResult
from mindflow_backend.workers.contracts.schemas.envelope import QueueMessageEnvelope
from mindflow_backend.workers.system.interfaces.memory import MemoryRecorder
from mindflow_backend.workers.system.schemas.memory_tasks import MemoryMessageRecordedPayload

try:
    from mindflow_backend.memory import get_memory_service as _get_memory_service
except Exception:  # pragma: no cover - import guard for lean test envs
    _get_memory_service = None

try:
    from mindflow_backend.infra.database.connection import get_db_session as _db_session
except Exception:  # pragma: no cover - import guard for lean test envs
    _db_session = None


_UNSET = object()


class MemoryTaskConsumer:
    """Consumes memory events and persists them with the active memory service."""

    def __init__(
        self,
        *,
        memory_service: MemoryRecorder | None = None,
        db_session_factory=_UNSET,
    ) -> None:
        self._memory_service = memory_service or (
            _get_memory_service() if _get_memory_service is not None else None
        )
        # Use module-level default only when no factory was explicitly provided.
        # Passing db_session_factory=None forces "no factory" (useful in tests).
        self._db_session_factory = _db_session if db_session_factory is _UNSET else db_session_factory

    async def consume_message_recorded(self, message_data: dict[str, Any]) -> dict[str, Any]:
        payload, idempotency_key = self._parse_message(message_data)

        if self._db_session_factory is None:
            raise RuntimeError("No database session factory available for memory consumer")

        async with self._db_session_factory() as db:
            raw_result = await self._memory_service.record_message(
                db,
                session_id=payload.session_id,
                agent_id=payload.agent_id,
                role=payload.role,
                content=payload.content,
                source_message_id=payload.source_message_id,
                idempotency_key=idempotency_key,
                source_status=payload.source_status,
                derived_from_recall=payload.derived_from_recall,
            )
            result = self._normalize_result(raw_result)

        return {
            "status": "duplicate" if result.was_deduplicated else "processed",
            "embedding_id": result.embedding_id,
            "event_id": result.event_id,
            "idempotency_key": idempotency_key,
            "source_message_id": payload.source_message_id,
        }

    def _parse_message(self, message_data: dict[str, Any]) -> tuple[MemoryMessageRecordedPayload, str]:
        if "schema_version" in message_data and "payload" in message_data:
            envelope = QueueMessageEnvelope.model_validate(message_data)
            payload = MemoryMessageRecordedPayload.model_validate(envelope.payload)
            idempotency_key = envelope.idempotency_key
        else:
            payload_data = {
                field_name: message_data[field_name]
                for field_name in MemoryMessageRecordedPayload.model_fields
                if field_name in message_data
            }
            payload = MemoryMessageRecordedPayload.model_validate(payload_data)
            idempotency_key = message_data.get("idempotency_key") or f"memory:{payload.content_hash}"

        return payload, idempotency_key

    def _normalize_result(self, result: Any) -> MemoryPersistResult:
        if isinstance(result, MemoryPersistResult):
            return result
        if isinstance(result, str):
            return MemoryPersistResult(embedding_id=result)
        if isinstance(result, dict):
            return MemoryPersistResult(**result)
        embedding_id = getattr(result, "embedding_id", None)
        if not isinstance(embedding_id, str):
            embedding_id = None
        event_id = getattr(result, "event_id", None)
        if not isinstance(event_id, int):
            event_id = None
        was_deduplicated = getattr(result, "was_deduplicated", False)
        if not isinstance(was_deduplicated, bool):
            was_deduplicated = False
        token_count = getattr(result, "token_count", 0)
        if not isinstance(token_count, int):
            token_count = 0
        return MemoryPersistResult(
            embedding_id=embedding_id,
            event_id=event_id,
            was_deduplicated=was_deduplicated,
            token_count=token_count,
        )
