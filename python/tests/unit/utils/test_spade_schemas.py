"""Tests for SPADE coordination schemas."""

from uuid import uuid4

from mindflow_backend.schemas.spade import (
    AgentEnvelope,
    ExecutionMode,
    Intent,
    MessagePriority,
    Performative,
    ReasoningRequest,
    ReasoningResult,
    ReasoningStatus,
)


def test_agent_envelope_creation() -> None:
    env = AgentEnvelope(
        message_id=uuid4(),
        correlation_id=uuid4(),
        conversation_id="conv-123",
        sender_jid="orchestrator@mindflow",
        performative=Performative.REQUEST,
        intent=Intent.DELEGATE_TASK,
        payload={"task": "analyze code"},
    )
    assert env.schema_version == "spade.v1"
    assert env.execution_mode == ExecutionMode.AUTO
    assert env.priority == MessagePriority.NORMAL
    assert env.ttl_ms == 60000


def test_reasoning_request_creation() -> None:
    req = ReasoningRequest(
        request_id=uuid4(),
        task="Analyze the auth module",
        agent_type="analyst",
        thinking_mode="deep",
    )
    assert req.max_latency_ms == 2500
    assert req.allow_sync is True


def test_reasoning_result_ok() -> None:
    result = ReasoningResult(
        request_id=uuid4(),
        status=ReasoningStatus.OK,
        answer="The auth module uses JWT with RS256.",
        thoughts=["Checked auth/jwt.py", "Found RS256 config"],
    )
    assert result.status == ReasoningStatus.OK
    assert len(result.thoughts) == 2


def test_envelope_round_trip() -> None:
    env = AgentEnvelope(
        message_id=uuid4(),
        correlation_id=uuid4(),
        conversation_id="conv-456",
        sender_jid="coder@mindflow",
        recipient_jid="orchestrator@mindflow",
        performative=Performative.INFORM,
        intent=Intent.REASONING_RESULT,
        payload={"result": "done"},
    )
    data = env.model_dump(mode="json")
    restored = AgentEnvelope.model_validate(data)
    assert restored.sender_jid == "coder@mindflow"
    assert restored.schema_version == "spade.v1"
