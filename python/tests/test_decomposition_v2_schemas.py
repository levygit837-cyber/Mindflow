"""Tests for Decomposition Thinking v2 schemas."""

from uuid import uuid4

from omnimind_backend.schemas.decomposition_v2 import (
    ComponentEvidence,
    ComponentOwner,
    ComponentStatus,
    ConsistencyCheck,
    DTDecision,
    DTMode,
    MainComponentContract,
    SubComponentContract,
    SubComponentState,
    SynthesisContract,
    SynthesisStrategy,
    ValidatedComponent,
)

# -- Task 1: Core contracts --------------------------------------------------


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


# -- Task 2: State machine ---------------------------------------------------


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


# -- Task 3: Synthesis & Decision --------------------------------------------


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
