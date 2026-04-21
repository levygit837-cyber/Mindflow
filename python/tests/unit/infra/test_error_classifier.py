"""Tests for error classifier module.

Tests error classification, severity levels, and retryability detection.
"""

from __future__ import annotations

import asyncio

import pytest

from mindflow_backend.infra.error_handling.classifier import (
    ErrorCategory,
    ErrorClassification,
    ErrorSeverity,
    classify_error,
    classify_error_full,
    get_error_severity,
    is_retryable,
)


class TestErrorCategory:
    """Test ErrorCategory enum."""

    def test_all_categories_exist(self) -> None:
        """Verify all expected categories are defined."""
        expected = [
            "aborted",
            "timeout",
            "circuit_open",
            "rate_limit",
            "server_overload",
            "auth_error",
            "auth_transient",
            "network_error",
            "tool_error",
            "validation_error",
            "capacity_error",
            "capacity",
            "memory_error",
            "context_overflow",
            "unknown",
        ]
        actual = [cat.value for cat in ErrorCategory]
        for exp in expected:
            assert exp in actual, f"Missing category: {exp}"


class TestErrorSeverity:
    """Test ErrorSeverity enum."""

    def test_severity_levels(self) -> None:
        """Verify severity levels exist."""
        assert ErrorSeverity.WARNING.value == "warning"
        assert ErrorSeverity.ERROR.value == "error"
        assert ErrorSeverity.CRITICAL.value == "critical"


class TestClassifyError:
    """Test classify_error function."""

    def test_cancelled_error(self) -> None:
        """Test cancelled error classification."""
        error = asyncio.CancelledError()
        assert classify_error(error) == ErrorCategory.ABORTED

    def test_timeout_error(self) -> None:
        """Test timeout error classification."""
        error = TimeoutError("Connection timed out")
        assert classify_error(error) == ErrorCategory.TIMEOUT

    def test_memory_error(self) -> None:
        """Test memory error classification."""
        error = MemoryError("Out of memory")
        assert classify_error(error) == ErrorCategory.MEMORY_ERROR

    def test_unknown_error(self) -> None:
        """Test unknown error classification."""
        error = RuntimeError("Something went wrong")
        assert classify_error(error) == ErrorCategory.UNKNOWN

    def test_message_pattern_timeout(self) -> None:
        """Test timeout detection from message."""
        error = Exception("Request timeout occurred")
        assert classify_error(error) == ErrorCategory.TIMEOUT

    def test_message_pattern_rate_limit(self) -> None:
        """Test rate limit detection from message."""
        error = Exception("Rate limit exceeded")
        assert classify_error(error) == ErrorCategory.RATE_LIMIT

    def test_message_pattern_overload(self) -> None:
        """Test overload detection from message."""
        error = Exception("Server overload detected")
        assert classify_error(error) == ErrorCategory.SERVER_OVERLOAD

    def test_message_pattern_capacity(self) -> None:
        """Test capacity detection from message."""
        error = Exception("No capacity available")
        assert classify_error(error) == ErrorCategory.CAPACITY

    def test_message_pattern_context_overflow(self) -> None:
        """Test context overflow detection from message."""
        error = Exception("Context overflow: maximum tokens exceeded")
        assert classify_error(error) == ErrorCategory.CONTEXT_OVERFLOW

    def test_message_pattern_memory(self) -> None:
        """Test memory detection from message."""
        error = Exception("Heap memory exhausted")
        assert classify_error(error) == ErrorCategory.MEMORY_ERROR

    def test_message_pattern_tool_error(self) -> None:
        """Test tool error detection from message."""
        error = Exception("Tool execution error")
        assert classify_error(error) == ErrorCategory.TOOL_ERROR


class TestClassifyByStatus:
    """Test HTTP status code classification."""

    def test_status_429(self) -> None:
        """Test rate limit status."""
        error = Exception("Too many requests")
        error.status = 429  # type: ignore[attr-defined]
        assert classify_error(error) == ErrorCategory.RATE_LIMIT

    def test_status_529(self) -> None:
        """Test server overload status."""
        error = Exception("Server overloaded")
        error.status = 529  # type: ignore[attr-defined]
        assert classify_error(error) == ErrorCategory.SERVER_OVERLOAD

    def test_status_401(self) -> None:
        """Test auth error status."""
        error = Exception("Unauthorized")
        error.status = 401  # type: ignore[attr-defined]
        assert classify_error(error) == ErrorCategory.AUTH_ERROR

    def test_status_403(self) -> None:
        """Test forbidden status."""
        error = Exception("Forbidden")
        error.status = 403  # type: ignore[attr-defined]
        assert classify_error(error) == ErrorCategory.AUTH_ERROR

    def test_status_500(self) -> None:
        """Test server error status."""
        error = Exception("Internal server error")
        error.status = 500  # type: ignore[attr-defined]
        assert classify_error(error) == ErrorCategory.SERVER_OVERLOAD

    def test_status_408(self) -> None:
        """Test timeout status."""
        error = Exception("Request timeout")
        error.status = 408  # type: ignore[attr-defined]
        assert classify_error(error) == ErrorCategory.TIMEOUT

    def test_status_413(self) -> None:
        """Test payload too large status."""
        error = Exception("Payload too large")
        error.status = 413  # type: ignore[attr-defined]
        assert classify_error(error) == ErrorCategory.CONTEXT_OVERFLOW


class TestClassifyErrorFull:
    """Test classify_error_full function."""

    def test_returns_classification(self) -> None:
        """Test full classification returns ErrorClassification."""
        error = TimeoutError("Timeout")
        result = classify_error_full(error)
        assert isinstance(result, ErrorClassification)
        assert result.category == ErrorCategory.TIMEOUT
        assert result.severity == ErrorSeverity.WARNING
        assert result.retryable is True

    def test_capacity_fallback_available(self) -> None:
        """Test capacity error has fallback available."""
        error = Exception("Server capacity exceeded")
        result = classify_error_full(error)
        assert result.fallback_available is True

    def test_critical_severity_circuit_open(self) -> None:
        """Test circuit open is critical severity."""
        from mindflow_backend.infra.resilience.circuit_breaker.core import CircuitOpenError

        error = CircuitOpenError("Circuit is open")
        result = classify_error_full(error)
        assert result.severity == ErrorSeverity.CRITICAL

    def test_to_dict(self) -> None:
        """Test serialization to dict."""
        error = TimeoutError("Timeout")
        result = classify_error_full(error)
        d = result.to_dict()
        assert d["category"] == "timeout"
        assert d["severity"] == "warning"
        assert d["retryable"] is True


class TestIsRetryable:
    """Test is_retryable function."""

    def test_timeout_is_retryable(self) -> None:
        """Test timeout errors are retryable."""
        error = TimeoutError("Timeout")
        assert is_retryable(error) is True

    def test_rate_limit_is_retryable(self) -> None:
        """Test rate limit errors are retryable."""
        error = Exception("Rate limit exceeded")
        assert is_retryable(error) is True

    def test_server_overload_is_retryable(self) -> None:
        """Test server overload errors are retryable."""
        error = Exception("Server overloaded")
        assert is_retryable(error) is True

    def test_capacity_is_retryable(self) -> None:
        """Test capacity errors are retryable."""
        error = Exception("No capacity")
        assert is_retryable(error) is True

    def test_auth_transient_is_retryable(self) -> None:
        """Test transient auth errors are retryable."""
        error = Exception("Temporary auth failure")
        error.status = 401  # type: ignore[attr-defined]
        assert is_retryable(error) is True

    def test_unknown_is_not_retryable(self) -> None:
        """Test unknown errors are not retryable."""
        error = RuntimeError("Unknown")
        assert is_retryable(error) is False


class TestGetErrorSeverity:
    """Test get_error_severity function."""

    def test_timeout_severity(self) -> None:
        """Test timeout severity is warning."""
        error = TimeoutError("Timeout")
        assert get_error_severity(error) == ErrorSeverity.WARNING

    def test_circuit_open_severity(self) -> None:
        """Test circuit open severity is critical."""
        from mindflow_backend.infra.resilience.circuit_breaker.core import CircuitOpenError

        error = CircuitOpenError("Circuit is open")
        assert get_error_severity(error) == ErrorSeverity.CRITICAL

    def test_memory_error_severity(self) -> None:
        """Test memory error severity is critical."""
        error = MemoryError("Out of memory")
        assert get_error_severity(error) == ErrorSeverity.CRITICAL