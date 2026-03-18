from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from mindflow_backend.orchestrator.step_runner import run_workflow_step


class _FakeLLM:
    def __init__(self, *, response: str) -> None:
        self._response = response
        self.bind_tools_called = False

    async def ainvoke(self, messages):  # noqa: ANN001
        return SimpleNamespace(content=self._response)

    def bind_tools(self, tools):  # noqa: ANN001
        self.bind_tools_called = True
        return self


@pytest.mark.asyncio
async def test_memory_grounded_turn_answers_without_tools_when_memory_is_sufficient(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_llm = _FakeLLM(response="Com base na memória, o marcador é MEMORIA-OMEGA-1779F714.")

    monkeypatch.setattr(
        "mindflow_backend.orchestrator.step_runner.get_settings",
        lambda: SimpleNamespace(working_path=None),
        raising=True,
    )
    monkeypatch.setattr(
        "mindflow_backend.orchestrator.step_runner.get_agent",
        lambda *args, **kwargs: SimpleNamespace(system_prompt="system", sandbox="none"),
        raising=True,
    )
    monkeypatch.setattr(
        "mindflow_backend.orchestrator.step_runner.get_agent_runtime_policy",
        lambda *args, **kwargs: SimpleNamespace(max_iterations=10),
        raising=True,
    )
    monkeypatch.setattr(
        "mindflow_backend.orchestrator.step_runner.create_default_registry",
        lambda *args, **kwargs: SimpleNamespace(get_tools_for_agent=lambda agent: ["dummy_tool"]),
        raising=True,
    )
    monkeypatch.setattr(
        "mindflow_backend.orchestrator.step_runner.to_langchain_tools",
        lambda tools: tools,
        raising=True,
    )
    monkeypatch.setattr(
        "mindflow_backend.orchestrator.step_runner.MindFlowSandbox",
        lambda *args, **kwargs: object(),
        raising=True,
    )
    monkeypatch.setattr(
        "mindflow_backend.orchestrator.step_runner.get_model_for_provider",
        lambda *args, **kwargs: fake_llm,
        raising=True,
    )

    invoke_with_tools = AsyncMock(side_effect=AssertionError("tools should not run"))
    monkeypatch.setattr(
        "mindflow_backend.orchestrator.step_runner.invoke_with_tools",
        invoke_with_tools,
        raising=True,
    )

    step = SimpleNamespace(
        agent_id="analyst",
        agent_role=SimpleNamespace(value="analyst"),
        specialist=None,
        step_id="step-1",
        objective="retome o marcador",
    )

    result = await run_workflow_step(
        step=step,
        user_message="Retome o marcador",
        provider="ollama",
        model="qwen3:8b",
        session_id="sess-1",
        memory_context="Memory Context:\n- O marcador salvo foi MEMORIA-OMEGA-1779F714.",
        memory_grounded=True,
    )

    assert result["status"] == "completed"
    assert "MEMORIA-OMEGA-1779F714" in result["full_output"]
    assert fake_llm.bind_tools_called is False


@pytest.mark.asyncio
async def test_workflow_step_forwards_event_dispatcher_when_using_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_llm = _FakeLLM(response="Resposta final do modelo.")
    event_dispatcher = AsyncMock()

    monkeypatch.setattr(
        "mindflow_backend.orchestrator.step_runner.get_settings",
        lambda: SimpleNamespace(working_path=None),
        raising=True,
    )
    monkeypatch.setattr(
        "mindflow_backend.orchestrator.step_runner.get_agent",
        lambda *args, **kwargs: SimpleNamespace(system_prompt="system", sandbox="none"),
        raising=True,
    )
    monkeypatch.setattr(
        "mindflow_backend.orchestrator.step_runner.get_agent_runtime_policy",
        lambda *args, **kwargs: SimpleNamespace(max_iterations=10),
        raising=True,
    )
    monkeypatch.setattr(
        "mindflow_backend.orchestrator.step_runner.create_default_registry",
        lambda *args, **kwargs: SimpleNamespace(get_tools_for_agent=lambda agent: ["dummy_tool"]),
        raising=True,
    )
    monkeypatch.setattr(
        "mindflow_backend.orchestrator.step_runner.to_langchain_tools",
        lambda tools: tools,
        raising=True,
    )
    monkeypatch.setattr(
        "mindflow_backend.orchestrator.step_runner.MindFlowSandbox",
        lambda *args, **kwargs: object(),
        raising=True,
    )
    monkeypatch.setattr(
        "mindflow_backend.orchestrator.step_runner.get_model_for_provider",
        lambda *args, **kwargs: fake_llm,
        raising=True,
    )

    invoke_with_tools = AsyncMock(return_value="agent output ready")
    monkeypatch.setattr(
        "mindflow_backend.orchestrator.step_runner.invoke_with_tools",
        invoke_with_tools,
        raising=True,
    )

    step = SimpleNamespace(
        agent_id="analyst",
        agent_role=SimpleNamespace(value="analyst"),
        specialist=None,
        step_id="step-1",
        objective="retome o marcador",
    )

    result = await run_workflow_step(
        step=step,
        user_message="Retome o marcador",
        provider="ollama",
        model="qwen3:8b",
        session_id="sess-1",
        event_dispatcher=event_dispatcher,
    )

    assert result["status"] == "completed"
    assert invoke_with_tools.await_count == 1
    assert invoke_with_tools.await_args.kwargs["event_dispatcher"] is event_dispatcher
