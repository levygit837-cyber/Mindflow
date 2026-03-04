"""Scorer adapter — wraps scoring.py functions into ScorerProtocol.

Thin adapter that delegates to the pure functions in scoring.py,
satisfying the ScorerProtocol interface.
"""

from __future__ import annotations

from omnimind_backend.orchestrator.decomposition.scoring import (
    compute_component_score,
    is_validated,
)
from omnimind_backend.schemas.orchestration.decomposition.decomposition_v2 import SubComponentState


class ComponentScorer:
    """ScorerProtocol implementation backed by scoring.py."""

    def score(
        self,
        state: SubComponentState,
        consistency: float,
        agent_confidence: float,
    ) -> float:
        """Compute the composite validation score for a component."""
        return compute_component_score(state, consistency, agent_confidence)

    def is_validated(self, score: float) -> bool:
        """Check if a score passes the validation threshold."""
        return is_validated(score)
