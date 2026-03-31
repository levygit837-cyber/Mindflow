"""CodeReviewGraph — Structured code review with pattern detection.

Fluxo: initialize → read_files → analyze_patterns → check_standards → annotate_findings → synthesize → report
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.graphs.base.graph import BaseGraph
from mindflow_backend.graphs.base.state import GraphState
from mindflow_backend.graphs.base.types import GraphConfig, GraphType, NodeConnection
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class CodeReviewGraph(BaseGraph):
    """Grafo de revisão de código estruturada."""

    @property
    def graph_type(self) -> GraphType:
        return GraphType.CODE_REVIEW

    def __init__(self, graph_id: str = "code_review", config: GraphConfig | None = None):
        super().__init__(graph_id, config or GraphConfig())
        self._setup_nodes()
        self._setup_connections()
        self.set_entry_point("initialize")

    def _setup_nodes(self) -> None:
        from mindflow_backend.nodes.implementations.analysis import (
            AnalysisInitializeNode,
            AnalysisReportNode,
            AnnotateNode,
            InvestigateNode,
            ReadContextNode,
            SynthesizeNode,
        )

        self.add_node("initialize", AnalysisInitializeNode("initialize"))
        self.add_node("read_files", ReadContextNode("read_files"))
        self.add_node("analyze_patterns", InvestigateNode("analyze_patterns"))
        self.add_node("check_standards", InvestigateNode("check_standards"))
        self.add_node("annotate_findings", AnnotateNode("annotate_findings"))
        self.add_node("synthesize", SynthesizeNode("synthesize"))
        self.add_node("report", AnalysisReportNode("report"))

    def _setup_connections(self) -> None:
        self.add_connection(NodeConnection(source_node="initialize", target_node="read_files"))
        self.add_connection(NodeConnection(source_node="read_files", target_node="analyze_patterns"))
        self.add_connection(NodeConnection(source_node="analyze_patterns", target_node="check_standards"))
        self.add_connection(NodeConnection(source_node="check_standards", target_node="annotate_findings"))
        self.add_connection(NodeConnection(source_node="annotate_findings", target_node="synthesize"))
        self.add_connection(NodeConnection(source_node="synthesize", target_node="report"))

    async def execute(self, state: GraphState) -> GraphState:
        """Executa revisão de código estruturada."""
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
                _logger.error("code_review_error", node=current_node, error=str(e))
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