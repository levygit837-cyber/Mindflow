"""Circuit breaker metrics.

Consolidated from grpc/resilience/circuit_breaker/metrics.py
with enhanced tracking capabilities including P95/P99 latency,
error rate windows, throughput, and error distribution.
"""

from __future__ import annotations

import statistics
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PerformanceMetrics:
    """Detailed performance metrics inspired by Claude Code.

    Tracks response times, error rates by window, throughput,
    and error distribution for comprehensive monitoring.
    """

    response_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    error_timestamps: deque = field(default_factory=lambda: deque(maxlen=100))
    throughput_windows: deque = field(default_factory=lambda: deque(maxlen=100))
    error_distribution: dict[str, int] = field(default_factory=dict)

    def calculate_p95_latency(self, window_size: int | None = None) -> float:
        """Calcula latência P95."""
        return self._calculate_percentile(95, window_size)

    def calculate_p99_latency(self, window_size: int | None = None) -> float:
        """Calcula latência P99."""
        return self._calculate_percentile(99, window_size)

    def _calculate_percentile(self, percentile: float, window_size: int | None = None) -> float:
        """Calcula percentil de latência."""
        if not self.response_times:
            return 0.0
        times = list(self.response_times)
        if window_size and len(times) >= window_size:
            times = times[-window_size:]
        positive = sorted(abs(t) for t in times if t != 0)
        if not positive:
            return 0.0
        idx = int((percentile / 100) * len(positive))
        return positive[min(idx, len(positive) - 1)]

    def calculate_error_rate(self, window_seconds: int = 60) -> float:
        """Calcula taxa de erros em janela de tempo."""
        if not self.error_timestamps:
            return 0.0
        cutoff = time.time() - window_seconds
        recent_errors = [t for t in self.error_timestamps if t > cutoff]
        return len(recent_errors) / max(window_seconds, 1)

    def calculate_throughput(self, window_seconds: int = 60) -> float:
        """Calcula throughput (ops/segundo) em janela de tempo."""
        if not self.throughput_windows:
            return 0.0
        cutoff = time.time() - window_seconds
        recent = [t for t in self.throughput_windows if t > cutoff]
        return len(recent) / max(window_seconds, 1)

    def record_response_time(self, duration: float) -> None:
        """Registra tempo de resposta."""
        self.response_times.append(duration)

    def record_error(self, error_type: str) -> None:
        """Registra erro com timestamp e tipo."""
        self.error_timestamps.append(time.time())
        self.error_distribution[error_type] = self.error_distribution.get(error_type, 0) + 1

    def record_throughput(self) -> None:
        """Registra operação para cálculo de throughput."""
        self.throughput_windows.append(time.time())

    def get_error_distribution(self) -> dict[str, int]:
        """Retorna distribuição de erros por tipo."""
        return dict(self.error_distribution)

    def reset(self) -> None:
        """Reseta todas as métricas."""
        self.response_times.clear()
        self.error_timestamps.clear()
        self.throughput_windows.clear()
        self.error_distribution.clear()


@dataclass
class CircuitBreakerMetrics:
    """Comprehensive metrics for circuit breaker monitoring.

    Tracks call statistics, response times, failure reasons,
    state transitions, and adaptive threshold history.
    """

    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    timeout_calls: int = 0

    response_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    failure_reasons: dict[str, int] = field(default_factory=dict)

    state_durations: dict[str, float] = field(default_factory=dict)
    state_transitions: list[dict[str, Any]] = field(default_factory=list)
    last_state_change: float = 0.0

    current_threshold: int = 5
    threshold_history: deque = field(default_factory=lambda: deque(maxlen=100))

    # Performance metrics (Phase 1 enhancement)
    performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)

    def calculate_success_rate(self, window_size: int | None = None) -> float:
        """Calculate success rate with optional window."""
        if self.total_calls == 0:
            return 0.0
        if window_size and len(self.response_times) >= window_size:
            recent = list(self.response_times)[-window_size:]
            successes = len([t for t in recent if t > 0])
            return (successes / len(recent)) * 100
        return (self.successful_calls / self.total_calls) * 100

    def calculate_failure_rate(self, window_size: int | None = None) -> float:
        """Calculate failure rate with optional window."""
        return 100.0 - self.calculate_success_rate(window_size)

    def calculate_average_response_time(
        self, window_size: int | None = None
    ) -> float:
        """Calculate average response time in seconds."""
        if not self.response_times:
            return 0.0
        times = list(self.response_times)
        if window_size and len(times) >= window_size:
            times = times[-window_size:]
        positive = [abs(t) for t in times if t != 0]
        return statistics.mean(positive) if positive else 0.0

    def get_percentile_response_time(
        self, percentile: float, window_size: int | None = None
    ) -> float:
        """Get response time at specified percentile."""
        if not self.response_times:
            return 0.0
        times = list(self.response_times)
        if window_size and len(times) >= window_size:
            times = times[-window_size:]
        positive = sorted(abs(t) for t in times if t != 0)
        if not positive:
            return 0.0
        idx = int((percentile / 100) * len(positive))
        return positive[min(idx, len(positive) - 1)]

    def get_p95_latency(self, window_size: int | None = None) -> float:
        """Get P95 latency using performance metrics."""
        return self.performance.calculate_p95_latency(window_size)

    def get_p99_latency(self, window_size: int | None = None) -> float:
        """Get P99 latency using performance metrics."""
        return self.performance.calculate_p99_latency(window_size)

    def get_error_rate_window(self, window_seconds: int = 60) -> float:
        """Get error rate in time window."""
        return self.performance.calculate_error_rate(window_seconds)

    def get_throughput(self, window_seconds: int = 60) -> float:
        """Get throughput (ops/sec) in time window."""
        return self.performance.calculate_throughput(window_seconds)

    def get_error_distribution(self) -> dict[str, int]:
        """Get error distribution by type."""
        return self.performance.get_error_distribution()

    def record_call_success(self, duration: float) -> None:
        """Record successful call with performance tracking."""
        self.total_calls += 1
        self.successful_calls += 1
        self.response_times.append(duration)
        self.performance.record_response_time(duration)
        self.performance.record_throughput()

    def record_call_failure(self, duration: float, error_type: str) -> None:
        """Record failed call with performance tracking."""
        self.total_calls += 1
        self.failed_calls += 1
        self.response_times.append(-duration)
        self.failure_reasons[error_type] = self.failure_reasons.get(error_type, 0) + 1
        self.performance.record_response_time(duration)
        self.performance.record_error(error_type)
        self.performance.record_throughput()
