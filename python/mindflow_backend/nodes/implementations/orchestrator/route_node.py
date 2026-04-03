"""Compatibility node wrapper around the canonical router + planner flow."""

from __future__ import annotations

from typing import Any

from mindflow_backend.nodes.base.node import BaseNode, NodeCategory, NodeType
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
    
    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Route requests using DecentralizedRouter or IntelligentRouter."""
        from mindflow_backend.infra.config import get_settings
        from mindflow_backend.infra.logging import get_logger

        _logger = get_logger(__name__)
        settings = get_settings()
        folder_path = state.get("folder_path")

        _logger.info("route_node_starting", message=state["message"][:100], has_folder_path=bool(folder_path))

        # Use DecentralizedRouter if enabled
        use_decentralized = getattr(settings, "use_decentralized_router", False)

        try:
            if use_decentralized:
                from mindflow_backend.orchestrator.routing.decentralized_router import (
                    get_decentralized_router,
                )
                router = get_decentralized_router()
                _logger.info("route_node_using_decentralized_router")
                decision = await router.route_message(
                    message=state["message"],
                    session=None,
                    folder_path=folder_path,
                )
            else:
                from mindflow_backend.orchestrator.routing.intelligent_router import (
                    get_intelligent_router,
                )
                router = get_intelligent_router()
                decision = await router.route_message_intelligently(
                    message=state["message"],
                    session=None,
                    folder_path=folder_path,
                )

            # Calculate complexity score based on strategy
            complexity_map = {
                "direct_response": 0.0,
                "single_agent": 0.5,
                "chain": 0.7,
                "graph": 0.9,
            }
            score = complexity_map.get(decision.execution_strategy.value, 0.5)

            _logger.info(
                "route_node_completed",
                agent=decision.agent.value,
                strategy=decision.execution_strategy.value,
                specialist=decision.specialist.value if decision.specialist else None,
                confidence=decision.confidence,
                tools_count=len(decision.tools) if hasattr(decision, 'tools') else 0,
            )

            self.set_node_state("last_agent", decision.agent.value)
            self.set_node_state("last_complexity", score)
            self.set_node_state("routing_count", self.get_node_state("routing_count", 0) + 1)

            return {
                "decision": decision,
                "complexity_score": score,
            }

        except Exception as exc:
            _logger.error("route_node_error", error=str(exc), exc_info=True)
            # Fallback to analyst on error
            from mindflow_backend.schemas.orchestration.orchestrator import (
                AgentType,
                ExecutionStrategy,
                OrchestratorDecision,
            )

            fallback_decision = OrchestratorDecision(
                agent=AgentType.ANALYST,
                execution_strategy=ExecutionStrategy.DELEGATE,
                rationale=f"Routing failed, defaulting to analyst: {exc}",
            )

            return {
                "decision": fallback_decision,
                "complexity_score": 0.5,
            }
    
    def validate_inputs(self, state: dict[str, Any]) -> list[str]:
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
