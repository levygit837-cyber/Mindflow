"""Token budget management for QueryEngine.

Mirrors Claude Code's budget management:
- TokenBudget: enforces context window limits
- Tracks token usage across all context sources
- Provides compression/trimming when approaching limits
- Auto-compact service for context window management
"""

from mindflow_backend.query.budget.auto_compact import (
    AutoCompactService,
    CompactConfig,
    CompactResult,
    CompactStrategy,
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
    "CompactConfig",
    "CompactResult",
    "CompactStrategy",
]