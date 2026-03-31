"""ResearchGraph — Multi-source research with deduplication.

Fluxo: initialize → (search → collect)* → deduplicate → synthesize → cite → report
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.graphs.base.graph import BaseGraph
from mindflow_backend.graphs.base.state import GraphState
from mindflow_backend.graphs.base.types import GraphConfig, GraphType, NodeConnection
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

DEFAULT_MAX_SEARCHES = 10


class ResearchGraph(BaseGraph):
    """Grafo de pesquisa multi-fonte com deduplicação."""

    @property
    def graph_type(self) -> GraphType:
        return GraphType.WEB_RESEARCH

    def __init__(self, graph_id: str = "research", config: GraphConfig | None = None):
        super().__init__(graph_id, config or GraphConfig())
        self._setup_nodes()
        self._setup_connections()
        self.set_entry_point("initialize")

    def _setup_nodes(self) -> None:
        from mindflow_backend.nodes.implementations.research import (
            CiteNode,
            CollectNode,
            DeduplicateNode,
            ResearchInitializeNode,
            ResearchReportNode,
            ResearchSynthesizeNode,
            SearchNode,
        )

        self.add_node("initialize", ResearchInitializeNode("initialize"))
        self.add_node("search", SearchNode("search"))
        self.add_node("collect", CollectNode("collect"))
        self.add_node("deduplicate", DeduplicateNode("deduplicate"))
        self.add_node("synthesize", ResearchSynthesizeNode("synthesize"))
        self.add_node("cite", CiteNode("cite"))
        self.add_node("report", ResearchReportNode("report"))

    def _setup_connections(self) -> None:
        self.add_connection(NodeConnection(source_node="initialize", target_node="search"))
        self.add_connection(NodeConnection(source_node="search", target_node="collect"))
        self.add_connection(NodeConnection(source_node="collect", target_node="deduplicate"))
        self.add_connection(NodeConnection(source_node="deduplicate", target_node="synthesize"))
        self.add_connection(NodeConnection(source_node="synthesize", target_node="cite"))
        self.add_connection(NodeConnection(source_node="cite", target_node="report"))

    @staticmethod
    def _should_continue_search(state: dict[str, Any]) -> str:
        iteration = state.get("iteration", 0)
        max_searches = state.get("max_searches", DEFAULT_MAX_SEARCHES)
        if iteration >= max_searches:
            return "deduplicate"
        return "search"

    async def execute(self, state: GraphState) -> GraphState:
        """Executa fluxo de pesquisa multi-fonte."""
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
                _logger.error("research_error", node=current_node, error=str(e))
                break

            if current_node == "collect":
                next_node = self._should_continue_search(dict(state))
            elif current_node == "search":
                next_node = "collect"
            else:
                next_nodes = self.get_next_nodes(current_node)
                next_node = next_nodes[0] if next_nodes else None

            current_node = next_node

        state["metrics"] = {
            "nodes_executed": nodes_executed,
            "nodes_failed": 1 if state.get("error") else 0,
            "total_tokens_used": 0,
            "error_details": [state["error"]] if state.get("error") else [],
        }

        return state

    def validate(self) -> list[str]:
        return self.validate_structure()