"""Compatibility adapter for legacy orchestrator graph imports.

The canonical runtime is implemented in
``mindflow_backend.graphs.implementations.orchestrator.simple_flow`` and is
constructed through ``mindflow_backend.graphs.factory``. This module preserves
older imports without defining a separate execution path.
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.graphs.factory import create_orchestrator_graph
from mindflow_backend.graphs.implementations.orchestrator.simple_flow import (
    SimpleOrchestratorGraph,
    build_simple_orchestrator_flow,
)


async def execute_node(state: dict[str, Any]) -> dict[str, Any]:
    """Run the canonical execute step through the simple-flow implementation."""
    graph = SimpleOrchestratorGraph()
    return await graph._execute_node_legacy(state)


__all__ = [
    "build_simple_orchestrator_flow",
    "create_orchestrator_graph",
    "execute_node",
]
