"""Core Orchestrator interface.

Defines the fundamental contract for orchestrator implementations,
including routing, decision making, session management, and complexity
evaluation based on orchestrator.py and delegation.py schemas.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from omnimind_backend.schemas.chat.agent import AgentChatRequest
from omnimind_backend.schemas.orchestration.delegation import (
    AgentSession,
    DelegationTask,
    OrchestratorSession,
)
from omnimind_backend.schemas.orchestration.orchestrator import (
    OrchestratorDecision,
)


@runtime_checkable
class OrchestratorCoreContract(Protocol):
    """Core contract for orchestrator implementations.
    
    Defines the fundamental operations that every orchestrator must
    support to route requests, make decisions, manage sessions, and
    evaluate task complexity.
    """

    async def route_request(self, request: AgentChatRequest) -> OrchestratorDecision:
        """Route an incoming chat request to the appropriate agent.
        
        Args:
            request: The incoming chat request from user.
            
        Returns:
            Complete routing decision with agent selection and configuration.
        """
        ...

    async def make_decision(self, context: dict) -> OrchestratorDecision:
        """Make an agent routing decision based on context.
        
        Args:
            context: Context information including user intent, history, etc.
            
        Returns:
            Decision with selected agent and execution parameters.
        """
        ...

    async def manage_session(self, session_id: UUID) -> OrchestratorSession:
        """Manage and update orchestrator session state.
        
        Args:
            session_id: Unique session identifier.
            
        Returns:
            Updated orchestrator session with current state.
        """
        ...

    async def evaluate_complexity(self, request: str) -> float:
        """Evaluate the complexity of a user request.
        
        Args:
            request: The user's request text.
            
        Returns:
            Complexity score between 0.0 (simple) and 1.0 (complex).
        """
        ...

    async def create_delegation_task(
        self,
        decision: OrchestratorDecision,
        session_id: UUID,
        context_summary: str = "",
    ) -> DelegationTask:
        """Create a delegation task from an orchestrator decision.
        
        Args:
            decision: The routing decision.
            session_id: Current session identifier.
            context_summary: Summary of relevant context.
            
        Returns:
            Formatted delegation task for agent execution.
        """
        ...

    async def process_delegation_result(
        self,
        result: dict,
        session_id: UUID,
    ) -> None:
        """Process and integrate a delegation result.
        
        Args:
            result: Result returned by delegated agent.
            session_id: Session for context integration.
        """
        ...

    async def should_use_decomposition_thinking(
        self,
        complexity_score: float,
        request: str,
    ) -> bool:
        """Determine if Decomposition Thinking should be used.
        
        Args:
            complexity_score: Evaluated complexity (0-1).
            request: Original user request.
            
        Returns:
            True if DT mode should be activated.
        """
        ...

    async def get_agent_session(
        self,
        agent_type: str,
        session_id: UUID,
    ) -> AgentSession | None:
        """Get or create an agent session for context management.
        
        Args:
            agent_type: Type of agent (coder, analyst, etc.).
            session_id: Orchestrator session identifier.
            
        Returns:
            Agent session for context window management.
        """
        ...

    async def update_agent_session(
        self,
        session: AgentSession,
        delegation_result: dict,
    ) -> AgentSession:
        """Update agent session after delegation completion.
        
        Args:
            session: Current agent session.
            delegation_result: Result from the delegation.
            
        Returns:
            Updated agent session with new state.
        """
        ...
