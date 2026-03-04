"""Scorer interface.

Defines the contract for computing component validation scores.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from omnimind_backend.schemas.orchestration.decomposition.decomposition_v2 import SubComponentState


@runtime_checkable
class ScorerProtocol(Protocol):
    """Contract for component scoring implementations."""

    def score(
        self,
        state: SubComponentState,
        consistency: float,
        agent_confidence: float,
    ) -> float:
        """Compute the composite validation score for a component.

        Args:
            state: Current component state with progress and evidence.
            consistency: Output compatibility with dependents (0-1).
            agent_confidence: Agent's self-reported confidence (0-1).

        Returns:
            Composite score (0-1). >= threshold means VALIDATED.
        """
        ...

    def is_validated(self, score: float) -> bool:
        """Check if a score passes the validation threshold."""
        ...
