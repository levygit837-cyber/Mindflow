"""Tests for retry manager."""

import asyncio
import pytest

from mindflow_backend.infra.error_handling.retry_manager import (
    QuerySource,
    FOREGROUND_RETRY_SOURCES,
    RetryConfig,
    get_retry_delay,
    is_foreground_source,
    should_retry_status,
)


class TestQuerySource:
    """Tests for QuerySource enum."""

    def test_foreground_sources(self):
        """Foreground sources should be in FOREGROUND_RETRY_SOURCES."""
        assert QuerySource.REPL_MAIN_THREAD in FOREGROUND_RETRY_SOURCES
        assert QuerySource.AGENT_DEFAULT in FOREGROUND_RETRY_SOURCES
        assert QuerySource.COMPACT in FOREGROUND_RETRY_SOURCES

    def test_background_not_in_foreground(self):
        """Background source should not be in FOREGROUND_RETRY_SOURCES."""
        assert QuerySource.BACKGROUND not in FOREGROUND_RETRY_SOURCES


class TestGetRetryDelay:
    """Tests for get_retry_delay function."""

    def test_basic_exponential_backoff(self):
        """Delay should increase exponentially."""
        delay1 = get_retry_delay(0)
        delay2 = get_retry_delay(1)
        delay3 = get_retry_delay(2)
        assert delay1 < delay2 < delay3

    def test_retry_after_overrides(self):
        """Retry-After header should override calculated delay."""
        delay = get_retry_delay(0, retry_after="5.0")
        assert delay == 5.0

    def test_invalid_retry_after_ignored(self):
        """Invalid Retry-After should be ignored."""
        delay = get_retry_delay(0, retry_after="invalid")
        assert delay > 0


class TestIsForegroundSource:
    """Tests for is_foreground_source function."""

    def test_foreground_source(self):
        """Foreground source should return True."""
        assert is_foreground_source(QuerySource.REPL_MAIN_THREAD) is True

    def test_background_source(self):
        """Background source should return False."""
        assert is_foreground_source(QuerySource.BACKGROUND) is False

    def test_none_defaults_to_foreground(self):
        """None source should default to foreground."""
        assert is_foreground_source(None) is True


class TestShouldRetryStatus:
    """Tests for should_retry_status function."""

    def test_retryable_status(self):
        """429 and 500 should be retryable."""
        config = RetryConfig()
        assert should_retry_status(429, config) is True
        assert should_retry_status(500, config) is True
        assert should_retry_status(529, config) is True

    def test_non_retryable_status(self):
        """400 and 404 should not be retryable."""
        config = RetryConfig()
        assert should_retry_status(400, config) is False
        assert should_retry_status(404, config) is False
