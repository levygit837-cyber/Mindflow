from __future__ import annotations

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
