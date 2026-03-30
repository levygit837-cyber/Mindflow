"""Scorer interface.

Defines the contract for computing task validation scores.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from mindflow_backend.schemas.orchestration.decomposition.decomposition_v2 import SubTaskState


@runtime_checkable
class ScorerProtocol(Protocol):
    """Contract for task scoring implementations."""

    def score(
        self,
        state: SubTaskState,
        consistency: float,
        agent_confidence: float,
    ) -> float:
        """Compute the composite validation score for a task.

        Args:
            state: Current task state with progress and evidence.
            consistency: Output compatibility with dependents (0-1).
            agent_confidence: Agent's self-reported confidence (0-1).

        Returns:
            Composite score (0-1). >= threshold means VALIDATED.
        """
        ...

    def is_validated(self, score: float) -> bool:
        """Check if a score passes the validation threshold."""
        ...
