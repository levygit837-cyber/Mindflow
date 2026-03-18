"""Publisher protocol for worker messages."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from mindflow_backend.workers.contracts.schemas.envelope import QueueMessageEnvelope


@runtime_checkable
class MessagePublisher(Protocol):
    """Minimal contract for publishing queue envelopes."""

    async def publish(self, queue_name: str, envelope: QueueMessageEnvelope) -> bool:
        """Publish an envelope to the given queue."""
