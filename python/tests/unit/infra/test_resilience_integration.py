"""Integration tests for resilience patterns.

Tests the integration between error classifier, retry with fallback,
circuit breakers, and remote configuration.
"""

from __future__ import annotations

import asyncio
import time

import pytest

from mindflow_backend.exceptions.base.core_new import RetryableError
from mindflow_backend.infra.error_handling.classifier import (
    ErrorCategory,
    ErrorSeverity,
    classify_error,
    classify_error_full,
    is_retryable,
)
from mindflow_backend.infra.resilience.circuit_breaker.core import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitOpenError,
    CircuitState,
)
from mindflow_backend.infra.resilience.remote_config import (
    CircuitBreakerRemoteConfig,
    FeatureFlagProvider,
    RemoteCircuitBreakerConfig,
)
from mindflow_backend.infra.resilience.retry_fallback import (
    RetryFallbackConfig,
    RetryFallbackError,
    calculate_backoff_delay,
    with_retry_and_fallback,
)


class TestRetryableError:
    """Test RetryableError exception."""

    def test_basic_creation(self) -> None:
        """Test basic RetryableError creation."""
        error = RetryableError("Test error")
        assert str(error) == "[{}] Test error".format(error.error_id)
        assert error.retry_count == 0
        assert error.max_retries == 3
        assert error.can_retry is True
        assert error.attempts_remaining == 3

    def test_with_retry_context(self) -> None:
        """Test RetryableError with retry context."""
        error = RetryableError(
            "Test error",
            retry_count=2,
            max_retries=5,
            next_retry_delay=2.0,
            fallback_available=True,
        )
        assert error.retry_count == 2
        assert error.max_retries == 5
        assert error.next_retry_delay == 2.0
        assert error.fallback_available is True
        assert error.can_retry is True
        assert error.attempts_remaining == 3

    def test_no_more_retries(self) -> None:
        """Test RetryableError when no retries remain."""
        error = RetryableError(
            "Test error",
            retry_count=3,
            max_retries=3,
        )
        assert error.can_retry is False
        assert error.attempts_remaining == 0

    def test_to_dict(self) -> None:
        """Test RetryableError serialization."""
        error = RetryableError(
            "Test error",
            retry_count=1,
            max_retries=3,
            next_retry_delay=1.5,
            fallback_available=True,
        )
        data = error.to_dict()
        assert data["retry_count"] == 1
        assert data["max_retries"] == 3
        assert data["next_retry_delay"] == 1.5
        assert data["fallback_available"] is True
        assert data["can_retry"] is True
        assert data["attempts_remaining"] == 2


class TestRetryFallbackConfig:
    """Test RetryFallbackConfig."""

    def test_default_config(self) -> None:
        """Test default configuration."""
        config = RetryFallbackConfig()
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 30.0
        assert config.jitter is True
        assert config.fallback_enabled is True

    def test_retry_categories(self) -> None:
        """Test retry categories."""
        config = RetryFallbackConfig()
        assert ErrorCategory.TIMEOUT in config.retry_on_categories
        assert ErrorCategory.RATE_LIMIT in config.retry_on_categories
        assert ErrorCategory.NETWORK_ERROR in config.retry_on_categories

    def test_fallback_categories(self) -> None:
        """Test fallback categories."""
        config = RetryFallbackConfig()
        assert ErrorCategory.CAPACITY in config.fallback_on_categories
        assert ErrorCategory.SERVER_OVERLOAD in config.fallback_on_categories
        assert ErrorCategory.CIRCUIT_OPEN in config.fallback_on_categories


class TestCalculateBackoffDelay:
    """Test calculate_backoff_delay function."""

    def test_exponential_backoff(self) -> None:
        """Test exponential backoff calculation."""
        delay0 = calculate_backoff_delay(0, base_delay=1.0, jitter=False)
        delay1 = calculate_backoff_delay(1, base_delay=1.0, jitter=False)
        delay2 = calculate_backoff_delay(2, base_delay=1.0, jitter=False)

        assert delay0 == 1.0
        assert delay1 == 2.0
        assert delay2 == 4.0

    def test_max_delay_cap(self) -> None:
        """Test max delay capping."""
        delay = calculate_backoff_delay(
            10, base_delay=1.0, max_delay=5.0, jitter=False
        )
        assert delay == 5.0

    def test_jitter(self) -> None:
        """Test jitter adds randomness."""
        delays = [
            calculate_backoff_delay(1, base_delay=1.0, jitter=True)
            for _ in range(10)
        ]
        # With jitter, delays should vary
        assert len(set(delays)) > 1


class TestRemoteCircuitBreakerConfig:
    """Test RemoteCircuitBreakerConfig."""

    def test_default_config(self) -> None:
        """Test default remote config."""
        config = RemoteCircuitBreakerConfig(
            provider=FeatureFlagProvider.LOCAL
        )
        assert config.provider == FeatureFlagProvider.LOCAL
        assert config.refresh_interval == 60.0

    def test_get_config(self) -> None:
        """Test getting config for a service."""
        manager = RemoteCircuitBreakerConfig()
        config = manager.get_config("test_service")
        assert isinstance(config, CircuitBreakerRemoteConfig)
        assert config.service_name == "test_service"
        assert config.enabled is True

    def test_update_config(self) -> None:
        """Test updating config."""
        manager = RemoteCircuitBreakerConfig()
        manager.update_config(
            "test_service",
            {"failure_threshold": 10, "recovery_timeout": 120.0},
        )
        config = manager.get_config("test_service")
        assert config.failure_threshold == 10
        assert config.recovery_timeout == 120.0

    def test_callback_notification(self) -> None:
        """Test callback notification on config change."""
        manager = RemoteCircuitBreakerConfig()
        notifications: list[CircuitBreakerRemoteConfig] = []

        def callback(config: CircuitBreakerRemoteConfig) -> None:
            notifications.append(config)

        manager.register_callback("test_service", callback)
        manager.update_config("test_service", {"failure_threshold": 8})

        assert len(notifications) == 1
        assert notifications[0].failure_threshold == 8


class TestCircuitBreakerIntegration:
    """Test circuit breaker integration with error classifier."""

    def test_circuit_open_error_classifies_correctly(self) -> None:
        """Test CircuitOpenError classification."""
        error = CircuitOpenError("Circuit is open")
        category = classify_error(error)
        assert category == ErrorCategory.CIRCUIT_OPEN

    def test_circuit_open_is_not_retryable(self) -> None:
        """Test CircuitOpenError is not retryable."""
        error = CircuitOpenError("Circuit is open")
        assert is_retryable(error) is False

    def test_circuit_open_severity_is_critical(self) -> None:
        """Test CircuitOpenError severity."""
        error = CircuitOpenError("Circuit is open")
        classification = classify_error_full(error)
        assert classification.severity == ErrorSeverity.CRITICAL


class TestErrorClassifierIntegration:
    """Test error classifier integration."""

    def test_timeout_classifies_as_retryable(self) -> None:
        """Test timeout errors are retryable."""
        error = TimeoutError("Connection timed out")
        assert is_retryable(error) is True
        assert classify_error(error) == ErrorCategory.TIMEOUT

    def test_rate_limit_classifies_as_retryable(self) -> None:
        """Test rate limit errors are retryable."""
        error = Exception("Rate limit exceeded")
        error.status = 429  # type: ignore[attr-defined]
        assert is_retryable(error) is True
        assert classify_error(error) == ErrorCategory.RATE_LIMIT

    def test_capacity_classifies_with_fallback(self) -> None:
        """Test capacity errors have fallback available."""
        error = Exception("Server capacity exceeded")
        classification = classify_error_full(error)
        assert classification.category == ErrorCategory.CAPACITY
        assert classification.fallback_available is True
        assert classification.retryable is True

    def test_memory_error_is_critical(self) -> None:
        """Test memory errors are critical."""
        error = MemoryError("Out of memory")
        classification = classify_error_full(error)
        assert classification.category == ErrorCategory.MEMORY_ERROR
        assert classification.severity == ErrorSeverity.CRITICAL