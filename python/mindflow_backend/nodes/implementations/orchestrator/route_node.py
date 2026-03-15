"""Route node - analyzes user message and selects agent personality."""

from __future__ import annotations

from typing import Any, Dict

from mindflow_backend.nodes.base.node import BaseNode, NodeType, NodeCategory
from mindflow_backend.nodes.base.stateful import StatefulNode
from mindflow_backend.schemas.orchestration.orchestrator import (
    OrchestratorDecision,
    ThinkingMode,
)


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
        """Execute the routing logic."""
        from mindflow_backend.orchestrator.intelligent_router import route_message_intelligently
        from mindflow_backend.schemas.orchestration.delegation import OrchestratorSession
        from mindflow_backend.orchestrator.complexity import ComplexityScorer
        from mindflow_backend.infra.config import get_settings
        from mindflow_backend.infra.logging import get_logger
        
        _logger = get_logger(__name__)
        
        # Create orchestrator session
        session = OrchestratorSession(
            user_intent=state["message"],
        )

        if state.get("agent_type") == "analyst" and state.get("folder_path"):
            from mindflow_backend.schemas.orchestration.orchestrator import (
                AgentType,
                ChainType,
                ExecutionStrategy,
                Priority,
                ThinkingLevel,
            )

            scorer = ComplexityScorer()
            score = await scorer.get_complexity_score(
                state["message"],
                provider=state.get("provider"),
                model=state.get("model"),
            )
            decision = OrchestratorDecision(
                rationale="Forced file analysis for analyst request with workspace root.",
                agent=AgentType.ANALYST,
                task=state["message"],
                thinking=ThinkingLevel.HIGH,
                priority=Priority.HIGH,
                execution_strategy=ExecutionStrategy.CHAIN,
                chain_id="file_analysis",
                chain_type=ChainType.FILE_ANALYSIS,
            )
            return {"decision": decision, "complexity_score": score}
        
        # Use intelligent routing
        decision = await route_message_intelligently(
            state["message"],
            session,
            folder_path=state.get("folder_path"),
        )
        
        # Calculate complexity score
        scorer = ComplexityScorer()
        score = await scorer.get_complexity_score(
            state["message"], 
            provider=state.get("provider"), 
            model=state.get("model")
        )
        
        # Check for decomposition thinking
        settings = get_settings()
        if settings.enable_decomposition_thinking and scorer.should_decompose(score):
            decision.thinking_mode = ThinkingMode.DECOMPOSITION
            _logger.info("route_node_triggering_dt", score=score)
        elif scorer.should_decompose(score):
            _logger.info("route_node_dt_disabled", score=score)
        
        _logger.info("route_node_completed", agent=decision.agent.value, score=score)
        
        # Update node state
        self.set_node_state("last_agent", decision.agent.value)
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
