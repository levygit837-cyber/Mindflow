"""
Runtime Router - Determines execution strategy for agent requests.

Handles routing logic for orchestrated, direct agent, and legacy execution modes.
"""

from typing import Any
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.chat.agent import AgentChatRequest

_logger = get_logger(__name__)


class RuntimeRouter:
    """
    Routes agent requests to appropriate execution strategy.
    
    Determines whether a request should be:
    - Orchestrated (multi-agent via LangGraph)
    - Direct (single agent execution)
    - Legacy (simple LLM call)
    """
    
    def resolve_execution_mode(self, payload: AgentChatRequest) -> str:
        """
        Determine the execution mode for a request.
        
        Args:
            payload: The chat request payload
            
        Returns:
            Execution mode: "orchestrated", "direct", or "legacy"
        """
        if payload.orchestrate or self._should_force_structured_analyst_flow(payload):
            return "orchestrated"
        if getattr(payload, "agent_type", None):
            return "direct"
        return "legacy"
    
    def _should_force_structured_analyst_flow(self, payload: AgentChatRequest) -> bool:
        """
        Force structured analyst flow for analyst agent with folder path.
        """
        return (
            (getattr(payload, "agent_type", None) or "").lower() == "analyst"
            and bool(getattr(payload, "folder_path", None))
        )
    
    def is_direct_response(self, decision: Any) -> bool:
        """
        Check if the orchestrator decision is a direct response (no delegation).
        """
        try:
            from mindflow_backend.schemas.orchestration.orchestrator import ExecutionStrategy
            if isinstance(decision, dict):
                s = decision.get("execution_strategy", "")
                return s == ExecutionStrategy.DIRECT_RESPONSE.value or s == "direct_response"
            s = getattr(decision, "execution_strategy", None)
            return s == ExecutionStrategy.DIRECT_RESPONSE
        except Exception:
            return False
    
    def get_decision_payload(self, decision: Any) -> dict[str, Any]:
        """
        Extract normalized payload from orchestrator decision.
        """
        if isinstance(decision, dict):
            agent_role = decision.get("agent_role") or decision.get("agent") or "coder"
            agent_role = getattr(agent_role, "value", agent_role)
            specialist = decision.get("specialist")
            specialist = getattr(specialist, "value", specialist) if specialist is not None else None
            agent_id = decision.get("agent_id") or (
                f"{str(agent_role).lower()}:{specialist}" if specialist else str(agent_role).lower()
            )
            return {
                "agent_type": str(agent_role).upper(),
                "agent_role": str(agent_role).lower(),
                "agent_id": str(agent_id).lower(),
                "specialist": specialist,
                "task": decision.get("task", ""),
            }
        
        agent_role = getattr(decision, "agent_role", None) or getattr(decision, "agent", None) or "coder"
        agent_role_value = getattr(agent_role, "value", agent_role)
        specialist = getattr(decision, "specialist", None)
        specialist_value = getattr(specialist, "value", specialist) if specialist is not None else None
        agent_id = getattr(decision, "agent_id", None) or (
            f"{str(agent_role_value).lower()}:{specialist_value}" if specialist_value else str(agent_role_value).lower()
        )
        return {
            "agent_type": str(agent_role_value).upper(),
            "agent_role": str(agent_role_value).lower(),
            "agent_id": str(agent_id).lower(),
            "specialist": specialist_value,
            "task": getattr(decision, "task", ""),
        }