"""Tests for specialist identity payloads in runtime streaming helpers."""

import json

from mindflow_backend.runtime.streaming.stream import AgentRuntime
from mindflow_backend.schemas.orchestration.orchestrator import (
    AgentType,
    ExecutionStrategy,
    OrchestratorDecision,
)
from mindflow_backend.schemas.orchestration.specialists import SpecialistType


def test_decision_payload_includes_specialist_and_agent_id() -> None:
    runtime = AgentRuntime()
    decision = OrchestratorDecision(
        agent=AgentType.ANALYST,
        specialist=SpecialistType.CRITIC,
        task="Review code",
        execution_strategy=ExecutionStrategy.SINGLE_AGENT,
    )

    payload = runtime._decision_payload(decision)

    assert payload["agent_type"] == "ANALYST"
    assert payload["agent_id"] == "analyst:critic"
    assert payload["specialist"] == "critic"


def test_serialize_decision_keeps_agent_identity_fields() -> None:
    runtime = AgentRuntime()
    decision = OrchestratorDecision(
        agent=AgentType.ANALYST,
        specialist=SpecialistType.DEEP_ITERATION,
        task="Analyze deeply",
    )

    serialized = json.loads(runtime._serialize_decision(decision))

    assert serialized["agent_id"] == "analyst:deep_iteration"
    assert serialized["specialist"] == "deep_iteration"
