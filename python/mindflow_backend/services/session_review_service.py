"""Session Review Service for context governance and memory management.

Provides high-level service for managing session reviews, token window
tracking, and coordination with the session review agent.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from mindflow_backend.agents.session_review_agent import get_session_review_agent
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.session.review import (
    ReviewPriority,
    ReviewTask,
    ReviewTriggerType,
    SessionReviewConfig,
    SessionReviewResult,
    TokenWindowTracker,
    WindowProgressInfo,
    WindowSize,
)
from mindflow_backend.storage.postgresql.repositories import ChatRepository
from mindflow_backend.storage.postgresql.review_repository import ReviewRepository

_logger = get_logger(__name__)


class SessionReviewService:
    """Service for managing session reviews and token window tracking."""
    
    def __init__(self) -> None:
        self.settings = get_settings()
        self.chat_repo = ChatRepository()
        self.review_repo = None  # Will be initialized with db session
        self.review_agent = get_session_review_agent()
        self._active_trackers: dict[str, TokenWindowTracker] = {}
    
    async def initialize_session_review(
        self,
        session_id: str,
        window_size: WindowSize = WindowSize.MEDIUM,
        custom_tokens: int | None = None,
        trigger_threshold: int | None = None,
    ) -> SessionReviewConfig:
        """Initialize session review configuration for a new session."""
        from uuid import uuid4
        
        # Determine window size in tokens
        if window_size == WindowSize.CUSTOM and custom_tokens:
            window_tokens = custom_tokens
        else:
            window_tokens = self._get_window_size_tokens(window_size)
        
        # Use default threshold if not provided
        if trigger_threshold is None:
            trigger_threshold = window_tokens
        
        config = SessionReviewConfig(
            session_id=uuid4(),
            window_size=window_size,
            custom_window_tokens=custom_tokens,
            trigger_type=ReviewTriggerType.TOKEN_THRESHOLD,
            trigger_threshold=trigger_threshold,
        )
        
        # Initialize token tracker
        tracker = TokenWindowTracker(
            session_id=config.session_id,
            window_size=window_tokens,
            next_review_threshold=trigger_threshold,
        )
        
        self._active_trackers[str(session_id)] = tracker
        
        _logger.info(
            "session_review_initialized",
            session_id=session_id,
            window_size=window_tokens,
            trigger_threshold=trigger_threshold,
        )
        
        return config
    
    async def update_token_count(
        self,
        session_id: str,
        additional_tokens: int,
    ) -> WindowProgressInfo:
        """Update token count and check if review should be triggered."""
        session_key = str(session_id)
        
        if session_key not in self._active_trackers:
            # Initialize with default settings
            await self.initialize_session_review(session_id)
            session_key = str(session_id)
        
        tracker = self._active_trackers[session_key]
        tracker.total_tokens_processed += additional_tokens
        tracker.tokens_in_current_window += additional_tokens
        tracker.updated_at = datetime.now(UTC)
        
        # Calculate progress
        progress_in_window = tracker.tokens_in_current_window / tracker.next_review_threshold
        overall_progress = tracker.total_tokens_processed / (tracker.window_size * 100)  # Assume 100 windows max
        
        # Create progress info
        progress_info = WindowProgressInfo(
            session_id=tracker.session_id,
            current_window=tracker.get_current_window_bounds(),
            window_index=tracker.current_window,
            progress_in_window=progress_in_window,
            overall_progress=overall_progress,
            tokens_until_next_review=max(0, tracker.next_review_threshold - tracker.tokens_in_current_window),
            estimated_next_review=datetime.now(UTC) + timedelta(
                minutes=max(1, tracker.tokens_until_next_review // 100)  # Rough estimate
            ),
            windows_remaining=100 - tracker.current_window,
        )
        
        # Check if review should be triggered
        if tracker.should_trigger_review(tracker.next_review_threshold):
            await self._trigger_review(session_id, tracker)
        
        return progress_info
    
    async def trigger_manual_review(
        self,
        session_id: str,
        window_index: int | None = None,
        priority: ReviewPriority = ReviewPriority.MEDIUM,
    ) -> SessionReviewResult:
        """Manually trigger a review for a specific window."""
        session_key = str(session_id)
        
        if session_key not in self._active_trackers:
            raise ValueError(f"No active tracker for session {session_id}")
        
        tracker = self._active_trackers[session_key]
        
        if window_index is None:
            window_index = tracker.current_window
        
        # Create review task
        task = ReviewTask(
            session_id=tracker.session_id,
            window_range=tracker.get_window_bounds(window_index),
            window_index=window_index,
            priority=priority,
            task_type="manual_review",
        )
        
        # Execute review
        result = await self._execute_review_task(task)
        
        _logger.info(
            "manual_review_completed",
            session_id=session_id,
            window_index=window_index,
            actions_found=len(result.actions_documented),
            insights_found=len(result.insights_extracted),
        )
        
        return result
    
    async def get_session_progress(self, session_id: str) -> WindowProgressInfo:
        """Get current progress information for a session."""
        session_key = str(session_id)
        
        if session_key not in self._active_trackers:
            raise ValueError(f"No active tracker for session {session_id}")
        
        tracker = self._active_trackers[session_key]
        
        progress_in_window = tracker.tokens_in_current_window / tracker.next_review_threshold
        overall_progress = tracker.total_tokens_processed / (tracker.window_size * 100)
        
        return WindowProgressInfo(
            session_id=tracker.session_id,
            current_window=tracker.get_current_window_bounds(),
            window_index=tracker.current_window,
            progress_in_window=progress_in_window,
            overall_progress=overall_progress,
            tokens_until_next_review=max(0, tracker.next_review_threshold - tracker.tokens_in_current_window),
            estimated_next_review=datetime.now(UTC) + timedelta(
                minutes=max(1, tracker.tokens_until_next_review // 100)
            ),
            windows_remaining=100 - tracker.current_window,
        )
    
    async def get_previous_reviews(
        self,
        session_id: str,
        limit: int = 10,
        db: Session | None = None
    ) -> list[SessionReviewResult]:
        """Get previous review results for a session."""
        if not self.review_repo:
            self.review_repo = ReviewRepository(db)
        
        return await self.review_repo.get_reviews_by_session(session_id, limit)
    
    async def _get_previous_reviews_dict(
        self,
        session_id: str,
        limit: int = 10,
        db: Session | None = None
    ) -> list[dict[str, Any]]:
        """Get previous review results for a session."""
        if not self.review_repo:
            self.review_repo = ReviewRepository(db)
        
        reviews = await self.review_repo.get_reviews_by_session(session_id, limit)
        
        # Convert to dict format for compatibility
        return [
            {
                "id": str(review.id),
                "session_id": review.session_id,
                "window_range": (review.window_start, review.window_end),
                "review_data": review.review_data,
                "priority": review.priority,
                "created_at": review.created_at.isoformat(),
            }
            for review in reviews
        ]
    
    async def _trigger_review(self, session_id: str, tracker: TokenWindowTracker) -> None:
        """Trigger automatic review when threshold is reached."""
        _logger.info(
            "auto_review_triggered",
            session_id=session_id,
            window_index=tracker.current_window,
            tokens_processed=tracker.tokens_in_current_window,
        )
        
        # Create review task
        task = ReviewTask(
            session_id=tracker.session_id,
            window_range=tracker.get_current_window_bounds(),
            window_index=tracker.current_window,
            priority=ReviewPriority.MEDIUM,
            task_type="automatic_threshold",
        )
        
        try:
            # Execute review
            result = await self._execute_review_task(task)
            
            # Advance to next window
            new_bounds = tracker.advance_to_next_window()
            tracker.last_review_at = datetime.now(UTC)
            
            _logger.info(
                "auto_review_completed",
                session_id=session_id,
                window_index=tracker.current_window - 1,  # Already advanced
                new_window_bounds=new_bounds,
                actions_found=len(result.actions_documented),
                insights_found=len(result.insights_extracted),
            )
            
        except Exception as exc:
            _logger.error(
                "auto_review_failed",
                session_id=session_id,
                window_index=tracker.current_window,
                error=str(exc),
            )
    
    async def _execute_review_task(self, task: ReviewTask) -> SessionReviewResult:
        """Execute a review task using the session review agent."""
        from mindflow_backend.schemas.session.review import ReviewExecutionContext
        
        # Get session messages for the window
        session_messages = await self._get_session_messages(
            str(task.session_id), task.window_range
        )
        
        # Create execution context
        context = ReviewExecutionContext(
            task_id=task.task_id,
            session_id=task.session_id,
            window_range=task.window_range,
            session_messages=session_messages,
            agent_capabilities=self.review_agent.agent_config.capabilities,
            max_tokens=task.max_tokens_to_analyze,
            time_limit_minutes=task.max_processing_time_minutes,
            quality_threshold=0.7,
        )
        
        # Execute review
        result = await self.review_agent.review_session_window(task, context)
        
        # Store result (TODO: Implement database storage)
        await self._store_review_result(result)
        
        return result
    
    async def _get_session_messages(
        self,
        session_id: str,
        window_range: tuple[int, int],
    ) -> list[dict[str, Any]]:
        """Get session messages within a token window."""
        # TODO: Implement proper token-based message retrieval
        # For now, get recent messages and filter by approximate token count
        
        with self.chat_repo.get_db() as db:
            messages = self.chat_repo.get_messages(db, session_id, limit=100)
            
            # Convert to dict format
            message_dicts = []
            current_tokens = 0
            
            for msg in messages:
                # Simple token estimation
                token_count = len(msg.content.split()) * 1.3  # Rough estimate
                
                if current_tokens >= window_range[0] and current_tokens < window_range[1]:
                    message_dicts.append({
                        "id": msg.id,
                        "role": msg.role,
                        "content": msg.content,
                        "created_at": msg.created_at.isoformat(),
                        "token_estimate": token_count,
                    })
                
                current_tokens += token_count
                
                if current_tokens >= window_range[1]:
                    break
            
            return message_dicts
    
    async def _store_review_result(self, result: SessionReviewResult, db: Session | None = None) -> None:
        """Store review result in database."""
        if not self.review_repo:
            self.review_repo = ReviewRepository(db)
        
        await self.review_repo.create_review(
            review_id=str(result.review_id),
            session_id=str(result.session_id),
            window_range=result.window_range,
            review_data=result.review_data,
            priority=result.priority,
            created_at=result.created_at
        )
        
        _logger.info(
            "storing_review_result",
            review_id=str(result.review_id),
            session_id=str(result.session_id),
            window_range=result.window_range,
        )
    
    def _get_window_size_tokens(self, window_size: WindowSize) -> int:
        """Get token count for window size."""
        size_mapping = {
            WindowSize.SMALL: 5000,
            WindowSize.MEDIUM: 10000,
            WindowSize.LARGE: 20000,
            WindowSize.EXTRA_LARGE: 50000,
        }
        return size_mapping.get(window_size, 10000)
    
    def get_active_tracker(self, session_id: str) -> TokenWindowTracker | None:
        """Get active token tracker for a session."""
        return self._active_trackers.get(str(session_id))
    
    def remove_session_tracker(self, session_id: str) -> None:
        """Remove tracker for a session (cleanup)."""
        session_key = str(session_id)
        if session_key in self._active_trackers:
            del self._active_trackers[session_key]
            _logger.info("session_tracker_removed", session_id=session_id)


# Global service instance
_session_review_service: SessionReviewService | None = None


def get_session_review_service() -> SessionReviewService:
    """Get or create the global session review service instance."""
    global _session_review_service
    if _session_review_service is None:
        _session_review_service = SessionReviewService()
    return _session_review_service
