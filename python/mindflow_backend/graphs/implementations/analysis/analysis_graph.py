"""AnalysisGraph — Execution graph para missões de análise iterativa.

Fluxo: initialize → read_context → (investigate → annotate)* → synthesize → report
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.graphs.base.graph import BaseGraph
from mindflow_backend.graphs.base.state import GraphState
from mindflow_backend.graphs.base.types import GraphConfig, GraphType, NodeConnection
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

CONFIDENCE_THRESHOLD = 0.85
DEFAULT_MAX_ITERATIONS = 500


class AnalysisGraph(BaseGraph):
    """Grafo de análise iterativa para o agente Analyst."""

    @property
    def graph_type(self) -> GraphType:
        return GraphType.ANALYSIS

    def __init__(self, graph_id: str = "analysis", config: GraphConfig | None = None):
        super().__init__(graph_id, config or GraphConfig())
        self._setup_nodes()
        self._setup_connections()
        self.set_entry_point("initialize")

    def _setup_nodes(self) -> None:
        # Use generic common nodes
        from mindflow_backend.nodes.common.initialize_node import InitializeNode
        from mindflow_backend.nodes.common.read_context_node import ReadContextNode
        from mindflow_backend.nodes.common.report_node import ReportNode

        # Use Analyst-specific nodes
        from mindflow_backend.nodes.analysis.investigate_node import InvestigateNode
        from mindflow_backend.nodes.analysis.annotate_node import AnnotateNode
        from mindflow_backend.nodes.analysis.synthesize_node import SynthesizeNode

        self.add_node("initialize", InitializeNode("initialize"))
        self.add_node("read_context", ReadContextNode("read_context"))
        self.add_node("investigate", InvestigateNode("investigate"))
        self.add_node("annotate", AnnotateNode("annotate"))
        self.add_node("synthesize", SynthesizeNode("synthesize"))
        self.add_node("report", ReportNode("report"))

    def _setup_connections(self) -> None:
        self.add_connection(NodeConnection(source_node="initialize", target_node="read_context"))
        self.add_connection(NodeConnection(source_node="read_context", target_node="investigate"))
        self.add_connection(NodeConnection(source_node="investigate", target_node="annotate"))
        self.add_connection(NodeConnection(source_node="synthesize", target_node="report"))

    @staticmethod
    def _should_continue(state: dict[str, Any]) -> str:
        confidence = state.get("confidence", 0.0)
        iteration = state.get("iteration", 0)
        max_iter = state.get("max_iterations", DEFAULT_MAX_ITERATIONS)

        if confidence >= CONFIDENCE_THRESHOLD or iteration >= max_iter:
            return "synthesize"
        return "investigate"

    async def execute(self, state: GraphState) -> GraphState:
        """Executa o fluxo de análise iterativa com loop condicional."""
        current_node = self._entry_point
        nodes_executed = 0
        iteration = state.get("iteration", 0)

        while current_node:
            state["current_node"] = current_node

            try:
                node = self._nodes[current_node]
                if hasattr(node, "execute"):
                    result = await node.execute(state)
                    if isinstance(result, dict):
                        state.update(result)
                else:
                    result = await node(state)
                    if isinstance(result, dict):
                        state.update(result)

                nodes_executed += 1

            except Exception as e:
                state["error"] = str(e)
                _logger.error("analysis_node_error", node=current_node, error=str(e))
                break

            # Determine next node
            if current_node == "annotate":
                next_node = self._should_continue(dict(state))
                if next_node == "investigate":
                    iteration += 1
                    state["iteration"] = iteration
            elif current_node == "investigate":
                next_node = "annotate"
            elif current_node == "synthesize":
                next_node = "report"
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