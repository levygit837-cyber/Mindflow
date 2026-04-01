"""Tests for error classifier."""

import asyncio
import pytest

from mindflow_backend.infra.error_handling.classifier import (
    ErrorCategory,
    classify_error,
    is_retryable,
)


class TestClassifyError:
    """Tests for classify_error function."""

    def test_cancelled_error(self):
        """CancelledError should be classified as ABORTED."""
        error = asyncio.CancelledError()
        assert classify_error(error) == ErrorCategory.ABORTED

    def test_timeout_error(self):
        """TimeoutError should be classified as TIMEOUT."""
        error = TimeoutError("Connection timed out")
        assert classify_error(error) == ErrorCategory.TIMEOUT

    def test_unknown_error(self):
        """Unknown errors should be classified as UNKNOWN."""
        error = ValueError("Some error")
        assert classify_error(error) == ErrorCategory.UNKNOWN

    def test_error_with_timeout_in_message(self):
        """Errors with 'timeout' in message should be TIMEOUT."""
        error = Exception("Request timeout occurred")
        assert classify_error(error) == ErrorCategory.TIMEOUT

    def test_error_with_rate_limit_in_message(self):
        """Errors with 'rate limit' in message should be RATE_LIMIT."""
        error = Exception("Rate limit exceeded")
        assert classify_error(error) == ErrorCategory.RATE_LIMIT

    def test_error_with_overload_in_message(self):
        """Errors with 'overload' in message should be SERVER_OVERLOAD."""
        error = Exception("Server overloaded")
        assert classify_error(error) == ErrorCategory.SERVER_OVERLOAD


class TestIsRetryable:
    """Tests for is_retryable function."""

    def test_timeout_is_retryable(self):
        """Timeout errors should be retryable."""
        error = TimeoutError()
        assert is_retryable(error) is True

    def test_cancelled_is_not_retryable(self):
        """Cancelled errors should not be retryable."""
        error = asyncio.CancelledError()
        assert is_retryable(error) is False

    def test_unknown_is_not_retryable(self):
        """Unknown errors should not be retryable."""
        error = ValueError()
        assert is_retryable(error) is False
