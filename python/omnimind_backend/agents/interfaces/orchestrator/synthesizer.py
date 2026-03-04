"""Synthesizer interface.

Defines the contract for combining validated sub-component
results into a final SynthesisContract.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from omnimind_backend.schemas.orchestration.decomposition.decomposition_v2 import (
    MainComponentContract,
    SynthesisContract,
    ValidatedComponent,
)


@runtime_checkable
class SynthesizerProtocol(Protocol):
    """Contract for synthesis implementations."""

    async def synthesize(
        self,
        session_id: UUID,
        main_contract: MainComponentContract,
        validated_components: list[ValidatedComponent],
        provider: str | None = None,
        model: str | None = None,
    ) -> SynthesisContract:
        """Combine validated components into a final synthesis.

        Args:
            session_id: DT session identifier.
            main_contract: The top-level goal and constraints.
            validated_components: Components that passed scoring.
            provider: LLM provider override.
            model: LLM model override.

        Returns:
            SynthesisContract with final answer, consistency checks,
            and overall confidence.
        """
        ...
