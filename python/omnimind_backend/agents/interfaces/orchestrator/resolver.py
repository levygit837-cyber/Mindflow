"""Resolver interface.

Defines the contract for executing a single sub-component
through the appropriate agent and producing state with evidence.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from omnimind_backend.schemas.orchestration.decomposition.decomposition_v2 import (
    SubComponentContract,
    SubComponentState,
)


@runtime_checkable
class ResolverProtocol(Protocol):
    """Contract for component resolution (execution) implementations."""

    async def resolve(
        self,
        contract: SubComponentContract,
        prior_results: dict[str, str],
        provider: str | None = None,
        model: str | None = None,
        memory_context: str = "",
    ) -> SubComponentState:
        """Execute a sub-component and return its runtime state.

        Args:
            contract: The sub-component contract to execute.
            prior_results: Map of component_id (str) -> result text
                from previously completed dependencies.
            provider: LLM provider override.
            model: LLM model override.
            memory_context: RAG context from memory service.

        Returns:
            Updated SubComponentState with evidence and progress.
        """
        ...
