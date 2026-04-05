"""Enhanced circuit breaker configuration.

Defines adaptive threshold types and enhanced configuration
for the circuit breaker with dynamic tuning capabilities.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker (base class)."""
    failure_threshold: int = 5          # Number of failures before opening
    recovery_timeout: float = 60.0      # Seconds to wait before trying again
    success_threshold: int = 3          # Successes needed to close circuit
    timeout: float = 30.0              # Timeout for individual calls
    max_half_open_calls: int = 10       # Max calls in half-open state
    monitor_period: float = 10.0        # Period to monitor health


class AdaptiveThresholdType(Enum):
    """Types of adaptive threshold strategies."""
    FIXED = "fixed"
    PERCENTILE_BASED = "percentile_based"
    RATE_BASED = "rate_based"
    PERFORMANCE_BASED = "performance_based"


@dataclass
class EnhancedCircuitBreakerConfig(CircuitBreakerConfig):
    """Enhanced configuration for circuit breaker.

    Extends the base CircuitBreakerConfig with adaptive thresholds,
    performance-based tuning, and dynamic configuration capabilities.
    """

    # Adaptive thresholds
    adaptive_threshold_type: AdaptiveThresholdType = AdaptiveThresholdType.FIXED
    min_failure_threshold: int = 3
    max_failure_threshold: int = 20
    adaptive_window_size: int = 100

    # Performance-based thresholds
    performance_threshold_ms: float = 1000.0  # Open if avg response time exceeds this
    performance_window_size: int = 50

    # Rate-based thresholds
    failure_rate_threshold: float = 0.5  # Open if 50%+ failure rate
    rate_window_size: int = 100

    # Dynamic configuration
    enable_dynamic_config: bool = True
    config_update_interval_seconds: float = 60.0
    auto_tune_thresholds: bool = True

    # Advanced metrics
    enable_detailed_metrics: bool = True
    metrics_retention_count: int = 10000

    # Event handling
    enable_event_callbacks: bool = True
    state_change_callbacks: list[Callable] = field(default_factory=list)