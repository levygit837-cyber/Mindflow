"""Compatibility planner backed by the canonical ResearchQueryEngine."""

from __future__ import annotations

from typing import Any

from mindflow_backend.agents.tools.specialist.research.core.query_engine import (
    ResearchQueryEngine,
)
from mindflow_backend.schemas.agents.research import QueryIntent, QueryPlan


class EnhancedQueryPlanner:
    """Bridge older planner calls onto the canonical query engine."""

    def __init__(self, query_engine: ResearchQueryEngine | None = None) -> None:
        self.query_engine = query_engine or ResearchQueryEngine()

    def analyze_intent(self, query: str) -> QueryIntent:
        """Analyze query intent using the canonical research engine."""
        return self.query_engine.analyze_intent(query)

    def plan_queries(self, intent: QueryIntent, query: str) -> QueryPlan:
        """Plan browser queries using the canonical research engine."""
        return self.query_engine.plan_queries(intent, query)

    async def plan_query(self, query: str, context: dict[str, Any] | None = None) -> QueryPlan:
        """Async compatibility wrapper for older planner entrypoints."""
        del context
        intent = self.analyze_intent(query)
        return self.plan_queries(intent, query)

    async def optimize_query(self, query: str) -> list[str]:
        """Return the expanded query variants that would be executed."""
        intent = self.analyze_intent(query)
        return self.plan_queries(intent, query).queries


def get_enhanced_query_planner() -> EnhancedQueryPlanner:
    """Return a compatibility planner instance."""
    return EnhancedQueryPlanner()


__all__ = ["EnhancedQueryPlanner", "get_enhanced_query_planner"]
