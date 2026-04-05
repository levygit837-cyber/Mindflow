"""Resilience utilities — retry, circuit breaker, and timeout configs.

Consolidated module that re-exports:
- Unified circuit breaker from circuit_breaker subpackage
- Orchestration fallback system (component-level graceful degradation)
- Orchestration retry system (retry before fallback)
- Negotiation timer for consensus phases
- Backward-compatible aliases for legacy imports
"""

from __future__ import annotations

from mindflow_backend.infra.logging import get_logger

# Re-export unified circuit breaker
from .circuit_breaker import (
    AdaptiveThresholdType,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerMetrics,
)
from mindflow_backend.infra.resilience.orchestration_fallback import (
    ComponentStatus,
    FallbackContext,
    FallbackResult,
    get_orchestration_fallback_manager,
    OrchestrationFallbackManager,
)
from mindflow_backend.infra.resilience.orchestration_fallback_metrics import (
    get_orchestration_fallback_metrics_collector,
    OrchestrationFallbackMetrics,
    OrchestrationFallbackMetricsCollector,
)
from mindflow_backend.infra.resilience.orchestration_fallback_registry import (
    get_orchestration_fallback_registry,
    OrchestrationFallbackRegistry,
)
from mindflow_backend.infra.resilience.orchestration_retry import (
    get_orchestration_retry_manager,
    OrchestrationRetryConfig,
    OrchestrationRetryManager,
)

from .negotiation_timer import (
    NegotiationTimer,
    TimerAlert,
    TimerConfig,
    TimerPhase,
    run_timer_with_alerts,
)

_logger = get_logger(__name__)


__all__ = [
    # Circuit Breaker (unified)
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerStats",
    "CircuitOpenError",
    "CircuitState",
    "circuit_protected",
    "get_breaker",
    "get_all_breakers",
    "get_all_stats",
    "reset_all_breakers",
    # Enhanced
    "AdaptiveThresholdType",
    "EnhancedCircuitBreaker",
    "EnhancedCircuitBreakerConfig",
    # Metrics
    "CircuitBreakerMetrics",
    # Orchestration Fallback
    "ComponentStatus",
    "FallbackContext",
    "FallbackResult",
    "OrchestrationFallbackManager",
    "get_orchestration_fallback_manager",
    "OrchestrationFallbackRegistry",
    "get_orchestration_fallback_registry",
    "OrchestrationFallbackMetrics",
    "OrchestrationFallbackMetricsCollector",
    "get_orchestration_fallback_metrics_collector",
    # Orchestration Retry
    "OrchestrationRetryConfig",
    "OrchestrationRetryManager",
    "get_orchestration_retry_manager",
    # Negotiation Timer
    "NegotiationTimer",
    "TimerAlert",
    "TimerConfig",
    "TimerPhase",
    "run_timer_with_alerts",
]