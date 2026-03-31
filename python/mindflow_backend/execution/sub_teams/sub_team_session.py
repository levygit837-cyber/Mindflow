"""
SubTeamSession and SubTeamResult — State and results for sub-team execution.

SubTeamSession tracks the execution state of a sub-team (subset of TeamSession).
SubTeamResult aggregates results from multiple sub-agents for parent synthesis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from mindflow_backend.execution.sub_teams.sub_team_config import SubTeamConfig


@dataclass
class SubTeamSession:
    """Execution state for a sub-team session.

    Extends TeamSession concept but simplified for sub-team execution:
    - No Discussion phase (skip_discussion=True in config)
    - Shorter timeout (≤60s)
    - Tier-2 models for cost control
    - Depth tracking to prevent recursion

    Attributes:
        session_id: Unique identifier for this sub-team session.
        parent_agent_id: ID of the parent Specialist agent that spawned this sub-team.
        sub_team_config: Configuration for sub-team behavior.
        depth: Nesting depth (always 1 for sub-teams, prevents recursion).
        model_tier: Model tier for sub-agents ("tier-2", "fast", "cheap").
        started_at: Timestamp when sub-team execution started.
        completed_at: Timestamp when sub-team execution completed (None if running).
        sub_agent_ids: List of sub-agent IDs spawned in this session.
        metadata: Additional metadata for tracking.
    """

    session_id: str
    parent_agent_id: str
    sub_team_config: SubTeamConfig
    depth: int = 1
    model_tier: str = "tier-2"
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    sub_agent_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate session constraints."""
        if self.depth != 1:
            raise ValueError(
                f"Sub-team depth must be 1 (no recursion), got {self.depth}"
            )

        if self.model_tier not in ("tier-2", "fast", "cheap"):
            raise ValueError(
                f"model_tier must be 'tier-2', 'fast', or 'cheap', got '{self.model_tier}'"
            )

    def mark_completed(self) -> None:
        """Mark the sub-team session as completed."""
        self.completed_at = datetime.now()

    def get_duration(self) -> float:
        """Get the duration of the sub-team session in seconds."""
        if self.completed_at is None:
            return (datetime.now() - self.started_at).total_seconds()
        return (self.completed_at - self.started_at).total_seconds()


@dataclass
class SubTeamResult:
    """Aggregated results from sub-team execution.

    Combines outputs from multiple sub-agents into a single result
    that the parent Specialist agent can use for synthesis.

    Attributes:
        sub_agent_count: Total number of sub-agents spawned.
        success_count: Number of sub-agents that completed successfully.
        total_duration: Cumulative execution time across all sub-agents (seconds).
        sub_agent_results: List of individual sub-agent results.
        synthesis: Combined/synthesized output from all sub-agents.
        errors: List of errors encountered during sub-team execution.
        metadata: Additional metadata for tracking.
    """

    sub_agent_count: int
    success_count: int
    total_duration: float
    sub_agent_results: list[dict[str, Any]] = field(default_factory=list)
    synthesis: str = ""
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Calculate success rate (0.0 to 1.0)."""
        if self.sub_agent_count == 0:
            return 0.0
        return self.success_count / self.sub_agent_count

    @property
    def has_failures(self) -> bool:
        """Check if any sub-agents failed."""
        return self.success_count < self.sub_agent_count

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "sub_agent_count": self.sub_agent_count,
            "success_count": self.success_count,
            "total_duration": self.total_duration,
            "success_rate": self.success_rate,
            "has_failures": self.has_failures,
            "sub_agent_results": self.sub_agent_results,
            "synthesis": self.synthesis,
            "errors": self.errors,
            "metadata": self.metadata,
        }
