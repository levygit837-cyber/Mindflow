"""CodingGraph — Implementation with auto-verify and verify-retry loop.

Fluxo: initialize → plan → read_context → implement → auto_verify → verify → test → report
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.graphs.base.graph import BaseGraph
from mindflow_backend.graphs.base.state import GraphState
from mindflow_backend.graphs.base.types import GraphConfig, GraphType, NodeConnection
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

MAX_VERIFY_RETRIES = 3


class CodingGraph(BaseGraph):
    """Grafo de implementação de código com retry de verificação."""

    @property
    def graph_type(self) -> GraphType:
        return GraphType.CODING_TASK

    def __init__(self, graph_id: str = "coding", config: GraphConfig | None = None):
        super().__init__(graph_id, config or GraphConfig())
        self._setup_nodes()
        self._setup_connections()
        self.set_entry_point("initialize")

    def _setup_nodes(self) -> None:
        from mindflow_backend.nodes.implementations.coding import (
            AutoVerifyNode,
            CodingInitializeNode,
            CodingReportNode,
            ImplementNode,
            PlanNode,
            TestNode,
            VerifyNode,
        )
        from mindflow_backend.nodes.implementations.analysis import ReadContextNode

        self.add_node("initialize", CodingInitializeNode("initialize"))
        self.add_node("plan", PlanNode("plan"))
        self.add_node("read_context", ReadContextNode("read_context"))
        self.add_node("implement", ImplementNode("implement"))
        self.add_node("auto_verify", AutoVerifyNode("auto_verify"))
        self.add_node("verify", VerifyNode("verify"))
        self.add_node("test", TestNode("test"))
        self.add_node("report", CodingReportNode("report"))

    def _setup_connections(self) -> None:
        self.add_connection(NodeConnection(source_node="initialize", target_node="plan"))
        self.add_connection(NodeConnection(source_node="plan", target_node="read_context"))
        self.add_connection(NodeConnection(source_node="read_context", target_node="implement"))
        self.add_connection(NodeConnection(source_node="implement", target_node="auto_verify"))
        self.add_connection(NodeConnection(source_node="auto_verify", target_node="verify"))
        self.add_connection(NodeConnection(source_node="verify", target_node="test"))
        self.add_connection(NodeConnection(source_node="test", target_node="report"))

    @staticmethod
    def _should_retry_implementation(state: dict[str, Any]) -> str:
        # First check auto_verify (quick check)
        if not state.get("auto_verify_passed", True):
            # If auto_verify failed, go back to implement
            return "implement"

        # Then check full verify
        if state.get("verify_passed"):
            return "test"

        # If verify failed but under retry limit, retry implement
        if state.get("verify_retries", 0) >= MAX_VERIFY_RETRIES:
            return "report"

        return "implement"

    async def execute(self, state: GraphState) -> GraphState:
        """Executa fluxo de implementação com auto-verify e retry de verificação."""
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
                _logger.error("coding_node_error", node=current_node, error=str(e))
                break

            # Determine next node
            if current_node == "verify":
                next_node = self._should_retry_implementation(dict(state))
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