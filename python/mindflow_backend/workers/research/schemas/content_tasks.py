"""Schemas for the research-domain content queue pipeline."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from mindflow_backend.workers.contracts.schemas.envelope import QueueMessageEnvelope


def build_content_task_hash(*, session_id: str, content_sources: list[dict[str, Any]]) -> str:
    normalized = json.dumps(content_sources, sort_keys=True, default=str)
    value = f"{session_id}:{normalized}".encode()
    return hashlib.sha256(value).hexdigest()


class ContentSynthesisPayload(BaseModel):
    """Payload published for queued content synthesis."""

    model_config = ConfigDict(extra="forbid")

    task_type: Literal["content_synthesis"] = "content_synthesis"
    session_id: str
    content_sources: list[dict[str, Any]]
    synthesis_type: str = "comprehensive"
    target_audience: str = "technical"
    synthesis_length: str = "medium"
    agent_id: str = "researcher"
    origin: str = "pinchtab_fleet_service"


def build_content_synthesis_idempotency_key(
    *,
    session_id: str,
    content_sources: list[dict[str, Any]],
) -> str:
    return (
        "content:content_synthesis:"
        f"{build_content_task_hash(session_id=session_id, content_sources=content_sources)}"
    )


def build_content_synthesis_envelope(
    *,
    session_id: str,
    content_sources: list[dict[str, Any]],
    synthesis_type: str = "comprehensive",
    target_audience: str = "technical",
    synthesis_length: str = "medium",
    agent_id: str = "researcher",
    origin: str = "pinchtab_fleet_service",
) -> QueueMessageEnvelope:
    idempotency_key = build_content_synthesis_idempotency_key(
        session_id=session_id,
        content_sources=content_sources,
    )
    payload = ContentSynthesisPayload(
        session_id=session_id,
        content_sources=content_sources,
        synthesis_type=synthesis_type,
        target_audience=target_audience,
        synthesis_length=synthesis_length,
        agent_id=agent_id,
        origin=origin,
    )
    return QueueMessageEnvelope(
        schema_version="1.0",
        task_id=idempotency_key,
        task_type=payload.task_type,
        session_id=session_id,
        correlation_id=idempotency_key,
        idempotency_key=idempotency_key,
        created_at=datetime.now(UTC),
        payload=payload.model_dump(mode="json"),
    )
