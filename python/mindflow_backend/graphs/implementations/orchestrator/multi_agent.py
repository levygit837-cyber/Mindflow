"""Multi-agent graph stub."""

from __future__ import annotations

from typing import Any

from mindflow_backend.graphs.base.graph import SimpleGraph
from mindflow_backend.graphs.base.types import GraphConfig, GraphType


class MultiAgentGraph(SimpleGraph):
    """Graph that coordinates multiple agents in parallel or sequentially."""

    def __init__(self, graph_id: str = "multi_agent") -> None:
        config = GraphConfig(graph_type=GraphType.SIMPLE, enable_streaming=True)
        super().__init__(graph_id, config)

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        return {"result": None, "metadata": {"graph_id": self.graph_id}}
