"""Delegation contracts for Orchestrator → Agent task management.

Defines the schemas that track every delegation from the Orchestrator
to a specialized agent: task formulation, agent session lifecycle,
context continuity decisions, and delegation audit log.

These schemas enforce the Orchestrator's contract: structured input,
structured output, tracked sessions, and context governance.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from mindflow_backend.schemas.orchestration.orchestrator import AgentType, Priority, ToolScope
from mindflow_backend.schemas.orchestration.specialists import SpecialistType

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DelegationStatus(StrEnum):
    """Lifecycle status of a delegated task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ContextContinuity(StrEnum):
    """How the agent's context window should be handled."""

    MAINTAIN = "maintain"       # Reuse existing context window
    FRESH = "fresh"             # Start new context window
    CARRY_SUMMARY = "carry_summary"  # Fresh window with summary from previous


class AgentSessionStatus(StrEnum):
    """Lifecycle status of an agent's context window."""

    CREATED = "created"
    MAINTAINED = "maintained"
    RECYCLED = "recycled"
    CLOSED = "closed"


# ---------------------------------------------------------------------------
# Delegation Task — what the Orchestrator sends to an agent
# ---------------------------------------------------------------------------


class DelegationTask(BaseModel):
    """A precise task formulated by the Orchestrator for a specific agent.

    This is the contract between Orchestrator and Agent. Every delegation
    MUST go through this schema — no free-form task descriptions.
    """

    task_id: UUID = Field(default_factory=uuid4)
    agent: AgentType
    agent_role: AgentType | None = None
    specialist: SpecialistType | None = None
    agent_id: str | None = None
    objective: str = Field(
        description="One clear sentence: what must the agent accomplish.",
    )
    scope: list[str] = Field(
        default_factory=list,
        description=(
            "Explicit boundaries: files, modules, or areas to focus on. "
            "Empty means agent decides scope within its constraints."
        ),
    )
    exclusions: list[str] = Field(
        default_factory=list,
        description="Explicit out-of-scope areas the agent must NOT touch.",
    )
    expected_output: str = Field(
        default="",
        description=(
            "What structure the response should have. "
            "e.g., 'Return a list of public functions with signatures and deps.'"
        ),
    )
    context_from_session: str = Field(
        default="",
        description=(
            "Relevant findings from previous delegations that this agent "
            "needs to know. Compressed, structured context — never raw code."
        ),
    )
    priority: Priority = Priority.NORMAL
    tools: list[ToolScope] = Field(default_factory=list)
    root_dir: str | None = Field(
        default=None,
        description="Working directory for filesystem tools (propagated from the calling orchestrator).",
    )
    context_continuity: ContextContinuity = ContextContinuity.MAINTAIN
    max_iterations: int = Field(
        default=1,
        ge=1,
        le=100,
        description="How many iteration rounds the agent may perform.",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def model_post_init(self, __context) -> None:
        if self.agent_role is None:
            self.agent_role = self.agent
        self.agent = self.agent_role
        if self.agent_id is None:
            if self.specialist is None:
                self.agent_id = self.agent_role.value
            else:
                self.agent_id = f"{self.agent_role.value}:{self.specialist.value}"


# ---------------------------------------------------------------------------
# Delegation Result — what comes back from the agent
# ---------------------------------------------------------------------------


class DelegationResult(BaseModel):
    """Structured result returned by an agent after completing a delegation.

    The Orchestrator integrates ``key_findings`` into its context and
    discards the rest. ``full_output`` is stored for audit but does NOT
    enter the Orchestrator's context window.
    """

    task_id: UUID = Field(description="References the originating DelegationTask.")
    agent: AgentType
    agent_role: AgentType | None = None
    specialist: SpecialistType | None = None
    agent_id: str | None = None
    status: DelegationStatus
    key_findings: str = Field(
        description=(
            "Compressed, structured summary of results. "
            "This is what enters the Orchestrator's context."
        ),
    )
    full_output: str = Field(
        default="",
        description=(
            "Complete agent response. Stored for audit, "
            "NOT integrated into Orchestrator context."
        ),
    )
    files_analyzed: list[str] = Field(default_factory=list)
    symbols_found: list[str] = Field(default_factory=list)
    gaps_detected: list[str] = Field(
        default_factory=list,
        description="Missing info, ambiguities, or unresolved questions.",
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Agent's self-assessed confidence in the findings.",
    )
    tokens_consumed: int = Field(
        default=0,
        ge=0,
        description="Approximate token cost of this delegation.",
    )
    error_message: str = Field(
        default="",
        description="Error details if status is FAILED.",
    )
    completed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def model_post_init(self, __context) -> None:
        if self.agent_role is None:
            self.agent_role = self.agent
        self.agent = self.agent_role
        if self.agent_id is None:
            if self.specialist is None:
                self.agent_id = self.agent_role.value
            else:
                self.agent_id = f"{self.agent_role.value}:{self.specialist.value}"


# ---------------------------------------------------------------------------
# Agent Session — context window lifecycle tracking
# ---------------------------------------------------------------------------


class AgentSession(BaseModel):
    """Tracks a single agent's context window lifecycle within a session.

    Each agent may have multiple AgentSessions across a conversation
    (e.g., when context is recycled). The Orchestrator uses this to
    decide whether to MAINTAIN or create a FRESH context window.
    """

    session_id: UUID = Field(default_factory=uuid4)
    orchestrator_session_id: UUID = Field(
        description="The parent Orchestrator session this belongs to.",
    )
    agent: AgentType
    status: AgentSessionStatus = AgentSessionStatus.CREATED
    delegation_count: int = Field(
        default=0,
        ge=0,
        description="Number of delegations executed in this context window.",
    )
    topic_coherence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description=(
            "How coherent the delegations in this window are. "
            "Drops when topic shifts are detected."
        ),
    )
    context_summary: str = Field(
        default="",
        description=(
            "Compressed summary of this agent session's findings. "
            "Used for carry-over when recycling context."
        ),
    )
    delegations: list[UUID] = Field(
        default_factory=list,
        description="Task IDs of all delegations in this session.",
    )
    tokens_total: int = Field(
        default=0,
        ge=0,
        description="Total tokens consumed across all delegations.",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    closed_at: datetime | None = None

    def should_recycle(self, max_delegations: int = 5) -> bool:
        """Whether this session's context should be recycled.

        Returns True if delegation count exceeds threshold or
        topic coherence has dropped below acceptable level.
        """
        return (
            self.delegation_count >= max_delegations
            or self.topic_coherence < 0.3
        )


# ---------------------------------------------------------------------------
# Delegation Log Entry — audit trail
# ---------------------------------------------------------------------------


class DelegationLogEntry(BaseModel):
    """Single entry in the Orchestrator's delegation audit log.

    The Orchestrator maintains this log as a lightweight record of
    all delegations in the session. Used for self-evaluation and
    context governance decisions.
    """

    task_id: UUID
    agent: AgentType
    objective: str
    status: DelegationStatus
    key_findings_summary: str = Field(
        default="",
        description="One-line summary of key findings (ultra-compressed).",
    )
    tokens_consumed: int = 0
    context_continuity: ContextContinuity = ContextContinuity.MAINTAIN
    agent_session_id: UUID | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Orchestrator Session — top-level session state
# ---------------------------------------------------------------------------


class OrchestratorSession(BaseModel):
    """Top-level session state maintained by the Orchestrator.

    This is the Orchestrator's view of the entire conversation: user
    intent, active tasks, agent sessions, and the delegation log.
    """

    session_id: UUID = Field(default_factory=uuid4)
    user_intent: str = Field(
        default="",
        description="Current interpreted user intent / objective.",
    )
    active_delegations: list[UUID] = Field(
        default_factory=list,
        description="Task IDs of currently in-progress delegations.",
    )
    agent_sessions: dict[str, UUID] = Field(
        default_factory=dict,
        description=(
            "Map of AgentType value → current AgentSession ID. "
            "Tracks which context window each agent is using."
        ),
    )
    delegation_log: list[DelegationLogEntry] = Field(
        default_factory=list,
        description="Ordered audit trail of all delegations.",
    )
    session_checkpoints: list[str] = Field(
        default_factory=list,
        description=(
            "Compressed checkpoint summaries created at natural boundaries. "
            "Used for context recovery."
        ),
    )
    total_tokens_consumed: int = Field(
        default=0,
        ge=0,
        description="Total tokens across all delegations in this session.",
    )
    total_delegations: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
