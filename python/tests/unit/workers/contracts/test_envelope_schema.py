from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from mindflow_backend.workers.contracts.interfaces.consumer import MessageConsumer
from mindflow_backend.workers.contracts.interfaces.message_bus import MessageBus
from mindflow_backend.workers.contracts.interfaces.publisher import MessagePublisher
from mindflow_backend.workers.contracts.interfaces.serializer import (
    JsonMessageSerializer,
    MessageSerializer,
)
from mindflow_backend.workers.contracts.schemas.envelope import QueueMessageEnvelope
from mindflow_backend.workers.contracts.schemas.health import WorkerHealthSnapshot
from mindflow_backend.workers.contracts.schemas.result import MessageProcessingResult
from mindflow_backend.workers.contracts.schemas.retry_policy import RetryPolicy


def test_queue_message_envelope_requires_schema_version() -> None:
    with pytest.raises(ValidationError):
        QueueMessageEnvelope(
            task_id="task-1",
            task_type="system.health.check",
            correlation_id="corr-1",
            idempotency_key="idem-1",
            created_at=datetime.now(UTC),
            payload={"ok": True},
        )


def test_json_serializer_rejects_payload_without_schema_version() -> None:
    serializer = JsonMessageSerializer()

    with pytest.raises(ValidationError):
        serializer.deserialize(
            b'{"task_id":"task-1","task_type":"system.health.check","correlation_id":"corr-1","idempotency_key":"idem-1","created_at":"2026-03-16T00:00:00Z","payload":{"ok":true}}'
        )


def test_json_serializer_round_trip() -> None:
    serializer = JsonMessageSerializer()
    envelope = QueueMessageEnvelope(
        schema_version="1.0",
        task_id="task-1",
        task_type="system.health.check",
        session_id="session-1",
        run_id="run-1",
        correlation_id="corr-1",
        idempotency_key="idem-1",
        created_at=datetime(2026, 3, 16, tzinfo=UTC),
        payload={"ok": True},
        metadata={"source": "test"},
    )

    encoded = serializer.serialize(envelope)
    decoded = serializer.deserialize(encoded)

    assert decoded == envelope


def test_contract_protocols_expose_minimum_methods() -> None:
    assert {"connect", "close"} <= set(MessageBus.__dict__.keys())
    assert {"publish"} <= set(MessagePublisher.__dict__.keys())
    assert {"consume", "ack", "reject"} <= set(MessageConsumer.__dict__.keys())
    assert {"serialize", "deserialize"} <= set(MessageSerializer.__dict__.keys())


def test_supporting_contract_schemas_validate_defaults() -> None:
    retry_policy = RetryPolicy(max_retries=3, retry_delay_seconds=30)
    result = MessageProcessingResult(success=True, message="processed")
    health = WorkerHealthSnapshot(
        worker_name="health_worker",
        worker_type="health",
        queue_name="mindflow.system.health.low",
        status="idle",
    )

    assert retry_policy.max_retries == 3
    assert result.success is True
    assert health.status == "idle"
