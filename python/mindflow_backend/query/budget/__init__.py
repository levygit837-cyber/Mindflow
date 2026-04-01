"""Token budget management for QueryEngine.

Mirrors Claude Code's budget management:
- TokenBudget: enforces context window limits
- Tracks token usage across all context sources
- Provides compression/trimming when approaching limits
- Auto-compact service for context window management
- LLM-based summary compaction with PTL retry
- Circuit breaker for failure protection
- File state preservation for post-compaction restoration
- Keep-alive signals for long compaction operations
"""

from mindflow_backend.query.budget.auto_compact import (
    AutoCompactService,
    AutoCompactTrackingState,
    CompactConfig,
    CompactResult,
    CompactStrategy,
    FileState,
    MAX_PTL_RETRIES,
    MAX_CONSECUTIVE_FAILURES,
    AUTOCOMPACT_BUFFER_TOKENS,
    POST_COMPACT_MAX_FILES_TO_RESTORE,
    POST_COMPACT_TOKEN_BUDGET,
    POST_COMPACT_MAX_TOKENS_PER_FILE,
    KEEPALIVE_INTERVAL_SECONDS,
)
from mindflow_backend.query.budget.token_budget_manager import (
    TokenBudgetConfig,
    TokenBudgetManager,
    TokenUsage,
)
from mindflow_backend.query.budget.token_counter import TokenBudget, TokenUsage as TokenCounterUsage

__all__ = [
    "TokenBudget",
    "TokenUsage",
    "TokenCounterUsage",
    "TokenBudgetConfig",
    "TokenBudgetManager",
    "AutoCompactService",
    "AutoCompactTrackingState",
    "CompactConfig",
    "CompactResult",
    "CompactStrategy",
    "FileState",
    "MAX_PTL_RETRIES",
    "MAX_CONSECUTIVE_FAILURES",
    "AUTOCOMPACT_BUFFER_TOKENS",
    "POST_COMPACT_MAX_FILES_TO_RESTORE",
    "POST_COMPACT_TOKEN_BUDGET",
    "POST_COMPACT_MAX_TOKENS_PER_FILE",
    "KEEPALIVE_INTERVAL_SECONDS",
    "MODEL_CONTEXT_WINDOWS",
]
