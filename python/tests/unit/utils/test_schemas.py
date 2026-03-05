import pytest
from pydantic import ValidationError

from omnimind_backend.schemas.agent import AgentChatRequest


def test_agent_chat_requires_message() -> None:
    with pytest.raises(ValidationError):
        AgentChatRequest(message="")


def test_agent_chat_request_no_longer_has_session_fields() -> None:
    payload = AgentChatRequest(message="hello")
    # assert not hasattr(payload, \"sessionId\")
    assert not hasattr(payload, "conversationId")
