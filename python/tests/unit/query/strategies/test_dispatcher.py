"""Tests for QueryEngine.execute() strategy dispatcher.

Focus: input validation, enum normalization, budget defaulting, and error
propagation via the ``{"type": "system", "is_error": True}`` contract.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from mindflow_backend.query import (
    QueryEngine,
    QueryStrategy,
    StrategyContext,
    TokenBudget,
)


@dataclass
class _FakeResponse:
    content: str


class _FakeAgent:
    async def ainvoke(self, messages, tools=None, context=None):
        return _FakeResponse(content="direct-ok")


@pytest.fixture
def engine() -> QueryEngine:
    return QueryEngine(
        providers=[],
        budget=TokenBudget(max_tokens=1000),
        session_id="dispatcher-test",
    )


@pytest.mark.asyncio
async def test_dispatcher_accepts_enum_value(engine):
    ctx = StrategyContext(message="hi", services={"agent": _FakeAgent()})
    events = [ev async for ev in engine.execute(QueryStrategy.DIRECT, ctx)]
    assistants = [ev for ev in events if ev["type"] == "assistant"]
    assert len(assistants) == 1
    assert assistants[0]["content"] == "direct-ok"


@pytest.mark.asyncio
async def test_dispatcher_accepts_string_value(engine):
    ctx = StrategyContext(message="hi", services={"agent": _FakeAgent()})
    events = [ev async for ev in engine.execute("direct", ctx)]
    assistants = [ev for ev in events if ev["type"] == "assistant"]
    assert len(assistants) == 1


@pytest.mark.asyncio
async def test_dispatcher_rejects_unknown_string_strategy(engine):
    ctx = StrategyContext(message="hi", services={"agent": _FakeAgent()})
    with pytest.raises(ValueError):
        async for _ in engine.execute("nonexistent", ctx):
            pass


@pytest.mark.asyncio
async def test_dispatcher_rejects_non_enum_type(engine):
    ctx = StrategyContext(message="hi", services={"agent": _FakeAgent()})
    with pytest.raises(TypeError, match="QueryStrategy"):
        async for _ in engine.execute(42, ctx):
            pass


@pytest.mark.asyncio
async def test_dispatcher_rejects_non_strategy_context(engine):
    with pytest.raises(TypeError, match="StrategyContext"):
        async for _ in engine.execute(QueryStrategy.DIRECT, {"not": "a context"}):
            pass


@pytest.mark.asyncio
async def test_dispatcher_defaults_token_budget_to_engine_budget(engine):
    ctx = StrategyContext(message="hi", services={"agent": _FakeAgent()})
    assert ctx.token_budget is None
    async for _ in engine.execute(QueryStrategy.DIRECT, ctx):
        pass
    assert ctx.token_budget is engine.budget


@pytest.mark.asyncio
async def test_dispatcher_surfaces_strategy_exception_as_error_event(engine):
    # DirectStrategy raises ValueError when 'agent' is missing, but the
    # strategy is invoked BEFORE that — the ValueError bubbles up through
    # the strategy .run() generator. The dispatcher catches it and yields
    # a system error event.
    ctx = StrategyContext(message="hi")  # no services["agent"]
    events = [ev async for ev in engine.execute(QueryStrategy.DIRECT, ctx)]
    errors = [ev for ev in events if ev.get("is_error")]
    assert len(errors) == 1
    assert "requires 'agent'" in errors[0]["content"]
