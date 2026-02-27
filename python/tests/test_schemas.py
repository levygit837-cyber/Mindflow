import pytest
from pydantic import ValidationError

from omnimind_backend.schemas.agent import AgentChatRequest, MindSandboxQueryRequest, SessionCreate


def test_agent_chat_requires_message() -> None:
    with pytest.raises(ValidationError):
        AgentChatRequest(message="")


def test_session_create_defaults_topic_type() -> None:
    payload = SessionCreate()
    assert payload.topic_type == "standalone"


def test_mind_sandbox_requires_session_ids() -> None:
    with pytest.raises(ValidationError):
        MindSandboxQueryRequest(sessionIds=[])
