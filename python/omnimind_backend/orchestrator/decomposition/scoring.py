"""DT v2 component scoring.

Implements the score formula from decomposition-thinking-contracts-v2.md:
score = 0.35 * progress + 0.35 * validation_objective + 0.20 * consistency + 0.10 * agent_confidence
"""

from __future__ import annotations

from omnimind_backend.schemas.orchestration.decomposition.decomposition_v2 import SubComponentState

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
