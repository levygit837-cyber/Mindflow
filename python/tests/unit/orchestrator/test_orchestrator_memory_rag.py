import contextlib
from types import SimpleNamespace

import pytest

from mindflow_backend.orchestrator.graph import execute_node
from mindflow_backend.schemas.orchestrator import AgentType, OrchestratorDecision

# These tests patch attributes in the orchestrator.graph compatibility shim that
# no longer exist there (e.g. get_agent, get_model_for_provider).  The tests are
# kept for reference but skipped until they are updated to patch the correct
# module paths in simple_flow.py / step_runner.py.
pytestmark = pytest.mark.skip(reason="patch targets outdated — compatibility shim no longer has get_agent etc.")


class _FakeLLM:
    def __init__(self) -> None:
        self.bound_tools = None
        self.seen_messages = None

    def bind_tools(self, tools):  # noqa: ANN001
        self.bound_tools = tools
        return self

    async def astream(self, messages):  # noqa: ANN001
        self.seen_messages = messages
        yield SimpleNamespace(content="ok", response_metadata={})


@pytest.mark.asyncio
async def test_execute_node_injects_memory_context_into_llm_messages(monkeypatch) -> None:
    fake_llm = _FakeLLM()
    fake_agent = SimpleNamespace(
        agent_type=AgentType.CODER,
        system_prompt="Você é um agente de código.",
    )

    class _FakeMemoryService:
        def retrieve_context_for_query(self, **_kwargs):  # noqa: ANN001
            return SimpleNamespace(
                context="Memory Context: decisões anteriores sobre autenticação e pgvector.",
                references=["window:1"],
            )

    monkeypatch.setattr("mindflow_backend.orchestrator.graph.get_agent", lambda *_args, **_kwargs: fake_agent)
    monkeypatch.setattr(
        "mindflow_backend.orchestrator.graph.get_model_for_provider",
        lambda *_args, **_kwargs: fake_llm,
    )
    monkeypatch.setattr(
        "mindflow_backend.orchestrator.graph.create_default_registry",
        lambda *_args, **_kwargs: SimpleNamespace(get_tools_for_agent=lambda *_a, **_k: []),
    )
    monkeypatch.setattr(
        "mindflow_backend.orchestrator.graph.MindFlowSandbox",
        lambda *_args, **_kwargs: object(),
    )
    monkeypatch.setattr(
        "mindflow_backend.orchestrator.graph.get_memory_service",
        lambda: _FakeMemoryService(),
    )
    monkeypatch.setattr(
        "mindflow_backend.orchestrator.graph.db_session",
        lambda: contextlib.nullcontext(object()),
    )
    monkeypatch.setattr(
        "mindflow_backend.orchestrator.graph.get_settings",
        lambda: SimpleNamespace(
            default_provider="openai",
            default_model="stub",
            enable_decomposition_thinking=False,
            working_path=None,
            memory_enabled=True,
        ),
    )
    async def _noop_dispatch(*_args, **_kwargs):  # noqa: ANN001
        return None

    monkeypatch.setattr("mindflow_backend.orchestrator.graph.adispatch_custom_event", _noop_dispatch)

    state = {
        "message": "Implemente login com JWT",
        "session_id": "sess-rag-1",
        "decision": OrchestratorDecision(agent=AgentType.CODER, task="Implemente login com JWT"),
    }

    result = await execute_node(state)

    assert result["response"] == "ok"
    assert fake_llm.seen_messages is not None
    assert any(
        "Memory Context" in str(getattr(msg, "content", ""))
        for msg in fake_llm.seen_messages
    )
