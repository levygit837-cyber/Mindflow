"""Tests for canonical simple-flow execution helpers."""

from types import SimpleNamespace

import pytest

from mindflow_backend.orchestrator.graph import execute_node
from mindflow_backend.schemas.orchestration.orchestrator import (
    AgentType,
    ExecutionStrategy,
    OrchestratorDecision,
)


@pytest.mark.asyncio
async def test_execute_node_runs_chain_when_strategy_is_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "mindflow_backend.graphs.implementations.orchestrator.simple_flow.get_settings",
        lambda: SimpleNamespace(
            default_provider="test",
            default_model="test",
            enable_decomposition_thinking=False,
            memory_enabled=False,
            working_path=None,
        ),
        raising=True,
    )
    monkeypatch.setattr(
        "mindflow_backend.graphs.implementations.orchestrator.simple_flow.get_agent",
        lambda *_args, **_kwargs: SimpleNamespace(agent_type=AgentType.CODER),
        raising=True,
    )
    monkeypatch.setattr(
        "mindflow_backend.graphs.implementations.orchestrator.simple_flow.get_model_for_provider",
        lambda *_args, **_kwargs: object(),
        raising=True,
    )

    async def _fake_execute_chain_with_intelligence(**kwargs):  # noqa: ANN003
        assert kwargs["chain_id"] == "coding_task"
        return {"response": "ok", "error": None, "execution_metadata": {"planner": "test"}}

    monkeypatch.setattr(
        "mindflow_backend.orchestrator.chain_integration.execute_chain_with_intelligence",
        _fake_execute_chain_with_intelligence,
        raising=True,
    )
    async def _noop_dispatch(*_args, **_kwargs):  # noqa: ANN001
        return None

    monkeypatch.setattr(
        "langchain_core.callbacks.manager.adispatch_custom_event",
        _noop_dispatch,
        raising=True,
    )

    decision = OrchestratorDecision(
        rationale="test",
        agent=AgentType.CODER,
        task="test",
        execution_strategy=ExecutionStrategy.CHAIN,
        chain_id="coding_task",
    )

    result = await execute_node(
        {
            "message": "Implement X",
            "provider": "google",
            "model": "test-model",
            "session_id": "sess-test",
            "decision": decision,
        }
    )

    assert result["response"] == "ok"
    assert result["error"] is None
