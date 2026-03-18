"""Tests for orchestrator schema enums."""

from mindflow_backend.schemas.orchestrator import AgentType


def test_creative_agent_type_is_removed() -> None:
    assert not hasattr(AgentType, "CREATIVE")


def test_core_agent_types_exist() -> None:
    assert AgentType.ANALYST == "analyst"
    assert AgentType.CODER == "coder"
    assert AgentType.RESEARCHER == "researcher"
    assert AgentType.ORCHESTRATOR == "orchestrator"


def test_all_agent_types_count() -> None:
    assert len(AgentType) == 4
