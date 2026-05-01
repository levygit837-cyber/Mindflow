"""Unit tests for ReActStrategy (Claude Code-style while-true loop)."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from mindflow_backend.query.budget.token_counter import TokenBudget
from mindflow_backend.query.strategies import StrategyContext
from mindflow_backend.query.strategies.react import ReActStrategy, react_loop


@dataclass
class _FakeToolCall:
    """Mimics LangChain structured_tool_calls — attrs name/args/id."""

    name: str
    args: dict  # LangChain uses ``.args`` for structured tool calls
    id: str


@dataclass
class _FakeResponse:
    content: str = ""
    structured_tool_calls: list[_FakeToolCall] = field(default_factory=list)
    # Intentionally NOT exposing .tool_calls so the extractor falls back to
    # .structured_tool_calls — this exercises the alternate code path.


class _ScriptedOrchestrator:
    """Returns each scripted response in turn, then empty tool_calls to end."""

    def __init__(self, scripted: list[_FakeResponse]):
        self.scripted = list(scripted)
        self.call_count = 0

    async def ainvoke(self, messages, tools=None, context=None):
        self.call_count += 1
        if not self.scripted:
            return _FakeResponse(content="done")
        return self.scripted.pop(0)


class _FakeTool:
    def __init__(self, name: str, *, raises: Exception | None = None, result="tool-ok"):
        self.name = name
        self.raises = raises
        self.result = result
        self.calls: list[dict] = []

    async def execute(self, **kwargs):
        self.calls.append(kwargs)
        if self.raises:
            raise self.raises
        return self.result


@pytest.mark.asyncio
async def test_react_requires_orchestrator_service():
    ctx = StrategyContext(message="hi")
    with pytest.raises(ValueError, match="requires 'orchestrator'"):
        async for _ in ReActStrategy().run(ctx):
            pass


@pytest.mark.asyncio
async def test_react_terminates_when_no_tool_use():
    orchestrator = _ScriptedOrchestrator([_FakeResponse(content="final answer")])
    ctx = StrategyContext(
        message="hi",
        services={"orchestrator": orchestrator},
        token_budget=TokenBudget(max_tokens=1000),
    )

    events = [ev async for ev in ReActStrategy().run(ctx)]

    assistant_events = [ev for ev in events if ev["type"] == "assistant"]
    assert len(assistant_events) == 1
    assert assistant_events[0]["content"] == "final answer"
    assert orchestrator.call_count == 1


@pytest.mark.asyncio
async def test_react_counts_response_against_token_budget():
    orchestrator = _ScriptedOrchestrator([_FakeResponse(content="x" * 200)])
    budget = TokenBudget(max_tokens=20, use_tiktoken=False)

    events = [
        ev
        async for ev in react_loop(
            initial_message="hi",
            orchestrator=orchestrator,
            tools=[],
            token_budget=budget,
        )
    ]

    assert any(ev["type"] == "assistant" for ev in events)
    assert events[-1]["type"] == "system"
    assert "Token budget exhausted" in events[-1]["content"]
    assert budget.remaining_tokens == 0


@pytest.mark.asyncio
async def test_react_executes_tool_then_terminates_on_next_turn():
    calls = [
        _FakeResponse(
            content="calling tool",
            structured_tool_calls=[_FakeToolCall(name="echo", args={"x": 1}, id="tc-1")],
        ),
        _FakeResponse(content="wrap-up", structured_tool_calls=[]),
    ]
    orchestrator = _ScriptedOrchestrator(calls)
    tool = _FakeTool(name="echo", result={"echoed": 1})
    ctx = StrategyContext(
        message="hi",
        tools=[tool],
        services={"orchestrator": orchestrator},
        token_budget=TokenBudget(max_tokens=1000),
    )

    events = [ev async for ev in ReActStrategy().run(ctx)]

    kinds = [ev["type"] for ev in events]
    assert kinds.count("assistant") == 2
    assert kinds.count("tool_result") == 1
    tool_result = next(ev for ev in events if ev["type"] == "tool_result")
    assert tool_result["tool_use_id"] == "tc-1"
    assert tool_result["content"] == {"echoed": 1}
    assert tool.calls == [{"x": 1}]


@pytest.mark.asyncio
async def test_react_missing_tool_yields_error_result():
    orchestrator = _ScriptedOrchestrator(
        [
            _FakeResponse(
                content="calling ghost",
                structured_tool_calls=[
                    _FakeToolCall(name="ghost", args={}, id="tc-x")
                ],
            ),
            _FakeResponse(content="end"),
        ]
    )
    ctx = StrategyContext(
        message="hi",
        tools=[],  # intentionally empty
        services={"orchestrator": orchestrator},
        token_budget=TokenBudget(max_tokens=1000),
    )

    events = [ev async for ev in ReActStrategy().run(ctx)]

    errors = [ev for ev in events if ev["type"] == "tool_result" and ev.get("is_error")]
    assert len(errors) == 1
    assert "not found" in errors[0]["content"]


@pytest.mark.asyncio
async def test_react_stops_at_max_turns():
    # Orchestrator always wants another tool call — should be cut by max_turns.
    infinite = [
        _FakeResponse(
            content=f"turn {i}",
            structured_tool_calls=[_FakeToolCall(name="echo", args={}, id=f"tc-{i}")],
        )
        for i in range(20)
    ]
    orchestrator = _ScriptedOrchestrator(infinite)
    tool = _FakeTool(name="echo")
    ctx = StrategyContext(
        message="hi",
        tools=[tool],
        services={"orchestrator": orchestrator},
        max_turns=2,
        token_budget=TokenBudget(max_tokens=1000),
    )

    events = [ev async for ev in ReActStrategy().run(ctx)]

    # Must end with a system message indicating max turns
    assert events[-1]["type"] == "system"
    assert "Max turns" in events[-1]["content"]


class _FakeResponseWithDictToolCalls:
    """Mimics LangChain AIMessage.tool_calls which returns plain dicts."""

    def __init__(self, content: str, tool_calls: list[dict] | None = None):
        self.content = content
        self.tool_calls = tool_calls or []


class _ScriptedOrchestratorDictTools:
    """Returns responses with dict-format tool_calls (LangChain native)."""

    def __init__(self, scripted: list[_FakeResponseWithDictToolCalls]):
        self.scripted = list(scripted)
        self.call_count = 0

    async def ainvoke(self, messages, tools=None, context=None):
        self.call_count += 1
        if not self.scripted:
            return _FakeResponseWithDictToolCalls(content="done")
        return self.scripted.pop(0)


@pytest.mark.asyncio
async def test_react_dict_format_tool_calls():
    """LangChain AIMessage.tool_calls returns dicts — must not crash on dict.function."""
    orchestrator = _ScriptedOrchestratorDictTools(
        [
            _FakeResponseWithDictToolCalls(
                content="calling tool",
                tool_calls=[
                    {"name": "echo", "input": {"x": 1}, "id": "tc-dict-1"}
                ],
            ),
            _FakeResponseWithDictToolCalls(content="wrap-up", tool_calls=[]),
        ]
    )
    tool = _FakeTool(name="echo", result="dict-tool-ok")
    ctx = StrategyContext(
        message="hi",
        tools=[tool],
        services={"orchestrator": orchestrator},
        token_budget=TokenBudget(max_tokens=1000),
    )

    events = [ev async for ev in ReActStrategy().run(ctx)]

    kinds = [ev["type"] for ev in events]
    assert kinds.count("assistant") == 2
    assert kinds.count("tool_result") == 1
    tool_result = next(ev for ev in events if ev["type"] == "tool_result")
    assert tool_result["tool_use_id"] == "tc-dict-1"
    assert tool_result["content"] == "dict-tool-ok"
