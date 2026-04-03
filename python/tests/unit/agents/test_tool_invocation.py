from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from mindflow_backend.agents.tools.base.tool_invocation import invoke_with_tools


class _FakeLLM:
    def __init__(self, response: str) -> None:
        self._response = response
        self.messages: list[list[dict[str, str]]] = []

    async def ainvoke(self, messages):  # noqa: ANN001
        self.messages.append(list(messages))
        return SimpleNamespace(content=self._response, tool_calls=[])


@pytest.mark.asyncio
async def test_invoke_with_tools_emits_final_agent_response_event() -> None:
    events: list[tuple[str, dict[str, str]]] = []

    async def event_dispatcher(name: str, payload: dict[str, str]) -> None:
        events.append((name, payload))

    result = await invoke_with_tools(
        llm=_FakeLLM("Resposta final do modelo."),
        messages=[{"role": "system", "content": "system"}],
        lc_tools=[],
        event_dispatcher=event_dispatcher,
    )

    assert result == "Resposta final do modelo."
    assert events == [("agent_response", {"chunk": "Resposta final do modelo."})]


class _FakeToolLoopLLM:
    def __init__(self) -> None:
        self.calls = 0
        self.messages: list[list[object]] = []

    async def ainvoke(self, messages):  # noqa: ANN001
        self.messages.append(list(messages))
        self.calls += 1
        if self.calls == 1:
            return SimpleNamespace(
                content="",
                tool_calls=[
                    {"id": "call-1", "name": "slow_tool", "args": {}},
                    {"id": "call-2", "name": "fast_tool", "args": {}},
                ],
            )
        return SimpleNamespace(content="Resposta final paralela.", tool_calls=[])


class _FakeStructuredTool:
    def __init__(self, name: str, delay: float, result: str) -> None:
        self.name = name
        self.metadata = {
            "is_concurrency_safe": True,
            "tool_name": name,
        }
        self._delay = delay
        self._result = result

    async def ainvoke(self, _tool_input):  # noqa: ANN001
        await asyncio.sleep(self._delay)
        return self._result


@pytest.mark.asyncio
async def test_invoke_with_tools_keeps_tool_result_order_for_parallel_batch() -> None:
    llm = _FakeToolLoopLLM()
    events: list[tuple[str, dict[str, str]]] = []

    async def event_dispatcher(name: str, payload: dict[str, str]) -> None:
        events.append((name, payload))

    result = await invoke_with_tools(
        llm=llm,
        messages=[{"role": "system", "content": "system"}],
        lc_tools=[
            _FakeStructuredTool("slow_tool", delay=0.05, result="slow-result"),
            _FakeStructuredTool("fast_tool", delay=0.01, result="fast-result"),
        ],
        event_dispatcher=event_dispatcher,
        session_id="session-tools",
    )

    assert result == "Resposta final paralela."
    second_call_messages = llm.messages[1]
    tool_messages = [
        message
        for message in second_call_messages
        if getattr(message, "tool_call_id", None) in {"call-1", "call-2"}
    ]
    assert [message.tool_call_id for message in tool_messages] == ["call-1", "call-2"]
    assert [message.content for message in tool_messages] == ["slow-result", "fast-result"]
    assert [
        payload["tool"]
        for name, payload in events
        if name == "tool_call"
    ] == ["slow_tool", "fast_tool"]
