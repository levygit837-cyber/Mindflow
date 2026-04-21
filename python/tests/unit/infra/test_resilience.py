"""Tests for resilience patterns.

Tests circuit breaker, retry with fallback, and adaptive thresholds.
"""

from __future__ import annotations

import asyncio
import time

import pytest

from mindflow_backend.infra.resilience.circuit_breaker.core import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitOpenError,
    CircuitState,
)
from mindflow_backend.infra.resilience.circuit_breaker.enhanced import (
    AdaptiveThresholdType,
    EnhancedCircuitBreaker,
    EnhancedCircuitBreakerConfig,
)
from mindflow_backend.infra.resilience.circuit_breaker.metrics import (
    CircuitBreakerMetrics,
    PerformanceMetrics,
)


class TestCircuitBreaker:
    """Test base CircuitBreaker."""

    def test_initial_state_is_closed(self) -> None:
        """Test circuit breaker starts in CLOSED state."""
        cb = CircuitBreaker("test")
        assert cb.state == CircuitState.CLOSED

    def test_can_execute_when_closed(self) -> None:
        """Test can execute when CLOSED."""
        cb = CircuitBreaker("test")
        assert cb.can_execute() is True

    def test_record_success(self) -> None:
        """Test recording success."""
        cb = CircuitBreaker("test")
        cb.record_success()
        assert cb.stats.successful_requests == 1
        assert cb.stats.consecutive_successes == 1

    def test_record_failure(self) -> None:
        """Test recording failure."""
        cb = CircuitBreaker("test")
        cb.record_failure()
        assert cb.stats.failed_requests == 1
        assert cb.stats.consecutive_failures == 1

    def test_opens_after_threshold_failures(self) -> None:
        """Test circuit opens after threshold failures."""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker("test", config)

        for _ in range(3):
            cb.record_failure()

        assert cb.state == CircuitState.OPEN
        assert cb.can_execute() is False

    def test_transitions_to_half_open_after_timeout(self) -> None:
        """Test transitions to HALF_OPEN after recovery timeout."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=0.1,
        )
        cb = CircuitBreaker("test", config)

        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

    def test_closes_after_success_threshold_in_half_open(self) -> None:
        """Test closes after success threshold in HALF_OPEN."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=0.1,
            success_threshold=2,
        )
        cb = CircuitBreaker("test", config)

        cb.record_failure()
        time.sleep(0.15)

        # Access state to trigger OPEN -> HALF_OPEN transition
        assert cb.state == CircuitState.HALF_OPEN

        cb.record_success()
        cb.record_success()
        assert cb.stats.consecutive_successes >= config.success_threshold
        assert cb.state == CircuitState.CLOSED

    def test_reset(self) -> None:
        """Test reset functionality."""
        config = CircuitBreakerConfig(failure_threshold=2)
        cb = CircuitBreaker("test", config)

        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.stats.total_requests == 0


class TestCircuitBreakerMetrics:
    """Test CircuitBreakerMetrics."""

    def test_initial_state(self) -> None:
        """Test initial metrics state."""
        metrics = CircuitBreakerMetrics()
        assert metrics.total_calls == 0
        assert metrics.successful_calls == 0
        assert metrics.failed_calls == 0

    def test_record_success(self) -> None:
        """Test recording success."""
        metrics = CircuitBreakerMetrics()
        metrics.record_call_success(0.1)
        assert metrics.total_calls == 1
        assert metrics.successful_calls == 1

    def test_record_failure(self) -> None:
        """Test recording failure."""
        metrics = CircuitBreakerMetrics()
        metrics.record_call_failure(0.1, "TimeoutError")
        assert metrics.total_calls == 1
        assert metrics.failed_calls == 1

    def test_calculate_success_rate(self) -> None:
        """Test success rate calculation."""
        metrics = CircuitBreakerMetrics()
        metrics.record_call_success(0.1)
        metrics.record_call_success(0.2)
        metrics.record_call_failure(0.1, "Error")

        rate = metrics.calculate_success_rate()
        assert rate == pytest.approx(66.67, rel=0.01)


class TestPerformanceMetrics:
    """Test PerformanceMetrics."""

    def test_initial_state(self) -> None:
        """Test initial state."""
        perf = PerformanceMetrics()
        assert len(perf.response_times) == 0
        assert len(perf.error_timestamps) == 0

    def test_record_response_time(self) -> None:
        """Test recording response time."""
        perf = PerformanceMetrics()
        perf.record_response_time(0.1)
        perf.record_response_time(0.2)
        assert len(perf.response_times) == 2

    def test_calculate_p95_latency(self) -> None:
        """Test P95 latency calculation."""
        perf = PerformanceMetrics()
        for i in range(100):
            perf.record_response_time(i * 0.01)

        p95 = perf.calculate_p95_latency()
        assert p95 > 0

    def test_calculate_p99_latency(self) -> None:
        """Test P99 latency calculation."""
        perf = PerformanceMetrics()
        for i in range(100):
            perf.record_response_time(i * 0.01)

        p99 = perf.calculate_p99_latency()
        assert p99 > 0

    def test_record_error(self) -> None:
        """Test recording error."""
        perf = PerformanceMetrics()
        perf.record_error("TimeoutError")
        perf.record_error("TimeoutError")
        perf.record_error("NetworkError")

        dist = perf.get_error_distribution()
        assert dist["TimeoutError"] == 2
        assert dist["NetworkError"] == 1


class TestEnhancedCircuitBreaker:
    """Test EnhancedCircuitBreaker."""

    def test_initial_state(self) -> None:
        """Test initial state."""
        ecb = EnhancedCircuitBreaker("test")
        assert ecb.state == CircuitState.CLOSED

    def test_adaptive_threshold_fixed(self) -> None:
        """Test fixed adaptive threshold."""
        config = EnhancedCircuitBreakerConfig(
            failure_threshold=5,
            adaptive_threshold_type=AdaptiveThresholdType.FIXED,
        )
        ecb = EnhancedCircuitBreaker("test", config)

        threshold = ecb._get_adaptive_threshold()
        assert threshold == 5

    def test_adaptive_threshold_rate_based(self) -> None:
        """Test rate-based adaptive threshold."""
        config = EnhancedCircuitBreakerConfig(
            failure_threshold=5,
            min_failure_threshold=3,
            max_failure_threshold=10,
            adaptive_threshold_type=AdaptiveThresholdType.RATE_BASED,
        )
        ecb = EnhancedCircuitBreaker("test", config)

        threshold = ecb._get_adaptive_threshold()
        assert threshold >= config.min_failure_threshold
        assert threshold <= config.max_failure_threshold

    def test_get_enhanced_metrics(self) -> None:
        """Test getting enhanced metrics."""
        ecb = EnhancedCircuitBreaker("test")
        metrics = ecb.get_enhanced_metrics()

        assert metrics["name"] == "test"
        assert metrics["state"] == "closed"
        assert "total_calls" in metrics
        assert "success_rate" in metrics
        assert "p95_response_time" in metrics

    def test_reset(self) -> None:
        """Test reset functionality."""
        ecb = EnhancedCircuitBreaker("test")
        ecb._failure_count = 5
        ecb._success_count = 3

        ecb.reset()
        assert ecb._failure_count == 0
        assert ecb._success_count == 0
        assert ecb.state == CircuitState.CLOSED


class TestCircuitBreakerConfig:
    """Test CircuitBreakerConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = CircuitBreakerConfig()
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 60.0
        assert config.success_threshold == 3
        assert config.timeout == 30.0

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = CircuitBreakerConfig(
            failure_threshold=10,
            recovery_timeout=120.0,
            success_threshold=5,
            timeout=60.0,
        )
        assert config.failure_threshold == 10
        assert config.recovery_timeout == 120.0
        assert config.success_threshold == 5
        assert config.timeout == 60.0


class TestEnhancedCircuitBreakerConfig:
    """Test EnhancedCircuitBreakerConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = EnhancedCircuitBreakerConfig()
        assert config.adaptive_threshold_type == AdaptiveThresholdType.FIXED
        assert config.min_failure_threshold == 3
        assert config.max_failure_threshold == 20
        assert config.auto_tune_thresholds is True

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = EnhancedCircuitBreakerConfig(
            adaptive_threshold_type=AdaptiveThresholdType.PERCENTILE_BASED,
            min_failure_threshold=5,
            max_failure_threshold=30,
            auto_tune_thresholds=False,
        )
        assert config.adaptive_threshold_type == AdaptiveThresholdType.PERCENTILE_BASED
        assert config.min_failure_threshold == 5
        assert config.max_failure_threshold == 30
        assert config.auto_tune_thresholds is False