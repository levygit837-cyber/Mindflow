"""Error handling system inspired by Claude Code.

Provides:
- Error classification (classify_error, classify_error_full)
- Error severity levels (ErrorSeverity)
- Granular retry by source (QuerySource-based)
- Persistent retry for capacity errors (529)
- Retry-After header support
- Streaming watchdog
- Model fallback with health tracking
- Graceful degradation for features
"""

from .classifier import (
    ErrorCategory,
    ErrorClassification,
    ErrorSeverity,
    classify_error,
    classify_error_full,
    get_error_severity,
    is_retryable,
)
from .retry_manager import (
    FOREGROUND_RETRY_SOURCES,
    QuerySource,
    RetryConfig,
    get_retry_delay,
    with_granular_retry,
)
from .persistent_retry import PersistentRetryConfig, persistent_retry
from .watchdog import StreamingWatchdog
from .model_fallback import (
    FallbackChain,
    ModelFallbackExhaustedError,
    ModelFallbackManager,
    ModelHealth,
    ModelStatus,
    calculate_backoff_delay,
    get_fallback_manager,
)
from .graceful_degradation import (
    DegradationLevel,
    DegradationPolicy,
    FeatureState,
    GracefulDegradationManager,
    get_degradation_manager,
)

__all__ = [
    # Classifier
    "ErrorCategory",
    "ErrorClassification",
    "ErrorSeverity",
    "classify_error",
    "classify_error_full",
    "get_error_severity",
    "is_retryable",
    # Retry Manager
    "QuerySource",
    "FOREGROUND_RETRY_SOURCES",
    "RetryConfig",
    "get_retry_delay",
    "with_granular_retry",
    # Persistent Retry
    "PersistentRetryConfig",
    "persistent_retry",
    # Watchdog
    "StreamingWatchdog",
    # Model Fallback
    "FallbackChain",
    "ModelFallbackExhaustedError",
    "ModelFallbackManager",
    "ModelHealth",
    "ModelStatus",
    "calculate_backoff_delay",
    "get_fallback_manager",
    # Graceful Degradation
    "DegradationLevel",
    "DegradationPolicy",
    "FeatureState",
    "GracefulDegradationManager",
    "get_degradation_manager",
]
