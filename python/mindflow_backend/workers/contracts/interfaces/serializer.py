"""Serialization contracts for queue envelopes."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from mindflow_backend.workers.contracts.schemas.envelope import QueueMessageEnvelope


@runtime_checkable
class MessageSerializer(Protocol):
    """Serializer contract for queue envelopes."""

    def serialize(self, envelope: QueueMessageEnvelope) -> bytes:
        """Encode an envelope into transport bytes."""

    def deserialize(self, payload: bytes) -> QueueMessageEnvelope:
        """Decode transport bytes into an envelope."""


class JsonMessageSerializer:
    """Default JSON serializer for queue envelopes."""

    def serialize(self, envelope: QueueMessageEnvelope) -> bytes:
        return envelope.model_dump_json().encode("utf-8")

    def deserialize(self, payload: bytes) -> QueueMessageEnvelope:
        return QueueMessageEnvelope.model_validate_json(payload)
