"""Core types for the unified execution engine.

This module defines the fundamental data structures used throughout
the execution system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from mindflow_backend.schemas.orchestration.orchestrator import (
    ExecutionStrategy,
    OrchestratorDecision,
)


class ExecutionStatus(StrEnum):
    """Status of an execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class ExecutionContext:
    """Context for a single execution.

    Contains all parameters needed to execute a task with any strategy.
    """

    # Core parameters
    decision: OrchestratorDecision
    session_id: str
    message: str

    # LLM configuration
    provider: str
    model: str

    # Optional parameters
    folder_path: str | None = None
    memory_context: str = ""
    conversation_history: list[dict[str, Any]] = field(default_factory=list)

    # Execution control
    max_iterations: int = 1000
    timeout_seconds: float = 300.0

    # Metadata
    execution_id: str | None = None
    parent_execution_id: str | None = None
    run_id: str | None = None

    @classmethod
    def from_delegation_task(
        cls,
        task: Any,  # DelegationTask
        session: Any,  # OrchestratorSession
        **kwargs: Any,
    ) -> ExecutionContext:
        """Create context from a delegation task."""
        from mindflow_backend.schemas.orchestration.orchestrator import (
            OrchestratorDecision,
        )

        decision = OrchestratorDecision(
            agent=task.agent,
            specialist=task.specialist,
            task=task.task,
            tools=task.tools or [],
            thinking=task.thinking,
            sandbox=task.sandbox,
        )

        return cls(
            decision=decision,
            session_id=session.session_id,
            message=task.task,
            provider=kwargs.get("provider", ""),
            model=kwargs.get("model", ""),
            folder_path=kwargs.get("folder_path"),
            execution_id=kwargs.get("execution_id"),
            parent_execution_id=kwargs.get("parent_execution_id"),
        )


@dataclass
class ExecutionState:
    """Mutable state tracked during execution.

    This is updated as the execution progresses.
    """

    status: ExecutionStatus = ExecutionStatus.PENDING
    current_iteration: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None

    # Accumulated data
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    # Team-specific state
    team_id: str | None = None
    mission_dag: Any = None  # MissionDAG
    mission_results: list[Any] = field(default_factory=list)

    def mark_started(self) -> None:
        """Mark execution as started."""
        self.status = ExecutionStatus.RUNNING
        self.start_time = datetime.now()

    def mark_completed(self) -> None:
        """Mark execution as completed."""
        self.status = ExecutionStatus.COMPLETED
        self.end_time = datetime.now()

    def mark_failed(self, error: str) -> None:
        """Mark execution as failed."""
        self.status = ExecutionStatus.FAILED
        self.end_time = datetime.now()
        self.errors.append(error)

    def add_tool_call(self, tool_name: str, args: dict[str, Any]) -> None:
        """Record a tool call."""
        self.tool_calls.append({
            "tool": tool_name,
            "args": args,
            "iteration": self.current_iteration,
            "timestamp": datetime.now().isoformat(),
        })

    def add_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Record an event."""
        self.events.append({
            "type": event_type,
            "data": data,
            "iteration": self.current_iteration,
            "timestamp": datetime.now().isoformat(),
        })


@dataclass
class ExecutionResult:
    """Result of an execution.

    Contains the final output and metadata about the execution.
    """

    success: bool
    response: str

    # Execution metadata
    status: ExecutionStatus
    iterations: int
    duration_seconds: float

    # Optional data
    error: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)

    # Team-specific results
    team_results: list[Any] = field(default_factory=list)
    mission_dag: Any = None

    @classmethod
    def from_state(
        cls,
        state: ExecutionState,
        response: str,
        success: bool = True,
        error: str | None = None,
    ) -> ExecutionResult:
        """Create result from execution state."""
        duration = 0.0
        if state.end_time and state.start_time:
            duration = (state.end_time - state.start_time).total_seconds()

        return cls(
            success=success,
            response=response,
            status=state.status,
            iterations=state.current_iteration,
            duration_seconds=duration,
            error=error,
            tool_calls=state.tool_calls,
            events=state.events,
            team_results=state.mission_results,
            mission_dag=state.mission_dag,
        )
