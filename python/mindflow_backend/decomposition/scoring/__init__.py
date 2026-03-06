"""Task validation scoring — pure functions + OOP adapter.

Functions
---------
compute_task_score(state, consistency, agent_confidence) -> float
    Weighted composite score:
    progress (35%) + evidence quality (35%) + consistency (20%) + agent_confidence (10%)

is_validated(score) -> bool
    True when score >= 0.85

Classes
-------
TaskScorer
    OOP adapter implementing ScorerProtocol backed by the functions above.
"""

from __future__ import annotations

from mindflow_backend.schemas.orchestration.decomposition.decomposition_v2 import SubTaskState


def compute_task_score(
    state: SubTaskState,
    consistency: float,
    agent_confidence: float,
) -> float:
    """Compute composite validation score for a completed sub-task.

    The scorer intentionally accepts any object with ``progress`` and
    ``evidence`` attributes so that callers that hand-craft mock states
    do not need to construct a full Pydantic model.
    """
    progress_score = getattr(state, "progress", 0.0) or 0.0

    evidence = getattr(state, "evidence", None)
    if evidence is not None:
        tests_total = getattr(evidence, "tests_total", 0) or 0
        tests_passed = getattr(evidence, "tests_passed", 0) or 0
        test_score = (tests_passed / tests_total) if tests_total > 0 else 0.0
        lint_score = 1.0 if getattr(evidence, "lint_passed", False) else 0.0
        evidence_score = 0.7 * test_score + 0.3 * lint_score
    else:
        evidence_score = 0.0

    raw = (
        0.35 * progress_score
        + 0.35 * evidence_score
        + 0.20 * consistency
        + 0.10 * agent_confidence
    )
    return max(0.0, min(1.0, raw))


def is_validated(score: float) -> bool:
    """Return True when *score* passes the validation threshold (≥ 0.85)."""
    return score >= 0.85


class TaskScorer:
    """OOP wrapper around compute_task_score / is_validated."""

    def score(
        self,
        state: SubTaskState,
        consistency: float,
        agent_confidence: float,
    ) -> float:
        return compute_task_score(state, consistency, agent_confidence)

    def is_validated(self, score: float) -> bool:
        return is_validated(score)
