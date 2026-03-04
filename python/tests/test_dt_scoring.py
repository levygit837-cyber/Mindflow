"""Tests for DT v2 component scoring."""

from uuid import uuid4

from omnimind_backend.orchestrator.decomposition.scoring import (
    compute_component_score,
    is_validated,
)
from omnimind_backend.schemas.decomposition_v2 import (
    ComponentEvidence,
    ComponentStatus,
    SubComponentState,
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
    # 0.35*0.9 + 0.35*(0.7*0.8+0.3*1.0) + 0.20*0.8 + 0.10*0.7
    # = 0.315 + 0.35*0.86 + 0.16 + 0.07 = 0.315 + 0.301 + 0.16 + 0.07 = 0.846
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


def test_is_validated_above_threshold() -> None:
    assert is_validated(0.90) is True
    assert is_validated(0.85) is True


def test_is_validated_below_threshold() -> None:
    assert is_validated(0.84) is False
    assert is_validated(0.0) is False
