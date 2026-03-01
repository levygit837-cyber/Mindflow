"""Orchestrator — decision and routing layer.

Public API:
    - ``route_message`` — keyword-based routing (Phase 2)
    - ``build_orchestrator_graph`` — compiled LangGraph graph
    - ``OrchestratorState`` — graph state TypedDict
"""

from omnimind_backend.orchestrator.graph import (
    OrchestratorState,
    build_orchestrator_graph,
)
from omnimind_backend.orchestrator.router import route_message

__all__ = [
    "OrchestratorState",
    "build_orchestrator_graph",
    "route_message",
]
