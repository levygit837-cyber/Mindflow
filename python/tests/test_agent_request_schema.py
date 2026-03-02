from omnimind_backend.schemas.agent import AgentChatRequest


def test_agent_request_accepts_agent_type_and_agent_alias() -> None:
    by_name = AgentChatRequest.model_validate({"message": "oi", "agent_type": "coder"})
    by_alias = AgentChatRequest.model_validate({"message": "oi", "agent": "coder"})

    assert by_name.agent_type == "coder"
    assert by_alias.agent_type == "coder"
