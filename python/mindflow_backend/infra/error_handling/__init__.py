"""Error handling system inspired by Claude Code.

Provides:
- Error classification (classify_error)
- Granular retry by source (QuerySource-based)
- Persistent retry for capacity errors (529)
- Retry-After header support
- Streaming watchdog
"""

from .classifier import ErrorCategory, classify_error, is_retryable
from .retry_manager import (
    FOREGROUND_RETRY_SOURCES,
    QuerySource,
    RetryConfig,
    get_retry_delay,
    with_granular_retry,
)
from .persistent_retry import PersistentRetryConfig, persistent_retry
from .watchdog import StreamingWatchdog

__all__ = [
    # Classifier
    "ErrorCategory",
    "classify_error",
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
]
