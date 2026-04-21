"""QueryEngine execution strategies.

Each strategy is a pluggable execution mode invoked by
``QueryEngine.execute(strategy, context)``. They unify the loops that previously
lived in multiple places (AgentRuntime, SimpleOrchestratorGraph,
DecompositionEngine, Deep Work Loop) under a single contract.

Strategies:
- DIRECT        — single LLM call, no tool loop (legacy direct-agent path)
- REACT         — Claude Code-style while-true ReAct loop (prior QueryLoop)
- DECOMPOSITION — Tasker → Scheduler → Resolver → Synthesizer pipeline
- DEEP_WORK     — multi-turn continuation protocol with accumulated context

See docs/09-analysis-and-reports/REPO-AUDIT-2026-04-20.md and
.windsurf/plans/unified-engine-47796c.md for the full migration plan.
"""

from __future__ import annotations

from mindflow_backend.query.strategies.base import (
    BaseStrategy,
    QueryStrategy,
    StrategyContext,
    StrategyResult,
)

__all__ = [
    "BaseStrategy",
    "QueryStrategy",
    "StrategyContext",
    "StrategyResult",
    "get_strategy",
]


def get_strategy(strategy: QueryStrategy) -> BaseStrategy:
    """Resolve a ``QueryStrategy`` enum to a concrete strategy instance.

    Lazy-imports strategy modules so importing the package itself stays cheap.
    """
    if strategy is QueryStrategy.DIRECT:
        from mindflow_backend.query.strategies.direct import DirectStrategy

        return DirectStrategy()
    if strategy is QueryStrategy.REACT:
        from mindflow_backend.query.strategies.react import ReActStrategy

        return ReActStrategy()
    if strategy is QueryStrategy.DECOMPOSITION:
        from mindflow_backend.query.strategies.decomposition import (
            DecompositionStrategy,
        )

        return DecompositionStrategy()
    if strategy is QueryStrategy.DEEP_WORK:
        from mindflow_backend.query.strategies.deep_work import DeepWorkStrategy

        return DeepWorkStrategy()
    raise ValueError(f"Unknown QueryStrategy: {strategy!r}")
