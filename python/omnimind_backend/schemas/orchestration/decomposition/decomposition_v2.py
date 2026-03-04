"""Decomposition Thinking v2 schemas.

Extends the Phase 3 DT contracts with MainComponent, SubComponent,
state management, scoring, and synthesis contracts as specified in
decomposition-thinking-contracts-v2.md.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SynthesisStrategy(StrEnum):
    """How validated sub-components are combined."""

    SEQUENTIAL_MERGE = "sequential_merge"
    PARALLEL_MERGE = "parallel_merge"
    HIERARCHICAL_MERGE = "hierarchical_merge"


class ComponentOwner(StrEnum):
    """Agent type that owns a component."""

    CODER = "coder"
    ANALYST = "analyst"
    RESEARCHER = "researcher"
    ARCH_TECH = "arch_tech"
    CRITIC = "critic"


class ComponentStatus(StrEnum):
    """State machine for sub-component lifecycle."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    BLOCKED = "BLOCKED"
    DONE = "DONE"
    VALIDATED = "VALIDATED"


class DTMode(StrEnum):
    """Orchestrator mode selection."""

    NORMAL = "NORMAL"
    DT = "DT"


# ---------------------------------------------------------------------------
# Core contracts
# ---------------------------------------------------------------------------


class MainComponentContract(BaseModel):
    """Top-level DT contract defining the overall task goal."""

    main_component_id: UUID
    goal: str
    success_criteria: list[str] = Field(default_factory=list)
    global_constraints: list[str] = Field(default_factory=list)
    target_confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    synthesis_strategy: SynthesisStrategy = SynthesisStrategy.SEQUENTIAL_MERGE


class SubComponentContract(BaseModel):
    """A decomposed sub-task within a DT session."""

    component_id: UUID
    parent_id: UUID
    title: str
    scope: str
    dependencies: list[UUID] = Field(default_factory=list)
    context_boundary: str = ""
    allowed_inputs: list[str] = Field(default_factory=list)
    forbidden_inputs: list[str] = Field(default_factory=list)
    expected_artifacts: list[str] = Field(default_factory=list)
    owner_agent: ComponentOwner
    priority: Literal["low", "medium", "high"] = "medium"


# ---------------------------------------------------------------------------
# State & evidence
# ---------------------------------------------------------------------------


class ComponentEvidence(BaseModel):
    """Validation evidence collected during component execution."""

    tests_passed: int = 0
    tests_total: int = 0
    lint_passed: bool = False
    checks: list[str] = Field(default_factory=list)
    agent_notes: str = ""


class SubComponentState(BaseModel):
    """Runtime state of a sub-component during DT execution."""

    component_id: UUID
    state: ComponentStatus = ComponentStatus.PENDING
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: ComponentEvidence | None = None
    last_checkpoint_at: datetime | None = None
    resume_instructions: str | None = None
    iteration_count: int = 0
    max_iterations: int = 3


# ---------------------------------------------------------------------------
# Synthesis & decision
# ---------------------------------------------------------------------------


class ValidatedComponent(BaseModel):
    """A sub-component that passed validation."""

    component_id: UUID
    title: str
    summary: str
    artifacts: list[str] = Field(default_factory=list)
    score: float = Field(ge=0.0, le=1.0)


class ConsistencyCheck(BaseModel):
    """A global consistency check across components."""

    check_name: str
    passed: bool
    details: str


class SynthesisContract(BaseModel):
    """Full synthesis result combining all validated components."""

    session_id: UUID
    main_component_id: UUID
    validated_components: list[ValidatedComponent] = Field(default_factory=list)
    global_consistency_checks: list[ConsistencyCheck] = Field(default_factory=list)
    final_answer: str = ""
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    open_risks: list[str] = Field(default_factory=list)


class DTDecision(BaseModel):
    """Orchestrator's mode selection output."""

    mode: DTMode
    reason: str
    complexity_score: float = Field(ge=0.0, le=1.0)
    estimated_components: int = Field(ge=1)
