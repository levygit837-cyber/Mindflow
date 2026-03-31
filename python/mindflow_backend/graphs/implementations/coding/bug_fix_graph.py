"""BugFixGraph — Reproduce, diagnose, fix, verify.

Fluxo: initialize → reproduce → diagnose → (fix → verify)* → test → report
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.graphs.base.graph import BaseGraph
from mindflow_backend.graphs.base.state import GraphState
from mindflow_backend.graphs.base.types import GraphConfig, GraphType, NodeConnection
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

MAX_FIX_RETRIES = 3


class BugFixGraph(BaseGraph):
    """Grafo de correção de bugs com reprodução e verificação."""

    @property
    def graph_type(self) -> GraphType:
        return GraphType.BUG_FIX

    def __init__(self, graph_id: str = "bug_fix", config: GraphConfig | None = None):
        super().__init__(graph_id, config or GraphConfig())
        self._setup_nodes()
        self._setup_connections()
        self.set_entry_point("initialize")

    def _setup_nodes(self) -> None:
        from mindflow_backend.nodes.implementations.coding import (
            CodingInitializeNode,
            CodingReportNode,
            ImplementNode,
            TestNode,
            VerifyNode,
        )
        from mindflow_backend.nodes.implementations.analysis import InvestigateNode, ReadContextNode

        self.add_node("initialize", CodingInitializeNode("initialize"))
        self.add_node("reproduce", ReadContextNode("reproduce"))
        self.add_node("diagnose", InvestigateNode("diagnose"))
        self.add_node("fix", ImplementNode("fix"))
        self.add_node("verify", VerifyNode("verify"))
        self.add_node("test", TestNode("test"))
        self.add_node("report", CodingReportNode("report"))

    def _setup_connections(self) -> None:
        self.add_connection(NodeConnection(source_node="initialize", target_node="reproduce"))
        self.add_connection(NodeConnection(source_node="reproduce", target_node="diagnose"))
        self.add_connection(NodeConnection(source_node="diagnose", target_node="fix"))
        self.add_connection(NodeConnection(source_node="fix", target_node="verify"))
        self.add_connection(NodeConnection(source_node="verify", target_node="test"))
        self.add_connection(NodeConnection(source_node="test", target_node="report"))

    @staticmethod
    def _should_retry_fix(state: dict[str, Any]) -> str:
        if state.get("verify_passed"):
            return "test"
        if state.get("verify_retries", 0) >= MAX_FIX_RETRIES:
            return "report"
        return "fix"

    async def execute(self, state: GraphState) -> GraphState:
        """Executa fluxo de correção de bugs."""
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
                _logger.error("bug_fix_error", node=current_node, error=str(e))
                break

            if current_node == "verify":
                next_node = self._should_retry_fix(dict(state))
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