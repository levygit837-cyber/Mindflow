"""Consumer protocol for worker messages."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol, runtime_checkable

from mindflow_backend.workers.contracts.schemas.envelope import QueueMessageEnvelope


@runtime_checkable
class MessageConsumer(Protocol):
    """Minimal contract for consuming and acknowledging queue envelopes."""

    async def consume(
        self,
        handler: Callable[[QueueMessageEnvelope], Awaitable[None]],
    ) -> None:
        """Begin consuming envelopes and dispatch them to the handler."""

    async def ack(self, delivery_tag: str | int) -> None:
        """Acknowledge successful processing for a delivery."""

    async def reject(self, delivery_tag: str | int, *, requeue: bool = False) -> None:
        """Reject a delivery, optionally requeueing it."""
