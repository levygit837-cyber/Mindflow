"""Resolver interface.

Defines the contract for executing a single sub-task
through the appropriate agent and producing state with evidence.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from omnimind_backend.schemas.orchestration.decomposition.decomposition_v2 import (
    SubTaskContract,
    SubTaskState,
)


@runtime_checkable
class ResolverProtocol(Protocol):
    """Contract for task resolution (execution) implementations."""

    async def resolve(
        self,
        contract: SubTaskContract,
        prior_results: dict[str, str],
        provider: str | None = None,
        model: str | None = None,
        memory_context: str = "",
    ) -> SubTaskState:
        """Execute a sub-task and return its runtime state.

        Args:
            contract: The sub-task contract to execute.
            prior_results: Map of task_id (str) -> result text
                from previously completed dependencies.
            provider: LLM provider override.
            model: LLM model override.
            memory_context: RAG context from memory service.

        Returns:
            Updated SubTaskState with evidence and progress.
        """
        ...
