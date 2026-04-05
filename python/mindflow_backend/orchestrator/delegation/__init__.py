"""Delegation sub-package — agent task execution.

DEPRECATED: Use QueryEngine instead. This module is kept for backward compatibility
and will be removed in a future release.

Migration guide:
- Replace DelegationEngine with QueryEngine
- Replace get_delegation_engine() with QueryEngine(providers=[], budget=TokenBudget())
- All delegation functionality is now in QueryEngine.delegate_task()
"""
from mindflow_backend.query.budget.token_counter import TokenBudget
from mindflow_backend.query.engine import QueryEngine

# Backward compatibility wrapper
def get_delegation_engine() -> QueryEngine:
    """Get a QueryEngine instance (backward compatibility for DelegationEngine)."""
    return QueryEngine(
        providers=[],
        budget=TokenBudget(max_tokens=200_000),
        session_id="delegation_compat",
        use_file_cache=False,
    )

# Alias for backward compatibility
DelegationEngine = QueryEngine

__all__ = ["DelegationEngine", "get_delegation_engine"]
