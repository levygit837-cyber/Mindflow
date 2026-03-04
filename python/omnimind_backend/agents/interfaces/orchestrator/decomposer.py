"""Decomposer interface.

Defines the contract for breaking a user message into
a MainComponentContract with SubComponentContracts.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from omnimind_backend.schemas.orchestration.decomposition.decomposition_v2 import (
    MainComponentContract,
    SubComponentContract,
)


@runtime_checkable
class DecomposerProtocol(Protocol):
    """Contract for decomposition implementations."""

    async def decompose(
        self,
        message: str,
        session_id: str,
        complexity_score: float,
        provider: str | None = None,
        model: str | None = None,
        memory_context: str = "",
    ) -> tuple[MainComponentContract, list[SubComponentContract]]:
        """Break a user message into a main contract and sub-components.

        Args:
            message: The original user request.
            session_id: Chat session identifier.
            complexity_score: Pre-computed complexity (0-1).
            provider: LLM provider override.
            model: LLM model override.
            memory_context: RAG context from memory service.

        Returns:
            Tuple of (main contract, list of sub-component contracts).
        """
        ...
