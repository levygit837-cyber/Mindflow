"""Enhanced circuit breaker with adaptive thresholds.

Consolidated from grpc/resilience/enhanced_circuit_breaker.py
with dynamic configuration and advanced metrics.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from mindflow_backend.infra.logging import get_logger

from .core import CircuitBreakerConfig, CircuitOpenError, CircuitState
from .metrics import CircuitBreakerMetrics

_logger = get_logger(__name__)


class AdaptiveThresholdType(Enum):
    """Types of adaptive threshold strategies."""
    FIXED = "fixed"
    PERCENTILE_BASED = "percentile_based"
    RATE_BASED = "rate_based"
    PERFORMANCE_BASED = "performance_based"


@dataclass
class EnhancedCircuitBreakerConfig(CircuitBreakerConfig):
    """Enhanced configuration with adaptive thresholds."""

    adaptive_threshold_type: AdaptiveThresholdType = AdaptiveThresholdType.FIXED
    min_failure_threshold: int = 3
    max_failure_threshold: int = 20
    adaptive_window_size: int = 100

    performance_threshold_ms: float = 1000.0
    performance_window_size: int = 50

    failure_rate_threshold: float = 0.5
    rate_window_size: int = 100

    enable_dynamic_config: bool = True
    config_update_interval_seconds: float = 60.0
    auto_tune_thresholds: bool = True

    enable_detailed_metrics: bool = True
    metrics_retention_count: int = 10000

    enable_event_callbacks: bool = True
    state_change_callbacks: list[Callable] = field(default_factory=list)


class EnhancedCircuitBreaker:
    """Enhanced circuit breaker with adaptive thresholds and advanced metrics.

    Extends the base CircuitBreaker with:
    - Adaptive failure thresholds based on performance/rate
    - Comprehensive metrics tracking
    - Dynamic configuration updates
    - Event callbacks for state changes
    """

    def __init__(
        self,
        name: str,
        config: EnhancedCircuitBreakerConfig | None = None,
    ):
        self.name = name
        self.config = config or EnhancedCircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float | None = None
        self._last_success_time: float | None = None
        self._half_open_calls = 0
        self._metrics = CircuitBreakerMetrics()
        self._call_history: list[int] = []
        self._running = False
        self._background_tasks: list[asyncio.Task] = []

        _logger.info(
            "enhanced_circuit_breaker_created",
            name=name,
            adaptive_type=self.config.adaptive_threshold_type.value,
        )

    @property
    def state(self) -> CircuitState:
        """Get current state with auto-transition."""
        if self._state == CircuitState.OPEN and self._last_failure_time:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self.config.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
                self._half_open_calls = 0
        return self._state

    def can_execute(self) -> bool:
        """Check if call should be attempted."""
        state = self.state
        if state == CircuitState.CLOSED:
            return True
        if state == CircuitState.OPEN:
            return False
        return self._half_open_calls < self.config.max_half_open_calls

    async def call(self, operation: Callable, *args: Any, **kwargs: Any) -> Any:
        """Execute operation with enhanced circuit breaker protection."""
        if not self.can_execute():
            self._record_call_attempt(False, 0.0)
            raise CircuitOpenError(f"Enhanced circuit breaker '{self.name}' is OPEN")

        start_time = time.monotonic()
        try:
            result = await asyncio.wait_for(
                operation(*args, **kwargs),
                timeout=self.config.timeout,
            )
            duration = time.monotonic() - start_time
            self._record_success(duration)
            return result
        except TimeoutError as exc:
            duration = time.monotonic() - start_time
            self._record_failure(duration, exc)
            raise
        except Exception as exc:
            duration = time.monotonic() - start_time
            self._record_failure(duration, exc)
            raise

    def _record_success(self, duration: float) -> None:
        """Record successful operation with metrics."""
        self._metrics.total_calls += 1
        self._metrics.successful_calls += 1
        self._metrics.response_times.append(duration)
        self._call_history.append(1)
        self._last_success_time = time.monotonic()

        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            self._half_open_calls += 1
            if self._success_count >= self.config.success_threshold:
                self._transition_to_closed()
        elif self._state == CircuitState.CLOSED:
            self._failure_count = 0

        if self.config.auto_tune_thresholds:
            self._check_adaptive_thresholds()

        _logger.debug(
            "enhanced_circuit_success",
            name=self.name,
            state=self._state.value,
            duration=duration,
        )

    def _record_failure(self, duration: float, error: Exception) -> None:
        """Record failed operation with metrics."""
        error_type = type(error).__name__
        self._metrics.total_calls += 1
        self._metrics.failed_calls += 1
        self._metrics.response_times.append(-duration)
        self._call_history.append(0)
        self._metrics.failure_reasons[error_type] = (
            self._metrics.failure_reasons.get(error_type, 0) + 1
        )
        self._last_failure_time = time.monotonic()

        if self._state == CircuitState.CLOSED:
            self._failure_count += 1
            threshold = self._get_adaptive_threshold()
            if self._failure_count >= threshold:
                self._transition_to_open()
        elif self._state == CircuitState.HALF_OPEN:
            self._transition_to_open()

        if self.config.auto_tune_thresholds:
            self._check_adaptive_thresholds()

        _logger.warning(
            "enhanced_circuit_failure",
            name=self.name,
            state=self._state.value,
            duration=duration,
            error_type=error_type,
        )

    def _get_adaptive_threshold(self) -> int:
        """Get adaptive failure threshold based on strategy."""
        if self.config.adaptive_threshold_type == AdaptiveThresholdType.FIXED:
            return self.config.failure_threshold
        if self.config.adaptive_threshold_type == AdaptiveThresholdType.RATE_BASED:
            return self._calculate_rate_threshold()
        if self.config.adaptive_threshold_type == AdaptiveThresholdType.PERCENTILE_BASED:
            return self._calculate_percentile_threshold()
        if self.config.adaptive_threshold_type == AdaptiveThresholdType.PERFORMANCE_BASED:
            return self._calculate_performance_threshold()
        return self.config.failure_threshold

    def _calculate_percentile_threshold(self) -> int:
        """Calculate threshold based on failure rate percentile."""
        if len(self._call_history) < self.config.adaptive_window_size:
            return self.config.failure_threshold
        recent = self._call_history[-self.config.adaptive_window_size :]
        failure_rate = 1.0 - (sum(recent) / len(recent))
        if failure_rate > 0.8:
            return min(self.config.max_failure_threshold, self.config.failure_threshold * 2)
        if failure_rate > 0.5:
            return self.config.failure_threshold
        return max(self.config.min_failure_threshold, self.config.failure_threshold // 2)

    def _calculate_rate_threshold(self) -> int:
        """Calculate threshold based on failure rate."""
        rate = self._metrics.calculate_failure_rate(self.config.rate_window_size) / 100
        if rate > self.config.failure_rate_threshold:
            return min(self.config.max_failure_threshold, self.config.failure_threshold * 2)
        if rate > self.config.failure_rate_threshold / 2:
            return self.config.failure_threshold
        return max(self.config.min_failure_threshold, self.config.failure_threshold // 2)

    def _calculate_performance_threshold(self) -> int:
        """Calculate threshold based on performance metrics."""
        avg = self._metrics.calculate_average_response_time(
            self.config.performance_window_size
        )
        if avg > self.config.performance_threshold_ms / 1000:
            return max(self.config.min_failure_threshold, self.config.failure_threshold // 2)
        return min(self.config.max_failure_threshold, self.config.failure_threshold * 2)

    def _check_adaptive_thresholds(self) -> None:
        """Check and update adaptive thresholds."""
        new_threshold = self._get_adaptive_threshold()
        if new_threshold != self._metrics.current_threshold:
            old = self._metrics.current_threshold
            self._metrics.current_threshold = new_threshold
            self._metrics.threshold_history.append(new_threshold)
            _logger.info(
                "adaptive_threshold_updated",
                name=self.name,
                old_threshold=old,
                new_threshold=new_threshold,
            )

    def _transition_to_open(self) -> None:
        """Transition to OPEN state."""
        self._state = CircuitState.OPEN
        self._last_failure_time = time.monotonic()
        self._metrics.state_transitions.append({
            "from": self._state.value,
            "to": CircuitState.OPEN.value,
            "timestamp": time.monotonic(),
        })
        _logger.warning("enhanced_circuit_opened", name=self.name)

    def _transition_to_half_open(self) -> None:
        """Transition to HALF_OPEN state."""
        self._state = CircuitState.HALF_OPEN
        self._success_count = 0
        self._half_open_calls = 0
        _logger.info("enhanced_circuit_half_open", name=self.name)

    def _transition_to_closed(self) -> None:
        """Transition to CLOSED state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        _logger.info("enhanced_circuit_closed", name=self.name)

    def _record_call_attempt(self, success: bool, duration: float) -> None:
        """Record call attempt for statistics."""
        self._metrics.total_calls += 1
        if success:
            self._metrics.successful_calls += 1
        else:
            self._metrics.failed_calls += 1

    def get_enhanced_metrics(self) -> dict[str, Any]:
        """Get comprehensive metrics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "current_threshold": self._metrics.current_threshold,
            "total_calls": self._metrics.total_calls,
            "successful_calls": self._metrics.successful_calls,
            "failed_calls": self._metrics.failed_calls,
            "success_rate": self._metrics.calculate_success_rate(),
            "failure_rate": self._metrics.calculate_failure_rate(),
            "average_response_time": self._metrics.calculate_average_response_time(),
            "p95_response_time": self._metrics.get_percentile_response_time(95),
            "p99_response_time": self._metrics.get_percentile_response_time(99),
            "failure_reasons": dict(self._metrics.failure_reasons),
            "adaptive_type": self.config.adaptive_threshold_type.value,
        }

    def reset(self) -> None:
        """Reset to initial state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._metrics = CircuitBreakerMetrics()
        self._call_history = []
        _logger.info("enhanced_circuit_reset", name=self.name)