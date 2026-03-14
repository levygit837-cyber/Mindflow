"""Decomposition graph stub."""

from __future__ import annotations

from typing import Any, Dict

from mindflow_backend.graphs.base.graph import SimpleGraph
from mindflow_backend.graphs.base.types import GraphConfig, GraphType


class DecompositionGraph(SimpleGraph):
    """Graph that decomposes complex tasks into sub-tasks."""

    def __init__(self, graph_id: str = "decomposition") -> None:
        config = GraphConfig(graph_type=GraphType.SIMPLE, enable_streaming=True)
        super().__init__(graph_id, config)

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return {"result": None, "metadata": {"graph_id": self.graph_id}}
