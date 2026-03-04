"""Tests for Session Review Service functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from omnimind_backend.schemas.session_review import (
    ReviewPriority,
    ReviewTask,
    ReviewTriggerType,
    SessionReviewConfig,
    WindowProgressInfo,
    WindowSize,
)
from omnimind_backend.services.session_review_service import SessionReviewService


@pytest.fixture
def session_review_service():
    """Create a session review service for testing."""
    return SessionReviewService()


@pytest.fixture
def sample_session_id():
    """Sample session ID for testing."""
    return "test-session-123"


class TestSessionReviewService:
    """Test cases for SessionReviewService."""
    
    @pytest.mark.asyncio
    async def test_initialize_session_review(self, session_review_service, sample_session_id):
        """Test initializing session review configuration."""
        config = await session_review_service.initialize_session_review(
            sample_session_id,
            window_size=WindowSize.MEDIUM,
        )
        
        assert config.session_id is not None
        assert config.window_size == WindowSize.MEDIUM
        assert config.trigger_type == ReviewTriggerType.TOKEN_THRESHOLD
        assert config.trigger_threshold == 10000
        assert config.enabled is True
        
        # Check that tracker was created
        tracker = session_review_service.get_active_tracker(sample_session_id)
        assert tracker is not None
        assert tracker.window_size == 10000
        assert tracker.current_window == 0
        assert tracker.tokens_in_current_window == 0
    
    @pytest.mark.asyncio
    async def test_update_token_count_no_trigger(self, session_review_service, sample_session_id):
        """Test updating token count without triggering review."""
        await session_review_service.initialize_session_review(sample_session_id)
        
        # Add tokens below threshold
        progress = await session_review_service.update_token_count(sample_session_id, 1000)
        
        assert progress.session_id is not None
        assert progress.progress_in_window == 0.1  # 1000/10000
        assert progress.tokens_until_next_review == 9000
        assert progress.window_index == 0
    
    @pytest.mark.asyncio
    async def test_update_token_count_trigger_review(self, session_review_service, sample_session_id):
        """Test updating token count that triggers review."""
        # Mock the review agent
        session_review_service.review_agent = AsyncMock()
        mock_result = MagicMock()
        mock_result.actions_documented = []
        mock_result.insights_extracted = []
        mock_result.summary_text = "Test summary"
        session_review_service.review_agent.review_session_window.return_value = mock_result
        
        await session_review_service.initialize_session_review(sample_session_id)
        
        # Add tokens above threshold
        progress = await session_review_service.update_token_count(sample_session_id, 15000)
        
        # Should have triggered review and advanced window
        assert progress.window_index >= 1  # Advanced to next window
        assert progress.progress_in_window < 0.5  # Reset for new window
        
        # Check that review was called
        session_review_service.review_agent.review_session_window.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_manual_review_trigger(self, session_review_service, sample_session_id):
        """Test manually triggering a review."""
        # Mock the review agent
        session_review_service.review_agent = AsyncMock()
        mock_result = MagicMock()
        mock_result.actions_documented = []
        mock_result.insights_extracted = []
        mock_result.summary_text = "Manual review summary"
        session_review_service.review_agent.review_session_window.return_value = mock_result
        
        await session_review_service.initialize_session_review(sample_session_id)
        
        # Trigger manual review for window 0
        result = await session_review_service.trigger_manual_review(
            sample_session_id,
            window_index=0,
            priority=ReviewPriority.HIGH,
        )
        
        assert result.summary_text == "Manual review summary"
        assert result.window_range == (0, 10000)
        
        # Check that review was called with correct parameters
        session_review_service.review_agent.review_session_window.assert_called_once()
        call_args = session_review_service.review_agent.review_session_window.call_args[1]
        assert call_args['window_index'] == 0
    
    @pytest.mark.asyncio
    async def test_get_session_progress(self, session_review_service, sample_session_id):
        """Test getting session progress information."""
        await session_review_service.initialize_session_review(sample_session_id)
        
        # Add some tokens
        await session_review_service.update_token_count(sample_session_id, 2500)
        
        progress = await session_review_service.get_session_progress(sample_session_id)
        
        assert progress.session_id is not None
        assert progress.window_index == 0
        assert progress.progress_in_window == 0.25  # 2500/10000
        assert progress.tokens_until_next_review == 7500
        assert progress.windows_remaining == 100
    
    def test_get_window_size_tokens(self, session_review_service):
        """Test conversion of window sizes to token counts."""
        assert session_review_service._get_window_size_tokens(WindowSize.SMALL) == 5000
        assert session_review_service._get_window_size_tokens(WindowSize.MEDIUM) == 10000
        assert session_review_service._get_window_size_tokens(WindowSize.LARGE) == 20000
        assert session_review_service._get_window_size_tokens(WindowSize.EXTRA_LARGE) == 50000
    
    def test_remove_session_tracker(self, session_review_service, sample_session_id):
        """Test removing session tracker."""
        import asyncio
        
        # Initialize tracker
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                session_review_service.initialize_session_review(sample_session_id)
            )
        finally:
            loop.close()
        
        # Verify tracker exists
        assert session_review_service.get_active_tracker(sample_session_id) is not None
        
        # Remove tracker
        session_review_service.remove_session_tracker(sample_session_id)
        
        # Verify tracker is gone
        assert session_review_service.get_active_tracker(sample_session_id) is None
    
    @pytest.mark.asyncio
    async def test_custom_window_size(self, session_review_service, sample_session_id):
        """Test initializing with custom window size."""
        config = await session_review_service.initialize_session_review(
            sample_session_id,
            window_size=WindowSize.CUSTOM,
            custom_tokens=15000,
        )
        
        tracker = session_review_service.get_active_tracker(sample_session_id)
        assert tracker.window_size == 15000
        assert config.custom_window_tokens == 15000
    
    @pytest.mark.asyncio
    async def test_multiple_windows_advancement(self, session_review_service, sample_session_id):
        """Test advancing through multiple windows."""
        # Mock the review agent to avoid actual reviews
        session_review_service.review_agent = AsyncMock()
        mock_result = MagicMock()
        mock_result.actions_documented = []
        mock_result.insights_extracted = []
        session_review_service.review_agent.review_session_window.return_value = mock_result
        
        await session_review_service.initialize_session_review(sample_session_id)
        
        # Add enough tokens for multiple windows
        await session_review_service.update_token_count(sample_session_id, 25000)
        
        tracker = session_review_service.get_active_tracker(sample_session_id)
        assert tracker.current_window >= 2  # Should advance through multiple windows
        assert tracker.windows_completed >= 2
        assert tracker.tokens_in_current_window >= 0  # Should be reset for current window


class TestTokenWindowTracker:
    """Test cases for TokenWindowTracker functionality."""
    
    def test_should_trigger_review(self):
        """Test review trigger logic."""
        from omnimind_backend.schemas.session_review import TokenWindowTracker
        
        tracker = TokenWindowTracker(
            session_id="test",
            window_size=10000,
            next_review_threshold=10000,
        )
        
        # Should not trigger
        assert not tracker.should_trigger_review(10000)
        
        # Should trigger
        tracker.tokens_in_current_window = 10000
        assert tracker.should_trigger_review(10000)
        
        # Should trigger with higher threshold
        assert tracker.should_trigger_review(5000)
    
    def test_advance_to_next_window(self):
        """Test window advancement logic."""
        from omnimind_backend.schemas.session_review import TokenWindowTracker
        
        tracker = TokenWindowTracker(
            session_id="test",
            window_size=10000,
            current_window=0,
            tokens_in_current_window=8000,
        )
        
        new_bounds = tracker.advance_to_next_window()
        
        assert tracker.current_window == 1
        assert tracker.tokens_in_current_window == 0
        assert tracker.windows_completed == 1
        assert new_bounds == (10000, 20000)
    
    def test_get_current_window_bounds(self):
        """Test getting current window bounds."""
        from omnimind_backend.schemas.session_review import TokenWindowTracker
        
        tracker = TokenWindowTracker(
            session_id="test",
            window_size=10000,
            current_window=2,
        )
        
        bounds = tracker.get_current_window_bounds()
        assert bounds == (20000, 30000)
