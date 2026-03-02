"""Creative agent output schemas.

Defines the structured output contract for the Creative agent's
diverge/converge workflow as specified in agent-team-extended-contracts.md.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class CreativeWorkType(StrEnum):
    """Classification of creative work requests."""

    NEW_FEATURE = "new_feature"
    FRAMEWORK_CHANGE = "framework_change"
    REFACTORING = "refactoring"
    EXPLORATORY = "exploratory"


class PathEvaluation(BaseModel):
    """Multi-criteria evaluation for a single solution path."""

    impact: float = Field(ge=0.0, le=1.0)
    risk: float = Field(ge=0.0, le=1.0)
    effort: float = Field(ge=0.0, le=1.0)
    time_estimate: str
    reversibility: float = Field(ge=0.0, le=1.0)
    learning_potential: float = Field(ge=0.0, le=1.0)


class ExploredPath(BaseModel):
    """A single explored solution path."""

    title: str
    description: str
    evaluations: PathEvaluation


class ShortlistedPath(BaseModel):
    """A ranked path after convergence."""

    path_title: str
    composite_score: float = Field(ge=0.0, le=1.0)
    justification: str


class DiscardedPath(BaseModel):
    """A path that was explored but discarded."""

    path_title: str
    reason: str


class CreativeOutput(BaseModel):
    """Full structured output from the Creative agent workflow."""

    creative_work_type: CreativeWorkType
    explored_paths: list[ExploredPath] = Field(min_length=1)
    shortlisted_paths: list[ShortlistedPath] = Field(default_factory=list)
    discarded_paths: list[DiscardedPath] = Field(default_factory=list)
    ask_questions_used: list[str] = Field(default_factory=list)
    next_experiment: str = ""
    confidence_level: float = Field(default=0.5, ge=0.0, le=1.0)
