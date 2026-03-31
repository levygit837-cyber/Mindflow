"""
SubTeamConfig — Configuration for sub-team behavior.

Immutable dataclass that defines how a sub-team should be spawned and executed.
Used by SubTeamLauncher to enforce constraints on model tier, team size,
timeout, and orchestration phases.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SubTeamConfig:
    """Configuration for sub-team spawning and execution.

    Attributes:
        model_tier: Model tier to use for sub-agents ("tier-2", "fast", "cheap").
                   Tier-2 models (GPT-4o-mini, Claude Haiku) provide cost control.
        max_agents: Maximum number of sub-agents in the team (2-5).
        timeout_seconds: Maximum execution time for the sub-team (≤60s).
        skip_discussion: Whether to skip Discussion phase (always True for sub-teams).
        min_agents: Minimum number of sub-agents required (default: 2).

    Constraints:
        - max_agents must be between 2 and 5
        - timeout_seconds must be ≤ 60.0
        - skip_discussion should always be True for sub-teams
    """

    model_tier: str = "tier-2"
    max_agents: int = 3
    timeout_seconds: float = 60.0
    skip_discussion: bool = True
    min_agents: int = 2

    def __post_init__(self) -> None:
        """Validate configuration constraints."""
        if self.max_agents < 2 or self.max_agents > 5:
            raise ValueError(
                f"max_agents must be between 2 and 5, got {self.max_agents}"
            )

        if self.min_agents < 2:
            raise ValueError(f"min_agents must be at least 2, got {self.min_agents}")

        if self.min_agents > self.max_agents:
            raise ValueError(
                f"min_agents ({self.min_agents}) cannot exceed max_agents ({self.max_agents})"
            )

        if self.timeout_seconds > 60.0:
            raise ValueError(
                f"timeout_seconds must be ≤ 60.0 for sub-teams, got {self.timeout_seconds}"
            )

        if self.timeout_seconds <= 0:
            raise ValueError(
                f"timeout_seconds must be positive, got {self.timeout_seconds}"
            )

        if self.model_tier not in ("tier-2", "fast", "cheap"):
            raise ValueError(
                f"model_tier must be 'tier-2', 'fast', or 'cheap', got '{self.model_tier}'"
            )


# Predefined configurations for common use cases
RESEARCHER_SUB_TEAM_CONFIG = SubTeamConfig(
    model_tier="tier-2",
    max_agents=3,
    timeout_seconds=45.0,
    skip_discussion=True,
    min_agents=2,
)

ANALYST_SUB_TEAM_CONFIG = SubTeamConfig(
    model_tier="tier-2",
    max_agents=3,
    timeout_seconds=50.0,
    skip_discussion=True,
    min_agents=2,
)

CODER_SUB_TEAM_CONFIG = SubTeamConfig(
    model_tier="tier-2",
    max_agents=3,
    timeout_seconds=60.0,
    skip_discussion=True,
    min_agents=3,  # Architect + Writer + Reviewer
)
