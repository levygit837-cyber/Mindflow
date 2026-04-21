"""Unit tests for DeepWorkStrategy."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from mindflow_backend.query.strategies import StrategyContext
from mindflow_backend.query.strategies.deep_work import DeepWorkStrategy


@dataclass
class _FakeResponse:
    content: str


class _ScriptedAgent:
    def __init__(self, scripted: list[str], raises_at: int | None = None):
        self.scripted = list(scripted)
        self.raises_at = raises_at
        self.call_count = 0

    async def ainvoke(self, messages, tools=None, context=None):
        self.call_count += 1
        if self.raises_at is not None and self.call_count - 1 == self.raises_at:
            raise RuntimeError(f"boom at turn {self.raises_at}")
        if not self.scripted:
            return _FakeResponse(content="default tail")
        return _FakeResponse(content=self.scripted.pop(0))


@pytest.mark.asyncio
async def test_deep_work_requires_agent_service():
    ctx = StrategyContext(message="hi")
    with pytest.raises(ValueError, match="requires 'agent'"):
        async for _ in DeepWorkStrategy().run(ctx):
            pass


@pytest.mark.asyncio
async def test_deep_work_stops_when_no_continuation_marker():
    agent = _ScriptedAgent(scripted=["Answer without continuation markers."])
    ctx = StrategyContext(message="hi", services={"agent": agent}, max_depth=10)

    events = [ev async for ev in DeepWorkStrategy().run(ctx)]

    assistant = [ev for ev in events if ev["type"] == "assistant"]
    final = [ev for ev in events if ev["type"] == "final"]

    assert len(assistant) == 1
    assert len(final) == 1
    assert final[0]["turns"] == 1
    assert agent.call_count == 1


@pytest.mark.asyncio
async def test_deep_work_continues_until_agent_stops_signaling():
    # First two responses contain a continuation marker, the third does not.
    # NOTE: should_continue_investigation() in orchestrator/deep_work.py
    # lowercases the response before checking markers but keeps some markers
    # mixed-case (e.g. "I should check"). We only use markers that are
    # lowercase to stay faithful to the legacy behaviour.
    agent = _ScriptedAgent(
        scripted=[
            "Let me investigate more...",  # triggers continuation ("let me investigate")
            "We need to explore further here.",  # triggers continuation
            "Final synthesis — done.",  # no marker
        ]
    )
    ctx = StrategyContext(message="hi", services={"agent": agent}, max_depth=10)

    events = [ev async for ev in DeepWorkStrategy().run(ctx)]

    assistants = [ev for ev in events if ev["type"] == "assistant"]
    final = next(ev for ev in events if ev["type"] == "final")

    assert len(assistants) == 3
    assert agent.call_count == 3
    # Legacy accumulated-response format with continuation markers
    assert "--- CONTINUATION TURN 2 ---" in final["content"]
    assert "--- CONTINUATION TURN 3 ---" in final["content"]
    assert final["turns"] == 3


@pytest.mark.asyncio
async def test_deep_work_respects_max_depth():
    agent = _ScriptedAgent(
        scripted=[
            "let me investigate",  # turn 0: continue
            "let me investigate",  # turn 1: continue
            "let me investigate",  # turn 2: continue (but max_depth will cut)
        ]
    )
    ctx = StrategyContext(
        message="hi",
        services={"agent": agent},
        max_depth=2,
    )

    events = [ev async for ev in DeepWorkStrategy().run(ctx)]

    assistants = [ev for ev in events if ev["type"] == "assistant"]
    # With max_depth=2, the loop allows turns 0 and 1 before breaking.
    assert len(assistants) == 2


@pytest.mark.asyncio
async def test_deep_work_surfaces_agent_failure_as_error_event():
    agent = _ScriptedAgent(scripted=["let me investigate"], raises_at=1)
    ctx = StrategyContext(message="hi", services={"agent": agent}, max_depth=10)

    events = [ev async for ev in DeepWorkStrategy().run(ctx)]

    errors = [ev for ev in events if ev.get("is_error")]
    assert len(errors) == 1
    assert "boom at turn 1" in errors[0]["content"]
