"""Tests for orchestrator schema enums."""

from omnimind_backend.schemas.orchestrator import AgentType


def test_creative_agent_type_exists() -> None:
    assert AgentType.CREATIVE == "creative"


def test_security_guard_agent_type_exists() -> None:
    assert AgentType.SECURITY_GUARD == "security_guard"


def test_all_agent_types_count() -> None:
    assert len(AgentType) == 7  # 5 original + 2 new
