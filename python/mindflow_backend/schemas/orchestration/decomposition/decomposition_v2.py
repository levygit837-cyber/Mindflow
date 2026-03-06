"""Task Thinking v2 schemas.

Extends the Phase 3 Task contracts with MainTask, SubTask,
state management, scoring, and synthesis contracts as specified in
task-thinking-contracts-v2.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
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


class TaskStatus(StrEnum):
    """State machine for sub-task lifecycle."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    BLOCKED = "BLOCKED"
    DONE = "DONE"
    VALIDATED = "VALIDATED"


class TaskMode(StrEnum):
    """Orchestrator mode selection."""

    NORMAL = "NORMAL"
    TASK = "TASK"


# ---------------------------------------------------------------------------
# Core contracts
# ---------------------------------------------------------------------------


class MainTaskContract(BaseModel):
    """Top-level Task contract defining the overall task goal."""

    main_task_id: UUID
    goal: str
    description: str = ""
    """Narrative summary: what this task is about, why it was created, what user intent it serves."""
    success_criteria: list[str] = Field(default_factory=list)
    global_constraints: list[str] = Field(default_factory=list)
    target_confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    synthesis_strategy: SynthesisStrategy = SynthesisStrategy.SEQUENTIAL_MERGE


class SubTaskContract(BaseModel):
    """A decomposed sub-task within a Task session."""

    task_id: UUID
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


class TaskEvidence(BaseModel):
    """Validation evidence collected during task execution."""

    tests_passed: int = 0
    tests_total: int = 0
    lint_passed: bool = False
    checks: list[str] = Field(default_factory=list)
    agent_notes: str = ""


class SubTaskState(BaseModel):
    """Runtime state of a sub-task during Task execution."""

    task_id: UUID
    state: TaskStatus = TaskStatus.PENDING
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: TaskEvidence | None = None
    last_checkpoint_at: datetime | None = None
    resume_instructions: str | None = None
    iteration_count: int = 0
    max_iterations: int = 3


# ---------------------------------------------------------------------------
# Synthesis & decision
# ---------------------------------------------------------------------------


class ValidatedTask(BaseModel):
    """A sub-task that passed validation."""

    task_id: UUID
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
    """Full synthesis result combining all validated tasks."""

    session_id: UUID
    main_task_id: UUID
    validated_tasks: list[ValidatedTask] = Field(default_factory=list)
    global_consistency_checks: list[ConsistencyCheck] = Field(default_factory=list)
    final_answer: str = ""
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    open_risks: list[str] = Field(default_factory=list)


class TaskDecision(BaseModel):
    """Orchestrator's mode selection output."""

    mode: TaskMode
    reason: str
    complexity_score: float = Field(ge=0.0, le=1.0)
    estimated_tasks: int = Field(ge=1)


# ---------------------------------------------------------------------------
# Task registry — used by the Orchestrator to index all MainTasks per session
# ---------------------------------------------------------------------------


class SubTaskSummary(BaseModel):
    """Lightweight summary of a SubTask for indexing purposes."""

    task_id: UUID
    title: str
    owner_agent: str
    priority: str = "medium"
    status: str = "pending"


class MainTaskSummary(BaseModel):
    """Indexed summary of a MainTask and its SubTasks.

    Stored in the SemanticContextManager task registry (in-memory, per session).
    Used by ``get_tasks()`` to give the Orchestrator a structured view of every
    MainTask decomposed in the current session, so it can retrieve content by
    MainTask or search semantically within a specific MainTask's SubTasks.
    """

    main_task_id: UUID
    goal: str
    description: str = ""
    subtasks: list[SubTaskSummary] = Field(default_factory=list)
    status: str = "in_progress"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
