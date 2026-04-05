"""Orchestration Fallback Metrics - Collects metrics for orchestration component fallbacks.

This module provides metrics collection specifically for orchestration components,
including fallback rate, latency, and success metrics per component.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


@dataclass
class OrchestrationFallbackMetrics:
    """Metrics for a specific orchestration component."""
    component: str
    fallback_total: int = 0
    fallback_success: int = 0
    fallback_failure: int = 0
    latency_samples: deque = field(default_factory=lambda: deque(maxlen=1000))
    last_fallback_time: float | None = None
    last_fallback_error: str | None = None

    @property
    def fallback_success_rate(self) -> float:
        """Calculate fallback success rate."""
        if self.fallback_total == 0:
            return 1.0
        return self.fallback_success / max(1, self.fallback_total)

    @property
    def avg_latency(self) -> float:
        """Calculate average fallback latency."""
        if not self.latency_samples:
            return 0.0
        return sum(self.latency_samples) / len(self.latency_samples)

    @property
    def p50_latency(self) -> float:
        """Calculate 50th percentile latency."""
        if not self.latency_samples:
            return 0.0
        sorted_samples = sorted(self.latency_samples)
        idx = int(len(sorted_samples) * 0.5)
        return sorted_samples[idx]

    @property
    def p95_latency(self) -> float:
        """Calculate 95th percentile latency."""
        if not self.latency_samples:
            return 0.0
        sorted_samples = sorted(self.latency_samples)
        idx = int(len(sorted_samples) * 0.95)
        return sorted_samples[idx]

    @property
    def p99_latency(self) -> float:
        """Calculate 99th percentile latency."""
        if not self.latency_samples:
            return 0.0
        sorted_samples = sorted(self.latency_samples)
        idx = int(len(sorted_samples) * 0.99)
        return sorted_samples[idx]


class OrchestrationFallbackMetricsCollector:
    """Collects and aggregates orchestration component fallback metrics.

    Tracks fallback rate, latency, and success metrics per orchestration component.
    Provides alerts when fallback rate exceeds threshold.
    """

    def __init__(
        self,
        window_seconds: int = 3600,
        alert_threshold: float = 0.2,
    ):
        self.window_seconds = window_seconds
        self.alert_threshold = alert_threshold
        self._lock: threading.RLock = threading.RLock()

        # Metrics per component
        self._metrics: dict[str, OrchestrationFallbackMetrics] = defaultdict(
            lambda: OrchestrationFallbackMetrics(component="")
        )

        # Time-windowed fallback counts for rate calculation
        self._fallback_events: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=10000)
        )

    def record_fallback(
        self,
        component: str,
        success: bool,
        fallback_used: bool,
        latency: float,
    ) -> None:
        """Record a fallback event.

        Args:
            component: Component identifier
            success: Whether the fallback was successful
            fallback_used: Whether fallback was triggered
            latency: Execution latency in seconds
        """
        with self._lock:
            metrics = self._metrics[component]
            metrics.component = component

            if fallback_used:
                metrics.fallback_total += 1
                metrics.last_fallback_time = time.time()

                if success:
                    metrics.fallback_success += 1
                else:
                    metrics.fallback_failure += 1
                    metrics.last_fallback_error = "Fallback execution failed"

                metrics.latency_samples.append(latency)

                # Record event with timestamp for rate calculation
                self._fallback_events[component].append(
                    (time.time(), success, fallback_used)
                )

                # Check if fallback rate is high
                rate = self._calculate_fallback_rate(component)
                if rate > self.alert_threshold:
                    _logger.warning(
                        "orchestration_high_fallback_rate",
                        component=component,
                        fallback_rate=rate,
                        threshold=self.alert_threshold,
                    )

    def _calculate_fallback_rate(self, component: str) -> float:
        """Calculate fallback rate in the configured time window.

        Args:
            component: Component identifier

        Returns:
            Fallback rate (0.0 to 1.0)
        """
        events = self._fallback_events.get(component)
        if not events:
            return 0.0

        now = time.time()
        window_start = now - self.window_seconds

        # Count fallback events in window
        fallback_count = sum(
            1 for timestamp, _, used in events
            if timestamp >= window_start and used
        )

        # Count total events in window
        total_count = sum(
            1 for timestamp, _, _ in events
            if timestamp >= window_start
        )

        if total_count == 0:
            return 0.0

        return fallback_count / total_count

    def get_metrics(self, component: str) -> OrchestrationFallbackMetrics:
        """Get metrics for a specific component.

        Args:
            component: Component identifier

        Returns:
            OrchestrationFallbackMetrics dataclass
        """
        with self._lock:
            metrics = self._metrics.get(component)
            if not metrics:
                return OrchestrationFallbackMetrics(component=component)

            # Calculate current fallback rate
            rate = self._calculate_fallback_rate(component)

            # Return a copy to avoid mutation
            return OrchestrationFallbackMetrics(
                component=metrics.component,
                fallback_total=metrics.fallback_total,
                fallback_success=metrics.fallback_success,
                fallback_failure=metrics.fallback_failure,
                latency_samples=deque(metrics.latency_samples),
                last_fallback_time=metrics.last_fallback_time,
                last_fallback_error=metrics.last_fallback_error,
            )

    def get_all_metrics(self) -> dict[str, OrchestrationFallbackMetrics]:
        """Get metrics for all components.

        Returns:
            Dictionary mapping component names to OrchestrationFallbackMetrics
        """
        with self._lock:
            return {
                component: self.get_metrics(component)
                for component in self._metrics.keys()
            }

    def is_fallback_rate_high(
        self,
        component: str,
        threshold: float | None = None,
    ) -> bool:
        """Check if fallback rate exceeds threshold.

        Args:
            component: Component identifier
            threshold: Custom threshold (uses default if None)

        Returns:
            True if fallback rate is high
        """
        threshold = threshold or self.alert_threshold
        rate = self._calculate_fallback_rate(component)
        return rate > threshold

    def get_overall_fallback_rate(self) -> float:
        """Calculate overall fallback rate across all components.

        Returns:
            Overall fallback rate (0.0 to 1.0)
        """
        with self._lock:
            total_fallbacks = 0
            total_events = 0

            now = time.time()
            window_start = now - self.window_seconds

            for component, events in self._fallback_events.items():
                for timestamp, _, used in events:
                    if timestamp >= window_start:
                        total_events += 1
                        if used:
                            total_fallbacks += 1

            if total_events == 0:
                return 0.0

            return total_fallbacks / total_events

    def get_alerting_components(self) -> list[str]:
        """Get list of components with high fallback rate.

        Returns:
            List of component identifiers exceeding alert threshold
        """
        with self._lock:
            return [
                component
                for component in self._metrics.keys()
                if self.is_fallback_rate_high(component)
            ]

    def reset_metrics(self, component: str | None = None) -> None:
        """Reset metrics for a component or all components.

        Args:
            component: Specific component to reset (None = reset all)
        """
        with self._lock:
            if component is None:
                self._metrics.clear()
                self._fallback_events.clear()
                _logger.info("orchestration_all_metrics_reset")
            else:
                if component in self._metrics:
                    del self._metrics[component]
                if component in self._fallback_events:
                    del self._fallback_events[component]
                _logger.info("orchestration_metrics_reset", component=component)


# Global instance
_orchestration_fallback_metrics_collector: OrchestrationFallbackMetricsCollector | None = None


def get_orchestration_fallback_metrics_collector(
    window_seconds: int = 3600,
    alert_threshold: float = 0.2,
) -> OrchestrationFallbackMetricsCollector:
    """Get or create the global orchestration fallback metrics collector instance."""
    global _orchestration_fallback_metrics_collector
    if _orchestration_fallback_metrics_collector is None:
        _orchestration_fallback_metrics_collector = OrchestrationFallbackMetricsCollector(
            window_seconds=window_seconds,
            alert_threshold=alert_threshold,
        )
        _logger.info(
            "orchestration_fallback_metrics_collector_initialized",
            window_seconds=window_seconds,
            alert_threshold=alert_threshold,
        )
    return _orchestration_fallback_metrics_collector
