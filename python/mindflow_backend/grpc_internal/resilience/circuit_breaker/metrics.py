"""Enhanced circuit breaker metrics.

Provides comprehensive metrics tracking for circuit breaker
performance monitoring and adaptive threshold tuning.
"""

from __future__ import annotations

import statistics
from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CircuitBreakerMetrics:
    """Enhanced metrics for circuit breaker.

    Tracks call statistics, response times, failure reasons,
    state transitions, and adaptive threshold history.
    """

    # Basic metrics
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    timeout_calls: int = 0

    # Performance metrics
    response_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    failure_reasons: dict[str, int] = field(default_factory=dict)

    # State metrics
    state_durations: dict[str, float] = field(default_factory=dict)
    state_transitions: list[dict[str, Any]] = field(default_factory=list)
    last_state_change: float = 0.0

    # Adaptive metrics
    current_threshold: int = 5
    threshold_history: deque = field(default_factory=lambda: deque(maxlen=100))
    performance_trend: deque = field(default_factory=lambda: deque(maxlen=100))

    def calculate_success_rate(self, window_size: int | None = None) -> float:
        """Calculate success rate with optional window.

        Args:
            window_size: Number of recent calls to consider

        Returns:
            Success rate as percentage (0-100)
        """
        if self.total_calls == 0:
            return 0.0

        if window_size and len(self.response_times) >= window_size:
            recent_times = list(self.response_times)[-window_size:]
            recent_success = len([t for t in recent_times if t > 0])  # Positive = success
            return (recent_success / len(recent_times)) * 100

        return (self.successful_calls / self.total_calls) * 100

    def calculate_failure_rate(self, window_size: int | None = None) -> float:
        """Calculate failure rate with optional window.

        Args:
            window_size: Number of recent calls to consider

        Returns:
            Failure rate as percentage (0-100)
        """
        if self.total_calls == 0:
            return 0.0

        return 100.0 - self.calculate_success_rate(window_size)

    def calculate_average_response_time(self, window_size: int | None = None) -> float:
        """Calculate average response time with optional window.

        Args:
            window_size: Number of recent calls to consider

        Returns:
            Average response time in seconds
        """
        if not self.response_times:
            return 0.0

        if window_size and len(self.response_times) >= window_size:
            recent_times = list(self.response_times)[-window_size:]
            return statistics.mean([abs(t) for t in recent_times if t != 0])

        return statistics.mean([abs(t) for t in self.response_times if t != 0])

    def get_percentile_response_time(self, percentile: float, window_size: int | None = None) -> float:
        """Get percentile response time.

        Args:
            percentile: Percentile value (0-100)
            window_size: Number of recent calls to consider

        Returns:
            Response time at the specified percentile
        """
        if not self.response_times:
            return 0.0

        if window_size and len(self.response_times) >= window_size:
            recent_times = list(self.response_times)[-window_size:]
        else:
            recent_times = list(self.response_times)

        positive_times = [abs(t) for t in recent_times if t != 0]
        if not positive_times:
            return 0.0

        sorted_times = sorted(positive_times)
        index = int((percentile / 100) * len(sorted_times))
        if index >= len(sorted_times):
            index = len(sorted_times) - 1

        return sorted_times[index]