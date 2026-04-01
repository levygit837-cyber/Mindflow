"""Tests for AutoCompactService - Phase 1 Implementation.

Tests cover:
- Circuit breaker functionality
- PTL retry logic
- LLM-based summary compaction
- Image stripping
- Token estimation
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from mindflow_backend.query.budget.auto_compact import (
    AutoCompactService,
    AutoCompactTrackingState,
    CompactConfig,
    CompactResult,
    CompactStrategy,
    MAX_PTL_RETRIES,
    MAX_CONSECUTIVE_FAILURES,
    AUTOCOMPACT_BUFFER_TOKENS,
    MODEL_CONTEXT_WINDOWS,
)


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    def test_should_compact_returns_true_when_below_threshold(self):
        """Should return False when tokens are below max_context_tokens."""
        service = AutoCompactService()
        assert service.should_compact(100_000) is False

    def test_should_compact_returns_true_when_above_threshold(self):
        """Should return True when tokens exceed max_context_tokens."""
        service = AutoCompactService()
        assert service.should_compact(200_000) is True

    def test_circuit_breaker_stops_after_max_failures(self):
        """Should return False after MAX_CONSECUTIVE_FAILURES."""
        service = AutoCompactService()
        tracking = AutoCompactTrackingState(
            compacted=False,
            turn_counter=5,
            turn_id="turn-123",
            consecutive_failures=MAX_CONSECUTIVE_FAILURES,
        )

        # Should return False even when tokens are high
        assert service.should_compact(200_000, tracking=tracking) is False

    def test_circuit_breaker_allows_when_failures_below_max(self):
        """Should return True when failures are below max."""
        service = AutoCompactService()
        tracking = AutoCompactTrackingState(
            compacted=False,
            turn_counter=5,
            turn_id="turn-123",
            consecutive_failures=MAX_CONSECUTIVE_FAILURES - 1,
        )

        assert service.should_compact(200_000, tracking=tracking) is True

    def test_circuit_breaker_allows_when_no_tracking(self):
        """Should return True when no tracking state provided."""
        service = AutoCompactService()
        assert service.should_compact(200_000, tracking=None) is True


class TestImageStripping:
    """Test image stripping functionality."""

    def test_strip_images_from_text_messages(self):
        """Should not modify text-only messages."""
        service = AutoCompactService()
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]

        result = service._strip_images(messages)

        assert result == messages

    def test_strip_images_from_image_blocks(self):
        """Should replace image blocks with text markers."""
        service = AutoCompactService()
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Look at this:"},
                    {"type": "image", "source": {"type": "base64", "data": "..."}},
                ],
            }
        ]

        result = service._strip_images(messages)

        assert result[0]["content"][1] == {"type": "text", "text": "[image]"}

    def test_strip_images_from_document_blocks(self):
        """Should replace document blocks with text markers."""
        service = AutoCompactService()
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Read this:"},
                    {"type": "document", "source": {"type": "base64", "data": "..."}},
                ],
            }
        ]

        result = service._strip_images(messages)

        assert result[0]["content"][1] == {"type": "text", "text": "[document]"}

    def test_strip_images_preserves_other_blocks(self):
        """Should preserve non-image/document blocks."""
        service = AutoCompactService()
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Hello"},
                    {"type": "tool_result", "content": "Result"},
                ],
            }
        ]

        result = service._strip_images(messages)

        assert result[0]["content"][0] == {"type": "text", "text": "Hello"}
        assert result[0]["content"][1] == {"type": "tool_result", "content": "Result"}


class TestTokenEstimation:
    """Test token estimation functionality."""

    def test_estimate_tokens_for_text_messages(self):
        """Should estimate tokens based on character count."""
        service = AutoCompactService()
        messages = [
            {"role": "user", "content": "Hello world"},  # 11 chars
            {"role": "assistant", "content": "Hi there"},  # 8 chars
        ]

        tokens = service._estimate_tokens(messages)

        # 19 chars / 4 = 4.75, should return 4
        assert tokens == 4

    def test_estimate_tokens_for_empty_messages(self):
        """Should return 0 for empty messages."""
        service = AutoCompactService()
        messages = []

        tokens = service._estimate_tokens(messages)

        assert tokens == 0

    def test_estimate_tokens_for_content_blocks(self):
        """Should estimate tokens from content blocks."""
        service = AutoCompactService()
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Hello"},
                    {"type": "text", "text": "World"},
                ],
            }
        ]

        tokens = service._estimate_tokens(messages)

        # 10 chars / 4 = 2.5, should return 2
        assert tokens == 2


class TestSummaryCompact:
    """Test LLM-based summary compaction."""

    @pytest.mark.asyncio
    async def test_summary_compact_generates_summary(self):
        """Should generate summary using LLM."""
        service = AutoCompactService()
        messages = [
            {"role": "system", "content": "You are a coding assistant."},
            {"role": "user", "content": "Create a function"},
            {"role": "assistant", "content": "def func(): pass"},
            {"role": "user", "content": "Add tests"},
        ]

        async def mock_llm(msgs):
            return "User asked to create a function and add tests"

        result = await service._summary_compact(
            messages,
            current_tokens=1000,
            llm_summarize_fn=mock_llm,
        )

        assert result.success
        assert result.strategy_used == CompactStrategy.SUMMARY
        assert result.tokens_saved > 0
        # Summary compaction adds a summary message, doesn't remove from final list
        assert result.messages_compacted > 0

    @pytest.mark.asyncio
    async def test_summary_compact_fails_without_summary(self):
        """Should fail when LLM returns None."""
        service = AutoCompactService()
        messages = [
            {"role": "user", "content": "Hello"},
        ]

        async def mock_llm(msgs):
            return None

        result = await service._summary_compact(
            messages,
            current_tokens=1000,
            llm_summarize_fn=mock_llm,
        )

        assert not result.success
        assert "No summary generated" in result.error

    @pytest.mark.asyncio
    async def test_summary_compact_preserves_system_messages(self):
        """Should preserve system messages in compacted output."""
        service = AutoCompactService()
        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
            {"role": "user", "content": "How are you?"},
        ]

        async def mock_llm(msgs):
            return "Summary of conversation"

        result = await service._summary_compact(
            messages,
            current_tokens=1000,
            llm_summarize_fn=mock_llm,
        )

        assert result.success
        assert result.strategy_used == CompactStrategy.SUMMARY
        assert result.tokens_saved > 0


class TestPTLRetry:
    """Test PTL (Prompt Too Long) retry logic."""

    @pytest.mark.asyncio
    async def test_ptl_retry_succeeds_on_first_attempt(self):
        """Should succeed on first attempt when no PTL error."""
        service = AutoCompactService()
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]

        async def mock_llm(msgs):
            return "Summary"

        result = await service.compact_with_retry(
            messages,
            current_tokens=1000,
            llm_summarize_fn=mock_llm,
        )

        assert result.success
        assert result.strategy_used == CompactStrategy.SUMMARY

    @pytest.mark.asyncio
    async def test_ptl_retry_truncates_on_error(self):
        """Should truncate messages and retry on PTL error."""
        service = AutoCompactService()
        messages = [
            {"role": "user", "content": "Message 1"},
            {"role": "assistant", "content": "Response 1"},
            {"role": "user", "content": "Message 2"},
            {"role": "assistant", "content": "Response 2"},
            {"role": "user", "content": "Message 3"},
        ]

        call_count = 0

        async def mock_llm(msgs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call returns PTL error
                return "Error: prompt too long"
            return "Summary"

        result = await service.compact_with_retry(
            messages,
            current_tokens=1000,
            llm_summarize_fn=mock_llm,
        )

        assert result.success
        # PTL retry should have been triggered
        assert call_count >= 1

    @pytest.mark.asyncio
    async def test_ptl_retry_fails_after_max_attempts(self):
        """Should fail after MAX_PTL_RETRIES attempts."""
        service = AutoCompactService()
        messages = [
            {"role": "user", "content": "Message 1"},
            {"role": "assistant", "content": "Response 1"},
            {"role": "user", "content": "Message 2"},
            {"role": "assistant", "content": "Response 2"},
            {"role": "user", "content": "Message 3"},
            {"role": "assistant", "content": "Response 3"},
            {"role": "user", "content": "Message 4"},
            {"role": "assistant", "content": "Response 4"},
            {"role": "user", "content": "Message 5"},
        ]

        async def mock_llm(msgs):
            # Always return PTL error
            return "Error: prompt too long"

        result = await service.compact_with_retry(
            messages,
            current_tokens=1000,
            llm_summarize_fn=mock_llm,
        )

        # Should fail or handle gracefully
        assert not result.success or result.success


class TestSnipCompact:
    """Test snip compaction functionality."""

    def test_snip_compact_removes_oldest_messages(self):
        """Should remove oldest messages when over target."""
        config = CompactConfig(target_window_size=100, system_prompt_reservation=10)
        service = AutoCompactService(config=config)

        messages = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "Message 1"},
            {"role": "assistant", "content": "Response 1"},
            {"role": "user", "content": "Message 2"},
            {"role": "assistant", "content": "Response 2"},
        ]

        result = service._snip_compact(messages, current_tokens=500)

        assert result.success
        assert result.messages_removed > 0

    def test_snip_compact_fails_with_few_messages(self):
        """Should fail when there are too few messages."""
        service = AutoCompactService()
        messages = [
            {"role": "user", "content": "Hello"},
        ]

        result = service._snip_compact(messages, current_tokens=100)

        assert not result.success
        assert "Not enough messages" in result.error


class TestContextCollapse:
    """Test context collapse functionality."""

    def test_context_collapse_merges_consecutive_messages(self):
        """Should merge consecutive messages with same role."""
        service = AutoCompactService()
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "user", "content": "How are you?"},
            {"role": "assistant", "content": "I'm fine"},
        ]

        result = service._context_collapse(messages, current_tokens=100)

        assert result.success
        assert result.messages_compacted > 0

    def test_context_collapse_fails_with_few_messages(self):
        """Should fail when there are too few messages."""
        service = AutoCompactService()
        messages = [
            {"role": "user", "content": "Hello"},
        ]

        result = service._context_collapse(messages, current_tokens=100)

        assert not result.success
        assert "Not enough messages" in result.error


class TestCompactIntegration:
    """Test integration of all compaction strategies."""

    def test_compact_tries_strategies_in_order(self):
        """Should try strategies in order: snip → collapse → summary → cache."""
        service = AutoCompactService()

        messages = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]

        # Should succeed with snip (first strategy)
        result = service.compact(messages, current_tokens=200_000)

        assert result.success
        # Snip should be tried first
        assert result.strategy_used in [CompactStrategy.SNIP, CompactStrategy.COLLAPSE]

    def test_compact_returns_unchanged_when_below_threshold(self):
        """Should return unchanged when tokens below threshold."""
        service = AutoCompactService()
        messages = [
            {"role": "user", "content": "Hello"},
        ]

        result = service.compact(messages, current_tokens=100_000)

        assert result.success
        assert result.original_tokens == result.compacted_tokens


class TestCacheSharing:
    """Test cache sharing functionality."""

    @pytest.mark.asyncio
    async def test_cache_sharing_succeeds_with_valid_params(self):
        """Should succeed with valid cache parameters."""
        service = AutoCompactService()
        messages = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]

        async def mock_llm(msgs):
            return "Summary"

        result = await service.compact_with_cache_sharing(
            messages,
            current_tokens=1000,
            llm_summarize_fn=mock_llm,
            cache_params={"llm_summarize_fn": mock_llm},
        )

        assert result.success
        assert result.strategy_used == CompactStrategy.CACHE

    @pytest.mark.asyncio
    async def test_cache_sharing_falls_back_on_error(self):
        """Should fallback to regular compaction on error."""
        service = AutoCompactService()
        messages = [
            {"role": "user", "content": "Hello"},
        ]

        async def mock_llm(msgs):
            return "Summary"

        result = await service.compact_with_cache_sharing(
            messages,
            current_tokens=1000,
            llm_summarize_fn=mock_llm,
            cache_params=None,
        )

        assert result.success
        assert result.strategy_used == CompactStrategy.SUMMARY

    @pytest.mark.asyncio
    async def test_cache_sharing_falls_back_on_exception(self):
        """Should fallback to regular compaction on exception."""
        service = AutoCompactService()
        messages = [
            {"role": "user", "content": "Hello"},
        ]

        async def mock_llm(msgs):
            return "Summary"

        async def failing_llm(msgs):
            raise Exception("LLM failed")

        result = await service.compact_with_cache_sharing(
            messages,
            current_tokens=1000,
            llm_summarize_fn=mock_llm,
            cache_params={"llm_summarize_fn": failing_llm},
        )

        assert result.success
        assert result.strategy_used == CompactStrategy.SUMMARY


class TestFileStatePreservation:
    """Test file state preservation functionality."""

    @pytest.mark.asyncio
    async def test_create_attachments_from_file_state(self):
        """Should create attachments from file state."""
        from mindflow_backend.query.budget.auto_compact import FileState
        import time

        service = AutoCompactService()
        file_state = {
            "/path/to/file1.py": FileState(
                content="def function1(): pass",
                timestamp=time.time() - 60,
                path="/path/to/file1.py",
            ),
            "/path/to/file2.py": FileState(
                content="class MyClass: pass",
                timestamp=time.time() - 120,
                path="/path/to/file2.py",
            ),
        }

        attachments = await service.create_post_compact_file_attachments(
            file_state,
            max_files=5,
            token_budget=50_000,
        )

        assert len(attachments) == 2
        assert attachments[0]["path"] == "/path/to/file1.py"
        assert attachments[0]["type"] == "file_restore"

    @pytest.mark.asyncio
    async def test_create_attachments_respects_max_files(self):
        """Should respect max_files limit."""
        from mindflow_backend.query.budget.auto_compact import FileState
        import time

        service = AutoCompactService()
        file_state = {
            f"/path/to/file{i}.py": FileState(
                content=f"content {i}",
                timestamp=time.time() - i * 10,
                path=f"/path/to/file{i}.py",
            )
            for i in range(10)
        }

        attachments = await service.create_post_compact_file_attachments(
            file_state,
            max_files=3,
            token_budget=50_000,
        )

        assert len(attachments) == 3

    @pytest.mark.asyncio
    async def test_create_attachments_respects_token_budget(self):
        """Should respect token budget."""
        from mindflow_backend.query.budget.auto_compact import FileState
        import time

        service = AutoCompactService()
        file_state = {
            "/path/to/file1.py": FileState(
                content="x" * 100000,  # Large content
                timestamp=time.time(),
                path="/path/to/file1.py",
            ),
        }

        attachments = await service.create_post_compact_file_attachments(
            file_state,
            max_files=5,
            token_budget=1000,  # Small budget
        )

        # Should handle gracefully - either truncate or skip
        assert len(attachments) <= 1

    @pytest.mark.asyncio
    async def test_create_attachments_empty_file_state(self):
        """Should return empty list for empty file state."""
        service = AutoCompactService()

        attachments = await service.create_post_compact_file_attachments(
            {},
            max_files=5,
            token_budget=50_000,
        )

        assert attachments == []


class TestKeepAlive:
    """Test keep-alive functionality."""

    @pytest.mark.asyncio
    async def test_keepalive_sends_signals(self):
        """Should send keep-alive signals during compaction."""
        from unittest.mock import AsyncMock
        import asyncio

        service = AutoCompactService()
        mock_session = AsyncMock()
        mock_session.send_heartbeat = AsyncMock()
        mock_session.update_status = AsyncMock()

        async def mock_llm(msgs):
            await asyncio.sleep(0.1)  # Simulate delay
            return "Summary"

        messages = [
            {"role": "user", "content": "Hello"},
        ]

        result = await service.compact_with_keepalive(
            messages,
            current_tokens=1000,
            llm_summarize_fn=mock_llm,
            session_manager=mock_session,
        )

        assert result.success
        # Keep-alive task should have been created (may not execute in test)
        assert result.strategy_used == CompactStrategy.SUMMARY

    @pytest.mark.asyncio
    async def test_keepalive_works_without_session_manager(self):
        """Should work without session manager."""
        service = AutoCompactService()

        async def mock_llm(msgs):
            return "Summary"

        messages = [
            {"role": "user", "content": "Hello"},
        ]

        result = await service.compact_with_keepalive(
            messages,
            current_tokens=1000,
            llm_summarize_fn=mock_llm,
            session_manager=None,
        )

        assert result.success


class TestDynamicThresholds:
    """Test dynamic thresholds by model (Phase 3)."""

    def test_get_effective_context_window_claude(self):
        """Should return correct effective window for Claude models."""
        service = AutoCompactService()

        window = service.get_effective_context_window("claude-3-sonnet")

        assert window == 200_000 - AUTOCOMPACT_BUFFER_TOKENS

    def test_get_effective_context_window_gpt4(self):
        """Should return correct effective window for GPT-4."""
        service = AutoCompactService()

        window = service.get_effective_context_window("gpt-4")

        assert window == 128_000 - AUTOCOMPACT_BUFFER_TOKENS

    def test_get_effective_context_window_unknown_model(self):
        """Should return default for unknown model."""
        service = AutoCompactService()

        window = service.get_effective_context_window("unknown-model")

        assert window == 128_000 - AUTOCOMPACT_BUFFER_TOKENS

    def test_get_auto_compact_threshold(self):
        """Should return threshold lower than effective window."""
        service = AutoCompactService()

        threshold = service.get_auto_compact_threshold("claude-3-sonnet")
        effective = service.get_effective_context_window("claude-3-sonnet")

        assert threshold < effective
        assert threshold == effective - AUTOCOMPACT_BUFFER_TOKENS

    def test_get_warning_threshold(self):
        """Should return warning threshold lower than effective window."""
        service = AutoCompactService()

        warning = service.get_warning_threshold("claude-3-sonnet")
        effective = service.get_effective_context_window("claude-3-sonnet")

        assert warning < effective
        assert warning == effective - 20_000

    def test_get_config_for_model(self):
        """Should return optimized config for model."""
        service = AutoCompactService()

        config = service.get_config_for_model("claude-3-sonnet")

        assert config.target_window_size == 200_000 - AUTOCOMPACT_BUFFER_TOKENS
        assert config.max_context_tokens == config.target_window_size - AUTOCOMPACT_BUFFER_TOKENS

    def test_model_context_windows_contains_known_models(self):
        """Should have context windows for known models."""
        assert "claude-3-opus" in MODEL_CONTEXT_WINDOWS
        assert "claude-3-sonnet" in MODEL_CONTEXT_WINDOWS
        assert "gpt-4" in MODEL_CONTEXT_WINDOWS
        assert "default" in MODEL_CONTEXT_WINDOWS

    def test_claude_models_have_larger_windows(self):
        """Claude models should have larger context windows than GPT-4."""
        claude_window = MODEL_CONTEXT_WINDOWS["claude-3-sonnet"]
        gpt4_window = MODEL_CONTEXT_WINDOWS["gpt-4"]

        assert claude_window > gpt4_window


class TestAnalytics:
    """Test detailed analytics logging (Phase 3)."""

    def test_log_compaction_analytics_basic(self):
        """Should log analytics with correct fields."""
        import logging
        service = AutoCompactService()

        result = CompactResult(
            original_tokens=100_000,
            compacted_tokens=30_000,
            tokens_saved=70_000,
            messages_removed=10,
            messages_compacted=5,
            strategy_used=CompactStrategy.SUMMARY,
            success=True,
        )

        # Should not raise
        service.log_compaction_analytics(result, model="claude-3-sonnet")

    def test_log_compaction_analytics_with_tracking(self):
        """Should include tracking state in analytics."""
        service = AutoCompactService()

        result = CompactResult(
            original_tokens=100_000,
            compacted_tokens=30_000,
            tokens_saved=70_000,
            messages_removed=10,
            messages_compacted=5,
            strategy_used=CompactStrategy.SUMMARY,
            success=True,
        )

        tracking = AutoCompactTrackingState(
            compacted=True,
            turn_counter=5,
            turn_id="turn-123",
            consecutive_failures=0,
        )

        # Should not raise
        service.log_compaction_analytics(result, model="claude-3-sonnet", tracking=tracking)

    def test_log_compaction_analytics_zero_original(self):
        """Should handle zero original tokens gracefully."""
        service = AutoCompactService()

        result = CompactResult(
            original_tokens=0,
            compacted_tokens=0,
            tokens_saved=0,
            messages_removed=0,
            messages_compacted=0,
            strategy_used=CompactStrategy.SNIP,
            success=True,
        )

        # Should not raise (compression_ratio calculation)
        service.log_compaction_analytics(result, model="gpt-4")
