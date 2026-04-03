"""Agent Proposal Schema — Decentralized routing proposals.

Defines how agents propose tasks to the Orchestrator in the
decentralized routing model. Each agent evaluates the user message
and sends a proposal if it can contribute.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ProposalConfidence(StrEnum):
    """Confidence levels for agent proposals."""
    LOW = "low"           # 0.0-0.3: Can maybe help
    MEDIUM = "medium"     # 0.3-0.6: Good fit
    HIGH = "high"         # 0.6-0.8: Excellent fit
    CERTAIN = "certain"   # 0.8-1.0: Best agent for this


class AgentProposal(BaseModel):
    """A proposal from an agent indicating it can handle a task.

    When the DecentralizedRouter broadcasts a user message, each
    agent evaluates it and returns an AgentProposal if it can help.
    The Orchestrator collects proposals and decides delegation.
    """

    proposal_id: UUID = Field(
        default_factory=uuid4,
        description="Unique proposal identifier.",
    )
    agent_id: str = Field(
        ...,
        description="Agent identifier (e.g., 'coder', 'analyst', 'research').",
    )
    agent_type: str = Field(
        default="",
        description="Agent type from AgentType enum value.",
    )
    specialist: str | None = Field(
        default=None,
        description="Specialist type if applicable.",
    )

    # Confidence & Fit
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="How confident the agent is (0.0-1.0).",
    )
    confidence_level: ProposalConfidence = Field(
        default=ProposalConfidence.MEDIUM,
        description="Categorized confidence level.",
    )

    # Task Description
    suggested_task: str = Field(
        ...,
        description="What the agent proposes to do.",
    )
    reasoning: str = Field(
        default="",
        description="Why the agent thinks it's a good fit.",
    )

    # Requirements
    required_tools: list[str] = Field(
        default_factory=list,
        description="Tools the agent needs to complete the task.",
    )
    estimated_complexity: str = Field(
        default="medium",
        description="Estimated complexity: low, medium, high.",
    )
    estimated_tokens: int = Field(
        default=0,
        description="Estimated token consumption.",
    )

    # Collaboration
    can_collaborate: bool = Field(
        default=False,
        description="Whether this agent can work in parallel with others.",
    )
    needs_help_from: list[str] = Field(
        default_factory=list,
        description="Agent IDs this agent needs help from.",
    )
    can_help_with: list[str] = Field(
        default_factory=list,
        description="Agent IDs this agent can help.",
    )

    # Metadata
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Self-assigned priority (1=highest, 10=lowest).",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )

    def model_post_init(self, __context: Any) -> None:
        """Auto-categorize confidence level."""
        if self.confidence >= 0.8:
            self.confidence_level = ProposalConfidence.CERTAIN
        elif self.confidence >= 0.6:
            self.confidence_level = ProposalConfidence.HIGH
        elif self.confidence >= 0.3:
            self.confidence_level = ProposalConfidence.MEDIUM
        else:
            self.confidence_level = ProposalConfidence.LOW


class ProposalRequest(BaseModel):
    """Request sent to agents to solicit proposals.

    Broadcast via CommunicationBus when a user message arrives.
    """

    request_id: UUID = Field(
        default_factory=uuid4,
    )
    message: str = Field(
        ...,
        description="User message to evaluate.",
    )
    session_id: str = Field(
        default="",
        description="Current session ID.",
    )
    folder_path: str | None = Field(
        default=None,
        description="Working directory context.",
    )
    context_summary: str = Field(
        default="",
        description="Brief context summary for agents.",
    )
    timeout_seconds: float = Field(
        default=5.0,
        description="How long to wait for proposals.",
    )
    exclude_agents: list[str] = Field(
        default_factory=list,
        description="Agents to exclude from proposal solicitation.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )


class ProposalResponse(BaseModel):
    """Response from an agent to a proposal request."""

    request_id: UUID = Field(
        ...,
        description="ID of the ProposalRequest being answered.",
    )
    agent_id: str = Field(
        ...,
        description="Agent that is responding.",
    )
    proposal: AgentProposal | None = Field(
        default=None,
        description="The proposal if agent can help, None if declining.",
    )
    declined_reason: str = Field(
        default="",
        description="Why the agent declined (if proposal is None).",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )