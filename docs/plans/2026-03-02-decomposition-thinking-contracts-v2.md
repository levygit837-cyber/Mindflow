# Decomposition Thinking Contracts v2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Evolve the existing DT pipeline from simple DTTask/DTSession to the full v2 contract set with MainComponent, SubComponent, state machine, score formula, and validation loop.

**Architecture:** Adds new Pydantic v2 schemas alongside existing `schemas/decomposition.py`, then progressively refactors the decomposer, resolver, and synthesizer to use the new contracts. Existing DTTask/DTSession remain as backward-compatible aliases during migration.

**Tech Stack:** Python 3.12, Pydantic v2, LangGraph, pytest, existing `orchestrator/decomposition/` pipeline

---

## Task 1: Add v2 Core Schemas — MainComponentContract and SubComponentContract

**Files:**
- Create: `python/omnimind_backend/schemas/decomposition_v2.py`
- Test: `python/tests/test_decomposition_v2_schemas.py`

**Step 1: Write the failing test**

Create `python/tests/test_decomposition_v2_schemas.py`:

```python
"""Tests for Decomposition Thinking v2 schemas."""

from uuid import uuid4

from omnimind_backend.schemas.decomposition_v2 import (
    MainComponentContract,
    SubComponentContract,
    SynthesisStrategy,
    ComponentOwner,
)


def test_main_component_creation() -> None:
    mc = MainComponentContract(
        main_component_id=uuid4(),
        goal="Refactor authentication module",
        success_criteria=["All auth tests pass", "No regression in login flow"],
        global_constraints=["Must be backward-compatible"],
    )
    assert mc.target_confidence == 0.85
    assert mc.synthesis_strategy == SynthesisStrategy.SEQUENTIAL_MERGE


def test_sub_component_creation() -> None:
    parent_id = uuid4()
    sc = SubComponentContract(
        component_id=uuid4(),
        parent_id=parent_id,
        title="Extract JWT validation",
        scope="Move JWT logic to dedicated module",
        owner_agent=ComponentOwner.CODER,
    )
    assert sc.priority == "medium"
    assert sc.dependencies == []


def test_component_owner_values() -> None:
    assert ComponentOwner.CODER == "coder"
    assert ComponentOwner.ANALYST == "analyst"
    assert ComponentOwner.RESEARCHER == "researcher"
    assert ComponentOwner.ARCH_TECH == "arch_tech"
    assert ComponentOwner.CRITIC == "critic"
```

**Step 2: Run test to verify it fails**

Run: `cd python && python -m pytest tests/test_decomposition_v2_schemas.py::test_main_component_creation -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `python/omnimind_backend/schemas/decomposition_v2.py`:

```python
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
```

**Step 4: Run test to verify it passes**

Run: `cd python && python -m pytest tests/test_decomposition_v2_schemas.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python/omnimind_backend/schemas/decomposition_v2.py python/tests/test_decomposition_v2_schemas.py
git commit -m "feat(schemas): add DT v2 MainComponentContract and SubComponentContract"
```

---

## Task 2: Add SubComponentState and ComponentEvidence

**Files:**
- Modify: `python/omnimind_backend/schemas/decomposition_v2.py`
- Test: `python/tests/test_decomposition_v2_schemas.py` (extend)

**Step 1: Write the failing test**

Append to `python/tests/test_decomposition_v2_schemas.py`:

```python
from omnimind_backend.schemas.decomposition_v2 import (
    SubComponentState,
    ComponentEvidence,
    ComponentStatus,
)


def test_component_status_values() -> None:
    assert ComponentStatus.PENDING == "PENDING"
    assert ComponentStatus.IN_PROGRESS == "IN_PROGRESS"
    assert ComponentStatus.PAUSED == "PAUSED"
    assert ComponentStatus.BLOCKED == "BLOCKED"
    assert ComponentStatus.DONE == "DONE"
    assert ComponentStatus.VALIDATED == "VALIDATED"


def test_sub_component_state_defaults() -> None:
    state = SubComponentState(component_id=uuid4())
    assert state.state == ComponentStatus.PENDING
    assert state.progress == 0.0
    assert state.iteration_count == 0
    assert state.max_iterations == 3


def test_component_evidence() -> None:
    ev = ComponentEvidence(
        tests_passed=8,
        tests_total=10,
        lint_passed=True,
        checks=["type check passed"],
        agent_notes="Minor type issues remain",
    )
    assert ev.tests_passed == 8
    assert ev.lint_passed is True


def test_state_with_evidence() -> None:
    state = SubComponentState(
        component_id=uuid4(),
        state=ComponentStatus.DONE,
        progress=1.0,
        evidence=ComponentEvidence(tests_passed=5, tests_total=5, lint_passed=True),
    )
    assert state.evidence is not None
    assert state.evidence.tests_passed == 5
```

**Step 2: Run test to verify it fails**

Run: `cd python && python -m pytest tests/test_decomposition_v2_schemas.py::test_component_status_values -v`
Expected: FAIL with `ImportError`

**Step 3: Write minimal implementation**

Add to `python/omnimind_backend/schemas/decomposition_v2.py`:

```python
class ComponentStatus(StrEnum):
    """State machine for sub-component lifecycle."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    BLOCKED = "BLOCKED"
    DONE = "DONE"
    VALIDATED = "VALIDATED"


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
```

**Step 4: Run test to verify it passes**

Run: `cd python && python -m pytest tests/test_decomposition_v2_schemas.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python/omnimind_backend/schemas/decomposition_v2.py python/tests/test_decomposition_v2_schemas.py
git commit -m "feat(schemas): add SubComponentState and ComponentEvidence for DT v2"
```

---

## Task 3: Add SynthesisContract and DTDecision

**Files:**
- Modify: `python/omnimind_backend/schemas/decomposition_v2.py`
- Test: `python/tests/test_decomposition_v2_schemas.py` (extend)

**Step 1: Write the failing test**

Append to `python/tests/test_decomposition_v2_schemas.py`:

```python
from omnimind_backend.schemas.decomposition_v2 import (
    SynthesisContract,
    ValidatedComponent,
    ConsistencyCheck,
    DTDecision,
    DTMode,
)


def test_validated_component() -> None:
    vc = ValidatedComponent(
        component_id=uuid4(),
        title="JWT extraction",
        summary="Moved JWT validation to auth/jwt.py",
        artifacts=["auth/jwt.py", "tests/test_jwt.py"],
        score=0.92,
    )
    assert vc.score >= 0.85


def test_consistency_check() -> None:
    cc = ConsistencyCheck(check_name="import_consistency", passed=True, details="All imports resolve")
    assert cc.passed is True


def test_synthesis_contract() -> None:
    sc = SynthesisContract(
        session_id=uuid4(),
        main_component_id=uuid4(),
        validated_components=[
            ValidatedComponent(component_id=uuid4(), title="A", summary="done", artifacts=[], score=0.9),
        ],
        global_consistency_checks=[
            ConsistencyCheck(check_name="no_conflicts", passed=True, details="ok"),
        ],
        final_answer="Refactoring complete.",
        overall_confidence=0.88,
    )
    assert sc.overall_confidence >= 0.85
    assert len(sc.validated_components) == 1


def test_dt_decision_normal() -> None:
    d = DTDecision(mode=DTMode.NORMAL, reason="Simple task", complexity_score=0.3, estimated_components=1)
    assert d.mode == DTMode.NORMAL


def test_dt_decision_triggers_dt() -> None:
    d = DTDecision(mode=DTMode.DT, reason="Multi-file refactor", complexity_score=0.75, estimated_components=4)
    assert d.complexity_score >= 0.65
    assert d.mode == DTMode.DT
```

**Step 2: Run test to verify it fails**

Run: `cd python && python -m pytest tests/test_decomposition_v2_schemas.py::test_dt_decision_normal -v`
Expected: FAIL with `ImportError`

**Step 3: Write minimal implementation**

Add to `python/omnimind_backend/schemas/decomposition_v2.py`:

```python
class DTMode(StrEnum):
    """Orchestrator mode selection."""

    NORMAL = "NORMAL"
    DT = "DT"


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
```

**Step 4: Run test to verify it passes**

Run: `cd python && python -m pytest tests/test_decomposition_v2_schemas.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python/omnimind_backend/schemas/decomposition_v2.py python/tests/test_decomposition_v2_schemas.py
git commit -m "feat(schemas): add SynthesisContract and DTDecision for DT v2"
```

---

## Task 4: Component Score Formula

**Files:**
- Create: `python/omnimind_backend/orchestrator/decomposition/scoring.py`
- Test: `python/tests/test_dt_scoring.py`

**Step 1: Write the failing test**

Create `python/tests/test_dt_scoring.py`:

```python
"""Tests for DT v2 component scoring."""

from uuid import uuid4

from omnimind_backend.orchestrator.decomposition.scoring import compute_component_score
from omnimind_backend.schemas.decomposition_v2 import (
    ComponentEvidence,
    SubComponentState,
    ComponentStatus,
)


def test_perfect_score() -> None:
    state = SubComponentState(
        component_id=uuid4(),
        state=ComponentStatus.DONE,
        progress=1.0,
        evidence=ComponentEvidence(tests_passed=10, tests_total=10, lint_passed=True),
    )
    score = compute_component_score(state, consistency=1.0, agent_confidence=1.0)
    assert score == 1.0


def test_zero_score() -> None:
    state = SubComponentState(component_id=uuid4())
    score = compute_component_score(state, consistency=0.0, agent_confidence=0.0)
    assert score == 0.0


def test_validation_threshold() -> None:
    state = SubComponentState(
        component_id=uuid4(),
        state=ComponentStatus.DONE,
        progress=0.9,
        evidence=ComponentEvidence(tests_passed=8, tests_total=10, lint_passed=True),
    )
    score = compute_component_score(state, consistency=0.8, agent_confidence=0.7)
    # 0.35*0.9 + 0.35*0.85 + 0.20*0.8 + 0.10*0.7 = 0.315+0.2975+0.16+0.07 = 0.8425
    assert 0.80 < score < 0.90


def test_partial_evidence_scoring() -> None:
    state = SubComponentState(
        component_id=uuid4(),
        state=ComponentStatus.DONE,
        progress=0.5,
        evidence=ComponentEvidence(tests_passed=0, tests_total=5, lint_passed=False),
    )
    score = compute_component_score(state, consistency=0.5, agent_confidence=0.3)
    assert score < 0.85  # Should NOT pass validation
```

**Step 2: Run test to verify it fails**

Run: `cd python && python -m pytest tests/test_dt_scoring.py -v`
Expected: FAIL with `ImportError`

**Step 3: Write minimal implementation**

Create `python/omnimind_backend/orchestrator/decomposition/scoring.py`:

```python
"""DT v2 component scoring.

Implements the score formula from decomposition-thinking-contracts-v2.md:
score = 0.35 * progress + 0.35 * validation_objective + 0.20 * consistency + 0.10 * agent_confidence
"""

from __future__ import annotations

from omnimind_backend.schemas.decomposition_v2 import SubComponentState

VALIDATION_THRESHOLD = 0.85

# Score weights
W_PROGRESS = 0.35
W_VALIDATION = 0.35
W_CONSISTENCY = 0.20
W_CONFIDENCE = 0.10


def _compute_validation_objective(state: SubComponentState) -> float:
    """Compute validation_objective from evidence."""
    if state.evidence is None:
        return 0.0

    ev = state.evidence
    test_ratio = ev.tests_passed / ev.tests_total if ev.tests_total > 0 else 0.0
    lint_score = 1.0 if ev.lint_passed else 0.0
    # Weighted: 70% test ratio + 30% lint
    return 0.7 * test_ratio + 0.3 * lint_score


def compute_component_score(
    state: SubComponentState,
    consistency: float,
    agent_confidence: float,
) -> float:
    """Compute the composite score for a DT sub-component.

    Args:
        state: Current component state with progress and evidence.
        consistency: Output compatibility with dependent components (0-1).
        agent_confidence: Agent's self-reported confidence (0-1).

    Returns:
        Composite score (0-1). >= 0.85 means VALIDATED.
    """
    validation_obj = _compute_validation_objective(state)

    score = (
        W_PROGRESS * state.progress
        + W_VALIDATION * validation_obj
        + W_CONSISTENCY * consistency
        + W_CONFIDENCE * agent_confidence
    )
    return round(min(max(score, 0.0), 1.0), 4)


def is_validated(score: float) -> bool:
    """Check if a score passes the validation threshold."""
    return score >= VALIDATION_THRESHOLD
```

**Step 4: Run test to verify it passes**

Run: `cd python && python -m pytest tests/test_dt_scoring.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python/omnimind_backend/orchestrator/decomposition/scoring.py python/tests/test_dt_scoring.py
git commit -m "feat(dt): add v2 component score formula with validation threshold"
```

---

## Task 5: Agent-to-Component Routing Map

**Files:**
- Create: `python/omnimind_backend/orchestrator/decomposition/component_router.py`
- Test: `python/tests/test_dt_component_router.py`

**Step 1: Write the failing test**

Create `python/tests/test_dt_component_router.py`:

```python
"""Tests for DT v2 component-to-agent routing."""

from omnimind_backend.orchestrator.decomposition.component_router import (
    get_agent_for_component,
    ComponentType,
)
from omnimind_backend.schemas.decomposition_v2 import ComponentOwner


def test_code_implementation_routes_to_coder() -> None:
    assert get_agent_for_component(ComponentType.CODE_IMPLEMENTATION) == ComponentOwner.CODER


def test_architecture_routes_to_arch_tech() -> None:
    assert get_agent_for_component(ComponentType.ARCHITECTURE_DESIGN) == ComponentOwner.ARCH_TECH


def test_code_analysis_routes_to_analyst() -> None:
    assert get_agent_for_component(ComponentType.CODE_ANALYSIS) == ComponentOwner.ANALYST


def test_external_research_routes_to_researcher() -> None:
    assert get_agent_for_component(ComponentType.EXTERNAL_RESEARCH) == ComponentOwner.RESEARCHER


def test_quality_review_routes_to_critic() -> None:
    assert get_agent_for_component(ComponentType.QUALITY_REVIEW) == ComponentOwner.CRITIC


def test_fallback_for_architecture() -> None:
    from omnimind_backend.orchestrator.decomposition.component_router import get_fallback_agent
    assert get_fallback_agent(ComponentType.ARCHITECTURE_DESIGN) == ComponentOwner.ANALYST


def test_no_fallback_for_coder() -> None:
    from omnimind_backend.orchestrator.decomposition.component_router import get_fallback_agent
    assert get_fallback_agent(ComponentType.CODE_IMPLEMENTATION) is None
```

**Step 2: Run test to verify it fails**

Run: `cd python && python -m pytest tests/test_dt_component_router.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `python/omnimind_backend/orchestrator/decomposition/component_router.py`:

```python
"""DT v2 component-to-agent routing.

Maps component types to primary and fallback agent types as specified in
decomposition-thinking-contracts-v2.md.
"""

from __future__ import annotations

from enum import StrEnum

from omnimind_backend.schemas.decomposition_v2 import ComponentOwner


class ComponentType(StrEnum):
    """Types of work a DT component can represent."""

    CODE_IMPLEMENTATION = "code_implementation"
    ARCHITECTURE_DESIGN = "architecture_design"
    CODE_ANALYSIS = "code_analysis"
    EXTERNAL_RESEARCH = "external_research"
    QUALITY_REVIEW = "quality_review"
    SECURITY_ASSESSMENT = "security_assessment"


_PRIMARY_AGENT: dict[ComponentType, ComponentOwner] = {
    ComponentType.CODE_IMPLEMENTATION: ComponentOwner.CODER,
    ComponentType.ARCHITECTURE_DESIGN: ComponentOwner.ARCH_TECH,
    ComponentType.CODE_ANALYSIS: ComponentOwner.ANALYST,
    ComponentType.EXTERNAL_RESEARCH: ComponentOwner.RESEARCHER,
    ComponentType.QUALITY_REVIEW: ComponentOwner.CRITIC,
    ComponentType.SECURITY_ASSESSMENT: ComponentOwner.CRITIC,
}

_FALLBACK_AGENT: dict[ComponentType, ComponentOwner | None] = {
    ComponentType.CODE_IMPLEMENTATION: None,
    ComponentType.ARCHITECTURE_DESIGN: ComponentOwner.ANALYST,
    ComponentType.CODE_ANALYSIS: ComponentOwner.CODER,
    ComponentType.EXTERNAL_RESEARCH: None,
    ComponentType.QUALITY_REVIEW: ComponentOwner.ANALYST,
    ComponentType.SECURITY_ASSESSMENT: ComponentOwner.ANALYST,
}


def get_agent_for_component(component_type: ComponentType) -> ComponentOwner:
    """Return the primary agent for a given component type."""
    return _PRIMARY_AGENT[component_type]


def get_fallback_agent(component_type: ComponentType) -> ComponentOwner | None:
    """Return the fallback agent, or None if no fallback is available."""
    return _FALLBACK_AGENT.get(component_type)
```

**Step 4: Run test to verify it passes**

Run: `cd python && python -m pytest tests/test_dt_component_router.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python/omnimind_backend/orchestrator/decomposition/component_router.py python/tests/test_dt_component_router.py
git commit -m "feat(dt): add v2 component-to-agent routing with fallbacks"
```

---

## Task 6: Full Regression Check

**Step 1: Run the full test suite**

Run: `cd python && python -m pytest tests/ -v --tb=short`
Expected: All tests PASS

**Step 2: Verify schema imports**

Run: `cd python && python -c "from omnimind_backend.schemas.decomposition_v2 import MainComponentContract, SubComponentContract, SubComponentState, SynthesisContract, DTDecision; print('All v2 schemas importable')"`
Expected: `All v2 schemas importable`

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | MainComponentContract + SubComponentContract | `schemas/decomposition_v2.py` |
| 2 | SubComponentState + ComponentEvidence | `schemas/decomposition_v2.py` |
| 3 | SynthesisContract + DTDecision | `schemas/decomposition_v2.py` |
| 4 | Score formula + validation threshold | `orchestrator/decomposition/scoring.py` |
| 5 | Component-to-agent routing map | `orchestrator/decomposition/component_router.py` |
| 6 | Full regression check | — |
