"""Circuit breaker metrics.

Consolidated from grpc/resilience/circuit_breaker/metrics.py
with enhanced tracking capabilities.
"""

from __future__ import annotations

import statistics
from collections import deque
from dataclasses import dataclass, field
from typing import Any


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