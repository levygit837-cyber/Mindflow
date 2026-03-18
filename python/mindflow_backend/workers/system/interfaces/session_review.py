"""Interfaces for the system-domain session review queue pipeline."""

from __future__ import annotations

from typing import Awaitable, Protocol, runtime_checkable

from mindflow_backend.schemas.session.review import SessionReviewResult
from mindflow_backend.workers.system.schemas.session_review_tasks import (
    SessionReviewRequestedPayload,
)


class SessionReviewPublisher(Protocol):
    """Publisher contract for queued session review requests."""

    async def publish_review_requested(
        self,
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
    ) -> bool: ...


@runtime_checkable
class SessionReviewExecutor(Protocol):
    """Callable contract for executing a queued session review."""

    async def __call__(
        self,
        payload: SessionReviewRequestedPayload,
    ) -> SessionReviewResult: ...


@runtime_checkable
class SessionReviewResultPersister(Protocol):
    """Callable contract for persisting a completed queued review."""

    async def __call__(
        self,
        result: SessionReviewResult,
    ) -> str | None: ...
