"""QueryEngine & Context Management for MindFlow.

Mirrors Claude Code's QueryEngine architecture and, as of the unified-engine
migration, is the canonical kernel for every request in MindFlow:

- QueryEngine: orchestrates query lifecycle, dispatches strategies, manages
  budget, delegation, workspace, communication, persistence, and hooks.
- Strategies (``query.strategies``): pluggable execution modes.
    DIRECT, REACT, DECOMPOSITION, DEEP_WORK.
- ContextBuilder: builds context from multiple providers.
- Context providers: git, file, memory, MCP.
- TokenBudget: manages context window budget.

Design principles:
- Providers are pluggable and independent.
- Budget is enforced at every level.
- Context is built incrementally and can be compressed.
- Strategies are stateless and data-driven (``StrategyContext``).
"""

from mindflow_backend.query.budget import TokenBudget
from mindflow_backend.query.context_builder import ContextBuilder
from mindflow_backend.query.engine import QueryEngine
from mindflow_backend.query.strategies import (
    BaseStrategy,
    QueryStrategy,
    StrategyContext,
    StrategyResult,
    get_strategy,
)

__all__ = [
    "QueryEngine",
    "ContextBuilder",
    "TokenBudget",
    "QueryStrategy",
    "StrategyContext",
    "StrategyResult",
    "BaseStrategy",
    "get_strategy",
]