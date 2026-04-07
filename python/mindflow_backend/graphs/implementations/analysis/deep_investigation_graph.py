"""DeepInvestigationGraph — Multi-pass investigation for deep codebase analysis.

Fluxo: initialize → scope → (pass_read → pass_annotate)* → cross_reference → synthesize → report
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.graphs.base.graph import BaseGraph
from mindflow_backend.graphs.base.state import GraphState
from mindflow_backend.graphs.base.types import GraphConfig, GraphType, NodeConnection
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

DEFAULT_MAX_PASSES = 10


class DeepInvestigationGraph(BaseGraph):
    """Grafo de investigação profunda com múltiplos passes independentes."""

    @property
    def graph_type(self) -> GraphType:
        return GraphType.DEEP_INVESTIGATION

    def __init__(self, graph_id: str = "deep_investigation", config: GraphConfig | None = None):
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
        self.add_node("scope", ReadContextNode("scope"))
        self.add_node("pass_read", InvestigateNode("pass_read"))
        self.add_node("pass_annotate", AnnotateNode("pass_annotate"))
        self.add_node("cross_reference", SynthesizeNode("cross_reference"))
        self.add_node("synthesize", SynthesizeNode("synthesize"))
        self.add_node("report", ReportNode("report"))

    def _setup_connections(self) -> None:
        self.add_connection(NodeConnection(source_node="initialize", target_node="scope"))
        self.add_connection(NodeConnection(source_node="scope", target_node="pass_read"))
        self.add_connection(NodeConnection(source_node="pass_read", target_node="pass_annotate"))
        self.add_connection(NodeConnection(source_node="pass_annotate", target_node="cross_reference"))
        self.add_connection(NodeConnection(source_node="cross_reference", target_node="synthesize"))
        self.add_connection(NodeConnection(source_node="synthesize", target_node="report"))

    @staticmethod
    def _should_continue_passes(state: dict[str, Any]) -> str:
        iteration = state.get("iteration", 0)
        max_passes = state.get("max_passes", DEFAULT_MAX_PASSES)
        if iteration >= max_passes:
            return "cross_reference"
        return "pass_read"

    async def execute(self, state: GraphState) -> GraphState:
        """Executa investigação profunda com múltiplos passes."""
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
                _logger.error("deep_investigation_error", node=current_node, error=str(e))
                break

            # Determine next node
            if current_node == "pass_annotate":
                iteration += 1
                state["iteration"] = iteration
                next_node = self._should_continue_passes(dict(state))
            elif current_node == "pass_read":
                next_node = "pass_annotate"
            else:
                next_nodes = self.get_next_nodes(current_node)
                next_node = next_nodes[0] if next_nodes else None

            current_node = next_node

        state["metrics"] = {
            "nodes_executed": nodes_executed,
            "nodes_failed": 1 if state.get("error") else 0,
            "total_tokens_used": 0,
            "passes_completed": iteration,
            "error_details": [state["error"]] if state.get("error") else [],
        }

        return state

    def validate(self) -> list[str]:
        return self.validate_structure()