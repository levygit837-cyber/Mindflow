from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from mindflow_backend.orchestrator.routing.orchestration_router import (
    OrchestrationRouter,
    RoutingContext,
)
from mindflow_backend.schemas.orchestration.orchestrator import (
    AgentType,
    ExecutionStrategy,
    OrchestratorDecision,
)


@pytest.mark.asyncio
async def test_forced_agent_type_uses_unified_delegate_path() -> None:
    router = OrchestrationRouter()

    decision = await router.route(
        RoutingContext(
            message="analise esta codebase",
            session_id="sess-1",
            agent_type="analyst",
            orchestrate=True,
        )
    )

    assert decision.execution_strategy == ExecutionStrategy.DELEGATE
    assert decision.agent_id_override == "analyst"
    assert decision.metadata["routing_mode"] == "forced_agent_type"


@pytest.mark.asyncio
async def test_legacy_direct_response_is_normalized_to_orchestrator_delegate(monkeypatch: pytest.MonkeyPatch) -> None:
    router = OrchestrationRouter()
    router._hybrid.route_message = AsyncMock(
        return_value=OrchestratorDecision(
            agent=AgentType.ORCHESTRATOR,
            agent_id="orchestrator",
            execution_strategy=ExecutionStrategy.DIRECT_RESPONSE,
            rationale="legacy greeting",
            task="oi",
            confidence=0.99,
            metadata={"source": "legacy"},
        )
    )

    decision = await router.route(
        RoutingContext(
            message="oi",
            session_id="sess-2",
            metadata={"entrypoint": "test"},
        )
    )

    assert decision.execution_strategy == ExecutionStrategy.DELEGATE
    assert decision.agent_id_override == "orchestrator"
    assert decision.metadata["legacy_execution_strategy"] == "direct_response"
    assert decision.metadata["entrypoint"] == "test"
