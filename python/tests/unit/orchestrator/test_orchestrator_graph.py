"""Tests for orchestrator graph execution helpers."""

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
        "mindflow_backend.orchestrator.graph.get_settings",
        lambda: type(
            "S",
            (),
            {
                "default_provider": "test",
                "default_model": "test",
                "enable_decomposition_thinking": False,
                "memory_enabled": False,
                "working_path": None,
            },
        )(),
        raising=True,
    )

    class _FakeChain:
        async def execute(self, context):  # noqa: ANN001
            return {"response": "ok", "error": None, "context_seen": context}

    def _fake_get_chain(chain_id: str):  # noqa: ANN001
        assert chain_id == "coding_task"
        return _FakeChain()

    monkeypatch.setattr(
        "mindflow_backend.chains.catalog.get_chain",
        _fake_get_chain,
        raising=True,
    )

    decision = OrchestratorDecision(
        rationale="test",
        agent=AgentType.ORCHESTRATOR,
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
