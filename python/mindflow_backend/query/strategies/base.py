"""Base contracts for QueryEngine execution strategies.

Every strategy implements the same surface:

    async def run(self, context: StrategyContext) -> AsyncGenerator[dict, None]

yielding dict-shaped events (``type``, ``content`` and strategy-specific keys).
The QueryEngine dispatcher is the only caller; strategies do NOT hold their own
state across invocations — all state lives in the ``StrategyContext``.

This file is dependency-light on purpose (no LangGraph, no DB, no streaming
service), which lets unit tests exercise each strategy in isolation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - typing-only
    from mindflow_backend.query.budget.token_counter import TokenBudget
    from mindflow_backend.schemas.orchestration.orchestrator import OrchestratorSession


class QueryStrategy(StrEnum):
    """Canonical list of execution strategies in the unified kernel."""

    DIRECT = "direct"
    REACT = "react"
    DECOMPOSITION = "decomposition"
    DEEP_WORK = "deep_work"


@dataclass
class StrategyContext:
    """Inputs carried across every strategy invocation.

    Keep this data-only. Services (memory, streaming, bus) are resolved via the
    ``services`` mapping so strategies stay testable without the full stack.
    """

    message: str
    session_id: str | None = None
    execution_id: str | None = None
    provider: str | None = None
    model: str | None = None
    agent_type: str | None = None
    tools: list[Any] = field(default_factory=list)
    messages: list[dict[str, Any]] = field(default_factory=list)
    max_turns: int = 50
    max_depth: int = 1000
    token_budget: TokenBudget | None = None
    session: OrchestratorSession | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    services: dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyResult:
    """Terminal summary of a strategy run, returned after the stream finishes."""

    response: str = ""
    error: str | None = None
    turn_count: int = 0
    messages: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseStrategy(ABC):
    """Abstract base class for every QueryEngine strategy.

    Strategies are cheap to construct and stateless. The engine builds a new
    instance per request via ``get_strategy(...)``.
    """

    #: The enum member this strategy implements.
    strategy: QueryStrategy

    @abstractmethod
    def run(
        self,
        context: StrategyContext,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Execute the strategy, yielding stream events as they occur.

        The final event SHOULD include ``{"type": "final", "result": ...}`` so
        the dispatcher can surface a ``StrategyResult`` to the caller.
        """
        raise NotImplementedError
