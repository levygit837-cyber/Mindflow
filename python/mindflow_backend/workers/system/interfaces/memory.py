"""Interfaces for the system-domain memory queue pipeline."""

from __future__ import annotations

from typing import Any, Protocol

from mindflow_backend.schemas.memory.contracts import MemoryPersistResult


class MemoryPublisher(Protocol):
    """Publisher contract for memory queue events."""

    async def publish_message_recorded(
        self,
        *,
        session_id: str,
        agent_id: str,
        role: str,
        content: str,
        source_message_id: int | None = None,
        source_status: str = "final",
        derived_from_recall: bool = False,
        origin: str = "stream_runtime",
    ) -> bool: ...


class MemoryRecorder(Protocol):
    """Recorder contract consumed by the memory worker pipeline.

    Aligned with MemoryFacade.record_message() — returns MemoryPersistResult
    instead of a bare str so callers receive structured persistence metadata.
    """

    async def record_message(
        self,
        db: Any,
        *,
        session_id: str,
        agent_id: str,
        role: str,
        content: str,
        source_message_id: int | None = None,
        idempotency_key: str | None = None,
        source_status: str = "final",
        derived_from_recall: bool = False,
    ) -> MemoryPersistResult: ...
