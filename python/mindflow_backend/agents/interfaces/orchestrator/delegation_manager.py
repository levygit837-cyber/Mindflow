"""Delegation manager interface.

Defines the contract for managing the complete delegation lifecycle:
task creation, result tracking, session management, and audit logging
based on delegation.py schemas.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from mindflow_backend.schemas.orchestration.delegation import (
    AgentSession,
    DelegationLogEntry,
    DelegationResult,
    DelegationStatus,
    DelegationTask,
    OrchestratorSession,
)
from mindflow_backend.schemas.orchestration.orchestrator import AgentType


@runtime_checkable
class DelegationManagerContract(Protocol):
    """Contract for delegation lifecycle management.
    
    Manages the complete flow from task creation through result
    integration, including session tracking and audit logging.
    """

    async def create_delegation(
        self,
        agent: AgentType,
        objective: str,
        session_id: UUID,
        scope: list[str] | None = None,
        exclusions: list[str] | None = None,
        expected_output: str = "",
        context_from_session: str = "",
        tools: list[str] | None = None,
        max_iterations: int = 1,
    ) -> DelegationTask:
        """Create a new delegation task.
        
        Args:
            agent: Target agent type.
            objective: Clear task objective.
            session_id: Current session identifier.
            scope: In-scope areas.
            exclusions: Out-of-scope areas.
            expected_output: Expected output format.
            context_from_session: Relevant context.
            tools: Allowed tools.
            max_iterations: Maximum iteration rounds.
            
        Returns:
            Created delegation task with unique ID.
        """
        ...

    async def track_delegation_result(
        self,
        task_id: UUID,
        result: DelegationResult,
    ) -> None:
        """Track and process a delegation result.
        
        Args:
            task_id: Original task identifier.
            result: Result from agent execution.
        """
        ...

    async def get_agent_session(
        self,
        agent: AgentType,
        orchestrator_session_id: UUID,
    ) -> AgentSession:
        """Get or create an agent session for context management.
        
        Args:
            agent: Agent type.
            orchestrator_session_id: Parent session ID.
            
        Returns:
            Agent session for context window tracking.
        """
        ...

    async def update_agent_session(
        self,
        session: AgentSession,
        delegation_result: DelegationResult,
    ) -> AgentSession:
        """Update agent session after delegation completion.
        
        Args:
            session: Current agent session.
            delegation_result: Result from delegation.
            
        Returns:
            Updated session with new state and metrics.
        """
        ...

    async def should_recycle_session(
        self,
        session: AgentSession,
        max_delegations: int = 5,
    ) -> bool:
        """Determine if an agent session should be recycled.
        
        Args:
            session: Agent session to evaluate.
            max_delegations: Maximum delegations per session.
            
        Returns:
            True if session should be recycled.
        """
        ...

    async def recycle_session(
        self,
        session: AgentSession,
        carry_over_summary: str = "",
    ) -> AgentSession:
        """Recycle an agent session with context carry-over.
        
        Args:
            session: Session to recycle.
            carry_over_summary: Summary to carry over.
            
        Returns:
            New recycled session.
        """
        ...

    async def log_delegation(
        self,
        task: DelegationTask,
        result: DelegationResult,
        agent_session_id: UUID | None = None,
    ) -> DelegationLogEntry:
        """Create an audit log entry for delegation.
        
        Args:
            task: Delegation task that was executed.
            result: Result from the task.
            agent_session_id: Agent session identifier.
            
        Returns:
            Audit log entry.
        """
        ...

    async def get_delegation_history(
        self,
        session_id: UUID,
        agent: AgentType | None = None,
        limit: int = 50,
    ) -> list[DelegationLogEntry]:
        """Get delegation history for a session.
        
        Args:
            session_id: Session identifier.
            agent: Optional agent filter.
            limit: Maximum entries to return.
            
        Returns:
            Ordered list of delegation log entries.
        """
        ...

    async def calculate_session_metrics(
        self,
        session: AgentSession,
    ) -> dict[str, float]:
        """Calculate performance metrics for a session.
        
        Args:
            session: Agent session to analyze.
            
        Returns:
            Dictionary with performance metrics.
        """
        ...

    async def get_active_delegations(
        self,
        session_id: UUID,
    ) -> list[UUID]:
        """Get list of currently active delegation task IDs.
        
        Args:
            session_id: Session identifier.
            
        Returns:
            List of active task IDs.
        """
        ...

    async def cancel_delegation(
        self,
        task_id: UUID,
        reason: str = "",
    ) -> bool:
        """Cancel an active delegation.
        
        Args:
            task_id: Task identifier to cancel.
            reason: Cancellation reason.
            
        Returns:
            True if cancellation was successful.
        """
        ...
