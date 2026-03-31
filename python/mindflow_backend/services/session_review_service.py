"""Session review service with queue-aware threshold dispatch."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from mindflow_backend.agents.session_review_agent import get_session_review_agent
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.session.review import (
    ReviewExecutionContext,
    ReviewPriority,
    ReviewTask,
    ReviewTriggerType,
    SessionReviewConfig,
    SessionReviewResult,
    TokenWindowTracker,
    WindowProgressInfo,
    WindowSize,
)
from mindflow_backend.storage import ChatRepository, db_session
from mindflow_backend.storage.postgresql.review_repository import ReviewRepository

_logger = get_logger(__name__)


class SessionReviewService:
    """Manage session review windows, fallback execution, and queue dispatch."""

    def __init__(
        self,
        *,
        settings: Any | None = None,
        review_agent: Any | None = None,
        review_publisher: Any | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.chat_repo = ChatRepository()
        self.review_agent = review_agent or get_session_review_agent()
        if review_publisher is None:
            from mindflow_backend.workers.system.publishers.session_review_publisher import (
                RabbitMQSessionReviewTaskPublisher,
            )

            review_publisher = RabbitMQSessionReviewTaskPublisher()
        self.review_publisher = review_publisher
        self._active_trackers: dict[str, TokenWindowTracker] = {}

    async def initialize_session_review(
        self,
        session_id: str,
        window_size: WindowSize = WindowSize.MEDIUM,
        custom_tokens: int | None = None,
        trigger_threshold: int | None = None,
    ) -> SessionReviewConfig:
        """Initialize review tracking for a session."""
        window_tokens = (
            custom_tokens
            if window_size == WindowSize.CUSTOM and custom_tokens
            else self._get_window_size_tokens(window_size)
        )
        threshold = trigger_threshold or window_tokens
        config = SessionReviewConfig(
            session_id=str(session_id),
            window_size=window_size,
            custom_window_tokens=custom_tokens,
            trigger_type=ReviewTriggerType.TOKEN_THRESHOLD,
            trigger_threshold=threshold,
        )
        self._active_trackers[str(session_id)] = TokenWindowTracker(
            session_id=str(session_id),
            window_size=window_tokens,
            next_review_threshold=threshold,
        )
        _logger.info(
            "session_review_initialized",
            session_id=session_id,
            window_size=window_tokens,
            trigger_threshold=threshold,
        )
        return config

    async def update_token_count(
        self,
        session_id: str,
        additional_tokens: int,
    ) -> WindowProgressInfo:
        """Update token counters and queue reviews when thresholds are reached."""
        tracker = await self._get_or_create_tracker(session_id)
        tracker.total_tokens_processed += additional_tokens
        tracker.tokens_in_current_window += additional_tokens
        tracker.updated_at = datetime.now(UTC)

        overflow_tokens = tracker.tokens_in_current_window
        while overflow_tokens >= tracker.next_review_threshold:
            tracker.tokens_in_current_window = tracker.next_review_threshold
            dispatched = await self._dispatch_threshold_review(session_id, tracker)
            if not dispatched:
                tracker.tokens_in_current_window = overflow_tokens
                break

            overflow_tokens -= tracker.next_review_threshold
            tracker.advance_to_next_window()
            tracker.tokens_in_current_window = overflow_tokens
            tracker.last_review_at = datetime.now(UTC)
            tracker.updated_at = datetime.now(UTC)

        return self._build_progress_info(tracker)

    async def trigger_manual_review(
        self,
        session_id: str,
        window_index: int | None = None,
        priority: ReviewPriority = ReviewPriority.MEDIUM,
    ) -> SessionReviewResult:
        """Execute a manual review synchronously to preserve the current contract."""
        tracker = self.get_active_tracker(session_id)
        if tracker is None:
            raise ValueError(f"No active tracker for session {session_id}")

        selected_window = tracker.current_window if window_index is None else window_index
        task = self._build_review_task(
            session_id=str(session_id),
            tracker=tracker,
            window_index=selected_window,
            priority=priority,
            task_type="manual_review",
            trigger_type=ReviewTriggerType.MANUAL,
        )
        result = await self._execute_review_task(task, persist_result=True)
        _logger.info(
            "manual_review_completed",
            session_id=session_id,
            window_index=selected_window,
            actions_found=len(result.actions_documented),
            insights_found=len(result.insights_extracted),
        )
        return result

    async def get_session_progress(self, session_id: str) -> WindowProgressInfo:
        """Return current window progress."""
        tracker = self.get_active_tracker(session_id)
        if tracker is None:
            raise ValueError(f"No active tracker for session {session_id}")
        return self._build_progress_info(tracker)

    async def get_previous_reviews(
        self,
        session_id: str,
        limit: int = 10,
        db: Session | None = None,
    ) -> list[Any]:
        """Get stored review records for a session."""
        if db is not None:
            return await ReviewRepository(db).get_reviews_by_session(session_id, limit)
        if db_session is None:
            return []
        with db_session() as sync_db:
            return await ReviewRepository(sync_db).get_reviews_by_session(session_id, limit)

    async def execute_requested_review(
        self,
        payload: SessionReviewRequestedPayload,
    ) -> SessionReviewResult:
        """Execute a queued review request without persisting it twice."""
        tracker = self.get_active_tracker(payload.session_id)
        window_size = max(1, payload.window_range[1] - payload.window_range[0])
        queue_tracker = tracker or TokenWindowTracker(
            session_id=payload.session_id,
            window_size=window_size,
            current_window=payload.window_index,
            tokens_in_current_window=payload.tokens_in_window,
            total_tokens_processed=payload.total_tokens_processed,
            next_review_threshold=payload.threshold,
        )
        task = self._build_review_task(
            session_id=payload.session_id,
            tracker=queue_tracker,
            window_index=payload.window_index,
            priority=ReviewPriority(payload.priority),
            task_type=payload.trigger_type,
            trigger_type=ReviewTriggerType.TOKEN_THRESHOLD,
            window_range=payload.window_range,
        )
        return await self._execute_review_task(task, persist_result=False)

    async def persist_review_result(
        self,
        result: SessionReviewResult,
    ) -> str | None:
        """Persist a queued review result."""
        try:
            return await self._store_review_result(result)
        except Exception as exc:  # pragma: no cover - DB wiring depends on runtime env
            _logger.error(
                "persist_review_result_failed",
                review_id=result.review_id,
                session_id=result.session_id,
                error=str(exc),
            )
            return None

    async def _dispatch_threshold_review(
        self,
        session_id: str,
        tracker: TokenWindowTracker,
    ) -> bool:
        """Dispatch threshold reviews to RabbitMQ or inline fallback."""
        task = self._build_review_task(
            session_id=str(session_id),
            tracker=tracker,
            window_index=tracker.current_window,
            priority=ReviewPriority.MEDIUM,
            task_type="automatic_threshold",
            trigger_type=ReviewTriggerType.TOKEN_THRESHOLD,
        )
        queue_enabled = self.settings.get_feature_flag(
            "rabbitmq_session_review_pipeline_enabled",
            False,
        )
        fallback_enabled = self.settings.get_feature_flag(
            "rabbitmq_session_review_publish_fallback_local",
            True,
        )

        if queue_enabled:
            try:
                published = await self.review_publisher.publish_review_requested(
                    session_id=task.session_id,
                    window_index=task.window_index,
                    window_range=task.window_range,
                    trigger_type=task.task_type,
                    priority=task.priority.value,
                    tokens_in_window=tracker.tokens_in_current_window,
                    total_tokens_processed=tracker.total_tokens_processed,
                    threshold=tracker.next_review_threshold,
                )
                if published:
                    _logger.info(
                        "session_review_queued",
                        session_id=session_id,
                        window_index=task.window_index,
                        window_range=task.window_range,
                    )
                    return True
            except Exception as exc:
                _logger.error(
                    "session_review_publish_failed",
                    session_id=session_id,
                    window_index=task.window_index,
                    error=str(exc),
                )
                if not fallback_enabled:
                    return False

        if not fallback_enabled and queue_enabled:
            return False

        try:
            result = await self._execute_review_task(task, persist_result=True)
            _logger.info(
                "auto_review_completed",
                session_id=session_id,
                window_index=task.window_index,
                actions_found=len(result.actions_documented),
                insights_found=len(result.insights_extracted),
            )
            return True
        except Exception as exc:
            _logger.error(
                "auto_review_failed",
                session_id=session_id,
                window_index=task.window_index,
                error=str(exc),
            )
            return False

    async def _execute_review_task(
        self,
        task: ReviewTask,
        *,
        persist_result: bool,
    ) -> SessionReviewResult:
        """Execute a review task using the active review agent."""
        session_messages = await self._get_session_messages(task.session_id, task.window_range)
        capabilities = list(
            getattr(getattr(self.review_agent, "agent_config", None), "capabilities", [])
        )
        context = ReviewExecutionContext(
            task_id=task.task_id,
            session_id=task.session_id,
            window_range=task.window_range,
            session_messages=session_messages,
            agent_capabilities=capabilities,
            max_tokens=task.max_tokens_to_analyze,
            time_limit_minutes=task.max_processing_time_minutes,
            quality_threshold=0.7,
        )
        raw_result = await self.review_agent.review_session_window(
            task=task,
            context=context,
            window_index=task.window_index,
        )
        result = self._normalize_review_result(raw_result, task)
        if persist_result:
            try:
                await self._store_review_result(result)
            except Exception as exc:  # pragma: no cover - DB wiring depends on runtime env
                _logger.error(
                    "store_review_result_failed",
                    review_id=result.review_id,
                    session_id=result.session_id,
                    error=str(exc),
                )
        return result

    async def _get_session_messages(
        self,
        session_id: str,
        window_range: tuple[int, int],
    ) -> list[dict[str, Any]]:
        """Get session messages within an approximate token window."""
        if db_session is None:
            return []

        with db_session() as db:
            messages = self.chat_repo.get_messages(db, session_id)

        message_dicts: list[dict[str, Any]] = []
        current_tokens = 0.0
        for msg in messages:
            token_count = max(1.0, len((msg.content or "").split()) * 1.3)
            if current_tokens >= window_range[0] and current_tokens < window_range[1]:
                message_dicts.append(
                    {
                        "id": getattr(msg, "id", None),
                        "role": getattr(msg, "role", "unknown"),
                        "content": getattr(msg, "content", ""),
                        "created_at": getattr(msg, "created_at", datetime.now(UTC)).isoformat(),
                        "token_estimate": token_count,
                    }
                )
            current_tokens += token_count
            if current_tokens >= window_range[1]:
                break
        return message_dicts

    async def _store_review_result(
        self,
        result: SessionReviewResult,
        db: Session | None = None,
    ) -> str | None:
        """Store a session review result in the relational store."""
        if db is not None:
            await ReviewRepository(db).create_review(
                review_id=str(result.review_id),
                session_id=str(result.session_id),
                window_range=result.window_range,
                review_data=result.review_data,
                priority=result.priority,
                created_at=result.created_at,
            )
            if hasattr(db, "commit"):
                db.commit()
            return result.review_id

        if db_session is None:
            return None

        with db_session() as sync_db:
            await ReviewRepository(sync_db).create_review(
                review_id=str(result.review_id),
                session_id=str(result.session_id),
                window_range=result.window_range,
                review_data=result.review_data,
                priority=result.priority,
                created_at=result.created_at,
            )
            if hasattr(sync_db, "commit"):
                sync_db.commit()
        return result.review_id

    def _build_review_task(
        self,
        *,
        session_id: str,
        tracker: TokenWindowTracker,
        window_index: int,
        priority: ReviewPriority,
        task_type: str,
        trigger_type: ReviewTriggerType,
        window_range: tuple[int, int] | None = None,
    ) -> ReviewTask:
        return ReviewTask(
            session_id=session_id,
            window_range=window_range or tracker.get_window_bounds(window_index),
            window_index=window_index,
            priority=priority,
            task_type=task_type,
            trigger_type=trigger_type,
            title=f"Session review window {window_index}",
            parameters={
                "window_size": tracker.window_size,
                "threshold": tracker.next_review_threshold,
            },
            max_tokens_to_analyze=tracker.window_size,
            max_processing_time_minutes=10,
        )

    def _normalize_review_result(
        self,
        raw_result: Any,
        task: ReviewTask,
    ) -> SessionReviewResult:
        if isinstance(raw_result, SessionReviewResult):
            return raw_result
        if isinstance(raw_result, dict):
            return SessionReviewResult(
                session_id=task.session_id,
                window_range=task.window_range,
                priority=task.priority,
                summary_text=str(raw_result.get("summary_text", "")),
                actions_documented=list(raw_result.get("actions_documented", [])),
                insights_extracted=list(raw_result.get("insights_extracted", [])),
                review_data=dict(raw_result.get("review_data", raw_result)),
            )
        review_data = getattr(raw_result, "review_data", None)
        if not isinstance(review_data, dict):
            review_data = {
                "summary_text": getattr(raw_result, "summary_text", ""),
                "actions_documented": list(getattr(raw_result, "actions_documented", [])),
                "insights_extracted": list(getattr(raw_result, "insights_extracted", [])),
            }

        return SessionReviewResult(
            session_id=task.session_id,
            window_range=task.window_range,
            priority=task.priority,
            summary_text=str(getattr(raw_result, "summary_text", "")),
            actions_documented=list(getattr(raw_result, "actions_documented", [])),
            insights_extracted=list(getattr(raw_result, "insights_extracted", [])),
            review_data=review_data,
        )

    def _build_progress_info(self, tracker: TokenWindowTracker) -> WindowProgressInfo:
        progress_in_window = (
            tracker.tokens_in_current_window / tracker.next_review_threshold
            if tracker.next_review_threshold
            else 0.0
        )
        overall_progress = (
            tracker.total_tokens_processed / (tracker.window_size * 100)
            if tracker.window_size
            else 0.0
        )
        return WindowProgressInfo(
            session_id=tracker.session_id,
            current_window=tracker.get_current_window_bounds(),
            window_index=tracker.current_window,
            progress_in_window=progress_in_window,
            overall_progress=overall_progress,
            tokens_until_next_review=tracker.tokens_until_next_review,
            estimated_next_review=datetime.now(UTC)
            + timedelta(minutes=max(1, tracker.tokens_until_next_review // 100)),
            windows_remaining=max(0, 100 - tracker.current_window),
        )

    async def _get_or_create_tracker(self, session_id: str) -> TokenWindowTracker:
        tracker = self.get_active_tracker(session_id)
        if tracker is not None:
            return tracker
        await self.initialize_session_review(session_id)
        created = self.get_active_tracker(session_id)
        assert created is not None
        return created

    def _get_window_size_tokens(self, window_size: WindowSize) -> int:
        size_mapping = {
            WindowSize.SMALL: 5_000,
            WindowSize.MEDIUM: 10_000,
            WindowSize.LARGE: 20_000,
            WindowSize.EXTRA_LARGE: 50_000,
            WindowSize.CUSTOM: getattr(self.settings, "execution_window_size", 10_000),
        }
        return size_mapping.get(window_size, 10_000)

    def get_active_tracker(self, session_id: str) -> TokenWindowTracker | None:
        return self._active_trackers.get(str(session_id))

    def remove_session_tracker(self, session_id: str) -> None:
        self._active_trackers.pop(str(session_id), None)
