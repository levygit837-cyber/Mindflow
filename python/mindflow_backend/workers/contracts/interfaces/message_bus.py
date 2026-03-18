"""Message bus protocol used by worker infrastructure."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class MessageBus(Protocol):
    """Minimal lifecycle contract for an asynchronous message bus."""

    async def connect(self) -> None:
        """Open the underlying transport connection."""

    async def close(self) -> None:
        """Close the underlying transport connection."""
