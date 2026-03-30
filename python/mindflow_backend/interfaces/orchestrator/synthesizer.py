"""Synthesizer interface.

Defines the contract for combining validated sub-task
results into a final SynthesisContract.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from mindflow_backend.schemas.orchestration.decomposition.decomposition_v2 import (
    MainTaskContract,
    SynthesisContract,
    ValidatedTask,
)


@runtime_checkable
class SynthesizerProtocol(Protocol):
    """Contract for synthesis implementations."""

    async def synthesize(
        self,
        session_id: UUID,
        main_contract: MainTaskContract,
        validated_components: list[ValidatedTask],
        provider: str | None = None,
        model: str | None = None,
    ) -> SynthesisContract:
        """Combine validated tasks into a final synthesis.

        Args:
            session_id: Task session identifier.
            main_contract: The top-level goal and constraints.
            validated_components: Tasks that passed scoring.
            provider: LLM provider override.
            model: LLM model override.

        Returns:
            SynthesisContract with final answer, consistency checks,
            and overall confidence.
        """
        ...
