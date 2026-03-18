"""Schemas for the system-domain session review queue pipeline."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from mindflow_backend.workers.contracts.schemas.envelope import QueueMessageEnvelope


def build_session_review_idempotency_key(
    *,
    session_id: str,
    window_index: int,
    trigger_type: str,
) -> str:
    return f"session_review:{session_id}:{window_index}:{trigger_type}"


class SessionReviewRequestedPayload(BaseModel):
    """Payload published when a review window should be processed asynchronously."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    window_index: int
    window_range: tuple[int, int]
    trigger_type: str
    priority: str
    tokens_in_window: int
    total_tokens_processed: int
    threshold: int
    origin: str = "session_review_service"
    requested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


def build_session_review_requested_envelope(
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
) -> QueueMessageEnvelope:
    idempotency_key = build_session_review_idempotency_key(
        session_id=session_id,
        window_index=window_index,
        trigger_type=trigger_type,
    )
    payload = SessionReviewRequestedPayload(
        session_id=session_id,
        window_index=window_index,
        window_range=window_range,
        trigger_type=trigger_type,
        priority=priority,
        tokens_in_window=tokens_in_window,
        total_tokens_processed=total_tokens_processed,
        threshold=threshold,
        origin=origin,
    )

    return QueueMessageEnvelope(
        schema_version="1.0",
        task_id=idempotency_key,
        task_type="session_review.requested",
        session_id=session_id,
        correlation_id=idempotency_key,
        idempotency_key=idempotency_key,
        created_at=datetime.now(UTC),
        payload=payload.model_dump(mode="json"),
    )
