"""Unit tests for DirectStrategy."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from mindflow_backend.query.strategies import StrategyContext
from mindflow_backend.query.strategies.direct import DirectStrategy


@dataclass
class _FakeResponse:
    content: str


class _FakeAgent:
    def __init__(self, *, response: str = "fake response", raises: Exception | None = None):
        self.response = response
        self.raises = raises
        self.calls: list[dict] = []

    async def ainvoke(self, messages, tools=None, context=None):
        self.calls.append({"messages": messages, "tools": tools, "context": context})
        if self.raises:
            raise self.raises
        return _FakeResponse(content=self.response)


@pytest.mark.asyncio
async def test_direct_strategy_single_call_yields_one_assistant_event():
    agent = _FakeAgent(response="hello world")
    ctx = StrategyContext(message="hi", services={"agent": agent})

    events = [ev async for ev in DirectStrategy().run(ctx)]

    assert len(events) == 1
    assert events[0] == {"type": "assistant", "content": "hello world"}
    assert len(agent.calls) == 1
    # message falls back to context.message when context.messages is empty
    assert agent.calls[0]["messages"] == [{"role": "user", "content": "hi"}]


@pytest.mark.asyncio
async def test_direct_strategy_uses_preexisting_messages_when_provided():
    agent = _FakeAgent()
    messages = [{"role": "user", "content": "first"}, {"role": "assistant", "content": "prev"}]
    ctx = StrategyContext(message="irrelevant", messages=list(messages), services={"agent": agent})

    events = [ev async for ev in DirectStrategy().run(ctx)]

    assert len(events) == 1
    assert agent.calls[0]["messages"] == messages


@pytest.mark.asyncio
async def test_direct_strategy_without_agent_raises():
    strat = DirectStrategy()
    ctx = StrategyContext(message="hi")  # no services["agent"]
    with pytest.raises(ValueError, match="requires 'agent'"):
        async for _ in strat.run(ctx):
            pass


@pytest.mark.asyncio
async def test_direct_strategy_surfaces_agent_exception_as_error_event():
    agent = _FakeAgent(raises=RuntimeError("boom"))
    ctx = StrategyContext(message="hi", services={"agent": agent})

    events = [ev async for ev in DirectStrategy().run(ctx)]

    assert len(events) == 1
    assert events[0]["type"] == "system"
    assert events[0]["is_error"] is True
    assert "boom" in events[0]["content"]
