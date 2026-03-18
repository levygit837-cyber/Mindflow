"""Canonical transport envelope for RabbitMQ messages."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class QueueMessageEnvelope(BaseModel):
    """Transport-safe queue envelope shared across domains."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str
    task_id: str
    task_type: str
    session_id: str | None = None
    run_id: str | None = None
    correlation_id: str
    idempotency_key: str
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any]
