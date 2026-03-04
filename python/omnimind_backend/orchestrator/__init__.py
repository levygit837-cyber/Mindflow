"""Orchestrator — decision and routing layer.

Public API:
    - ``route_message`` — keyword-based routing (Phase 2)
    - ``build_orchestrator_graph`` — compiled LangGraph graph
    - ``OrchestratorState`` — graph state TypedDict

Imports are lazy to avoid cascading through the entire agent system
when only submodules (e.g. decomposition.scoring) are needed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnimind_backend.orchestrator.graph import (
        OrchestratorState as OrchestratorState,
        build_orchestrator_graph as build_orchestrator_graph,
    )
    from omnimind_backend.orchestrator.router import route_message as route_message

__all__ = [
    "OrchestratorState",
    "build_orchestrator_graph",
    "route_message",
]


def __getattr__(name: str) -> object:
    if name in ("OrchestratorState", "build_orchestrator_graph", "build_simple_orchestrator_flow"):
        from omnimind_backend.orchestrator.graph import (
            OrchestratorState,
            build_orchestrator_graph,
        )
        return {"OrchestratorState": OrchestratorState, "build_orchestrator_graph": build_orchestrator_graph, "build_simple_orchestrator_flow": build_orchestrator_graph}[name]
    if name == "route_message":
        from omnimind_backend.orchestrator.router import route_message
        return route_message
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
