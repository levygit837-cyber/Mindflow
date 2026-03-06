"""Orchestrator — decision and routing layer.

Public API:
    - ``route_message`` — intelligent LLM-based routing (Phase 2)
    - ``build_orchestrator_graph`` — compiled LangGraph graph
    - ``OrchestratorState`` — graph state TypedDict
    - ``context_validation`` — consolidated context validation

Imports are lazy to avoid cascading through the entire agent system
when only submodules (e.g. decomposition.scoring) are needed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mindflow_backend.orchestrator.graph import (
        OrchestratorState as OrchestratorState,
        build_orchestrator_graph as build_orchestrator_graph,
    )
    from mindflow_backend.orchestrator.router import route_message as route_message

__all__ = [
    "OrchestratorState",
    "build_orchestrator_graph",
    "route_message",
    "context_validation",
]


def __getattr__(name: str) -> object:
    if name in ("OrchestratorState", "build_orchestrator_graph", "build_simple_orchestrator_flow"):
        from mindflow_backend.orchestrator.graph import (
            OrchestratorState,
            build_orchestrator_graph,
        )
        return {"OrchestratorState": OrchestratorState, "build_orchestrator_graph": build_orchestrator_graph, "build_simple_orchestrator_flow": build_orchestrator_graph}[name]
    if name == "route_message":
        from mindflow_backend.orchestrator.router import route_message
        return route_message
    if name == "context_validation":
        from mindflow_backend.orchestrator import context_validation
        return context_validation
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
