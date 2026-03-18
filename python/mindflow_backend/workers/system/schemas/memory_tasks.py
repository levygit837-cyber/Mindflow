"""Schemas for the system-domain memory queue pipeline."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from mindflow_backend.workers.contracts.schemas.envelope import QueueMessageEnvelope


def build_memory_content_hash(
    *,
    session_id: str,
    agent_id: str,
    role: str,
    content: str,
) -> str:
    normalized = f"{session_id}:{agent_id}:{role}:{content.strip()}".encode()
    return hashlib.sha256(normalized).hexdigest()


class MemoryMessageRecordedPayload(BaseModel):
    """Payload published when a chat message should enter the memory pipeline."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    agent_id: str
    role: Literal["user", "assistant", "system"]
    content: str
    source_message_id: int | None = None
    source_status: str = "final"
    derived_from_recall: bool = False
    content_hash: str
    origin: str = "stream_runtime"


def build_memory_message_recorded_envelope(
    *,
    session_id: str,
    agent_id: str,
    role: Literal["user", "assistant", "system"],
    content: str,
    source_message_id: int | None = None,
    source_status: str = "final",
    derived_from_recall: bool = False,
    origin: str = "stream_runtime",
) -> QueueMessageEnvelope:
    content_hash = build_memory_content_hash(
        session_id=session_id,
        agent_id=agent_id,
        role=role,
        content=content,
    )
    idempotency_key = (
        f"memory:{source_message_id}"
        if source_message_id is not None
        else f"memory:{content_hash}"
    )

    payload = MemoryMessageRecordedPayload(
        session_id=session_id,
        agent_id=agent_id,
        role=role,
        content=content,
        source_message_id=source_message_id,
        source_status=source_status,
        derived_from_recall=derived_from_recall,
        content_hash=content_hash,
        origin=origin,
    )

    return QueueMessageEnvelope(
        schema_version="1.0",
        task_id=idempotency_key,
        task_type="memory.message.recorded",
        session_id=session_id,
        correlation_id=idempotency_key,
        idempotency_key=idempotency_key,
        created_at=datetime.now(UTC),
        payload=payload.model_dump(mode="json"),
    )
