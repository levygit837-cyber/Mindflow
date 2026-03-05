"""DecompositionEngine — coordinates the full Task DAG pipeline.

Orchestrates: Tasker → Scheduler → Resolver (per task) → Synthesizer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from omnimind_backend.schemas.orchestration.decomposition.decomposition_v2 import (
    MainTaskContract,
    SubTaskContract,
)


# ---------------------------------------------------------------------------
# Abstract base classes (contracts for each pipeline stage)
# ---------------------------------------------------------------------------


class TaskDecomposer(ABC):
    """Breaks a user message into a MainTaskContract + list of SubTaskContracts."""

    @abstractmethod
    async def decompose(
        self,
        message: str,
        session_id: str,
        complexity_score: float,
        provider: str | None = None,
        model: str | None = None,
        memory_context: str = "",
    ) -> tuple[MainTaskContract, list[SubTaskContract]]:
        """Return (main, sub_tasks)."""


class TaskResolver(ABC):
    """Executes a single SubTaskContract and returns a result dict."""

    @abstractmethod
    async def resolve(
        self,
        contract: SubTaskContract,
        prior_results: dict[str, str],
        provider: str,
        model: str,
        memory_context: str = "",
        session_id: str = "default",
    ) -> dict[str, Any]:
        """Return dict with at least ``{"result": str}``."""


class TaskScheduler(ABC):
    """Orders SubTaskContracts respecting their dependency graph."""

    @abstractmethod
    def get_execution_order(
        self,
        components: list[SubTaskContract],
    ) -> list[SubTaskContract]:
        """Return tasks in dependency-safe execution order."""


class TaskSynthesizerBase(ABC):
    """Combines validated task results into a SynthesisContract."""

    @abstractmethod
    async def synthesize(
        self,
        session_id: UUID,
        main_contract: MainTaskContract,
        validated_components: list[Any],
        provider: str,
        model: str,
    ) -> Any:
        """Return SynthesisContract."""


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class DecompositionEngine:
    """Coordinates the Tasker → Scheduler → Resolver → Synthesizer pipeline."""

    def __init__(
        self,
        tasker: TaskDecomposer,
        resolver: TaskResolver,
        scheduler: TaskScheduler,
        synthesizer: TaskSynthesizerBase,
    ) -> None:
        self.tasker = tasker
        self.resolver = resolver
        self.scheduler = scheduler
        self.synthesizer = synthesizer

    async def execute(
        self,
        message: str,
        session_id: str,
        complexity_score: float,
        provider: str,
        model: str,
        memory_context: str = "",
    ) -> dict[str, Any]:
        """Run the full pipeline and return a results dict."""
        # 1 — Decompose
        main, components = await self.tasker.decompose(
            message=message,
            session_id=session_id,
            complexity_score=complexity_score,
            provider=provider,
            model=model,
            memory_context=memory_context,
        )

        # 2 — Schedule
        ordered = self.scheduler.get_execution_order(components)

        # 3 — Resolve
        prior_results: dict[str, str] = {}
        validated: list[dict[str, Any]] = []

        for contract in ordered:
            result = await self.resolver.resolve(
                contract=contract,
                prior_results=prior_results,
                provider=provider,
                model=model,
                memory_context=memory_context,
                session_id=session_id,
            )
            prior_results[str(contract.task_id)] = result.get("result", "")
            validated.append(result)

        # 4 — Synthesise
        try:
            sid = UUID(session_id)
        except ValueError:
            sid = main.main_task_id

        synthesis = await self.synthesizer.synthesize(
            session_id=sid,
            main_contract=main,
            validated_components=validated,
            provider=provider,
            model=model,
        )

        return {
            "main_contract": main,
            "components": components,
            "validated": validated,
            "synthesis": synthesis,
        }
