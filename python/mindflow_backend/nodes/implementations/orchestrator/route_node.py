"""Compatibility node wrapper around the canonical router + planner flow."""

from __future__ import annotations

from typing import Any, Dict

from mindflow_backend.nodes.base.node import BaseNode, NodeType, NodeCategory
from mindflow_backend.nodes.base.stateful import StatefulNode


class RouteNode(StatefulNode, BaseNode):
    """Node that analyzes messages and routes to appropriate agents."""
    
    def __init__(self, node_id: str = "route") -> None:
        super().__init__(
            node_id=node_id,
            node_type=NodeType.ROUTER,
            category=NodeCategory.CONTROL_FLOW,
            description="Analyze user message and select agent personality"
        )
        
        # Required inputs for routing
        self.config.required_inputs = {"message"}
        self.config.outputs = {"decision", "complexity_score"}
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Route all requests to the Orchestrator as sole entry point."""
        from mindflow_backend.infra.logging import get_logger
        from mindflow_backend.schemas.orchestration.orchestrator import (
            AgentType,
            ExecutionStrategy,
            OrchestratorDecision,
        )

        _logger = get_logger(__name__)

        decision = OrchestratorDecision(
            agent=AgentType.ORCHESTRATOR,
            execution_strategy=ExecutionStrategy.DIRECT_RESPONSE,
            rationale="Orchestrator handles all requests directly.",
        )
        score = 0.0

        _logger.info("route_node_completed", agent="orchestrator", strategy="direct_response")

        self.set_node_state("last_agent", "orchestrator")
        self.set_node_state("last_complexity", score)
        self.set_node_state("routing_count", self.get_node_state("routing_count", 0) + 1)

        return {
            "decision": decision,
            "complexity_score": score,
        }
    
    def validate_inputs(self, state: Dict[str, Any]) -> list[str]:
        """Validate routing inputs."""
        errors = []
        
        if "message" not in state:
            errors.append("Missing required input: message")
        elif not isinstance(state["message"], str) or not state["message"].strip():
            errors.append("Message must be a non-empty string")
        
        return errors
    
    async def _on_initialize(self) -> None:
        """Initialize the route node."""
        self.set_node_state("routing_count", 0)
        self.set_node_state("last_agent", None)
        self.set_node_state("last_complexity", 0.0)
