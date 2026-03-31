"""ComparisonGraph — Compare multiple options/solutions.

Fluxo: initialize → gather_options → analyze_each → compare → synthesize → report
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.graphs.base.graph import BaseGraph
from mindflow_backend.graphs.base.state import GraphState
from mindflow_backend.graphs.base.types import GraphConfig, GraphType, NodeConnection
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class ComparisonGraph(BaseGraph):
    """Grafo de comparação de múltiplas opções/soluções."""

    @property
    def graph_type(self) -> GraphType:
        return GraphType.COMPARISON

    def __init__(self, graph_id: str = "comparison", config: GraphConfig | None = None):
        super().__init__(graph_id, config or GraphConfig())
        self._setup_nodes()
        self._setup_connections()
        self.set_entry_point("initialize")

    def _setup_nodes(self) -> None:
        from mindflow_backend.nodes.implementations.research import (
            CollectNode,
            ResearchInitializeNode,
            ResearchReportNode,
            ResearchSynthesizeNode,
            SearchNode,
        )

        self.add_node("initialize", ResearchInitializeNode("initialize"))
        self.add_node("gather_options", SearchNode("gather_options"))
        self.add_node("analyze_each", CollectNode("analyze_each"))
        self.add_node("compare", ResearchSynthesizeNode("compare"))
        self.add_node("synthesize", ResearchSynthesizeNode("synthesize"))
        self.add_node("report", ResearchReportNode("report"))

    def _setup_connections(self) -> None:
        self.add_connection(NodeConnection(source_node="initialize", target_node="gather_options"))
        self.add_connection(NodeConnection(source_node="gather_options", target_node="analyze_each"))
        self.add_connection(NodeConnection(source_node="analyze_each", target_node="compare"))
        self.add_connection(NodeConnection(source_node="compare", target_node="synthesize"))
        self.add_connection(NodeConnection(source_node="synthesize", target_node="report"))

    async def execute(self, state: GraphState) -> GraphState:
        """Executa fluxo de comparação."""
        current_node = self._entry_point
        nodes_executed = 0

        while current_node:
            state["current_node"] = current_node

            try:
                node = self._nodes[current_node]
                if hasattr(node, "execute"):
                    result = await node.execute(state)
                    if isinstance(result, dict):
                        state.update(result)
                nodes_executed += 1

            except Exception as e:
                state["error"] = str(e)
                _logger.error("comparison_error", node=current_node, error=str(e))
                break

            next_nodes = self.get_next_nodes(current_node)
            current_node = next_nodes[0] if next_nodes else None

        state["metrics"] = {
            "nodes_executed": nodes_executed,
            "nodes_failed": 1 if state.get("error") else 0,
            "total_tokens_used": 0,
            "error_details": [state["error"]] if state.get("error") else [],
        }

        return state

    def validate(self) -> list[str]:
        return self.validate_structure()