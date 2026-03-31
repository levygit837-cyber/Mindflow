"""SecurityAuditGraph — Read-only security audit with vulnerability scanning.

Fluxo: initialize → scan_surface → identify_vectors → (test_vulnerabilities → document)* → prioritize → report

Regra especial: Sandbox sempre READ_ONLY. Nunca escreve arquivos.
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.graphs.base.graph import BaseGraph
from mindflow_backend.graphs.base.state import GraphState
from mindflow_backend.graphs.base.types import GraphConfig, GraphType, NodeConnection
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class SecurityAuditGraph(BaseGraph):
    """Grafo de auditoria de segurança READ-ONLY."""

    @property
    def graph_type(self) -> GraphType:
        return GraphType.SECURITY_AUDIT

    def __init__(self, graph_id: str = "security_audit", config: GraphConfig | None = None):
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
        self.add_node("scan_surface", ReadContextNode("scan_surface"))
        self.add_node("identify_vectors", InvestigateNode("identify_vectors"))
        self.add_node("test_vulnerabilities", InvestigateNode("test_vulnerabilities"))
        self.add_node("document", AnnotateNode("document"))
        self.add_node("prioritize", SynthesizeNode("prioritize"))
        self.add_node("report", AnalysisReportNode("report"))

    def _setup_connections(self) -> None:
        self.add_connection(NodeConnection(source_node="initialize", target_node="scan_surface"))
        self.add_connection(NodeConnection(source_node="scan_surface", target_node="identify_vectors"))
        self.add_connection(NodeConnection(source_node="identify_vectors", target_node="test_vulnerabilities"))
        self.add_connection(NodeConnection(source_node="test_vulnerabilities", target_node="document"))
        self.add_connection(NodeConnection(source_node="document", target_node="prioritize"))
        self.add_connection(NodeConnection(source_node="prioritize", target_node="report"))

    @staticmethod
    def _should_continue_vuln_scan(state: dict[str, Any]) -> str:
        """Cada vulnerabilidade é documentada imediatamente."""
        iteration = state.get("iteration", 0)
        max_vulns = state.get("max_vulnerabilities", 50)
        if iteration >= max_vulns:
            return "prioritize"
        return "test_vulnerabilities"

    async def execute(self, state: GraphState) -> GraphState:
        """Executa auditoria de segurança READ-ONLY."""
        # Mark sandbox as read-only
        state["sandbox_mode"] = "read_only"

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
                _logger.error("security_audit_error", node=current_node, error=str(e))
                break

            # Determine next node
            if current_node == "document":
                next_node = self._should_continue_vuln_scan(dict(state))
            elif current_node == "test_vulnerabilities":
                next_node = "document"
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