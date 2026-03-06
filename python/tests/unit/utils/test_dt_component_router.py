"""Tests for DT v2 component-to-agent routing."""

from mindflow_backend.orchestrator.decomposition.component_router import (
    ComponentType,
    get_agent_for_component,
    get_fallback_agent,
)
from mindflow_backend.schemas.decomposition_v2 import ComponentOwner


def test_code_implementation_routes_to_coder() -> None:
    assert get_agent_for_component(ComponentType.CODE_IMPLEMENTATION) == ComponentOwner.CODER


def test_architecture_routes_to_arch_tech() -> None:
    assert get_agent_for_component(ComponentType.ARCHITECTURE_DESIGN) == ComponentOwner.ARCH_TECH


def test_code_analysis_routes_to_analyst() -> None:
    assert get_agent_for_component(ComponentType.CODE_ANALYSIS) == ComponentOwner.ANALYST


def test_external_research_routes_to_researcher() -> None:
    assert get_agent_for_component(ComponentType.EXTERNAL_RESEARCH) == ComponentOwner.RESEARCHER


def test_quality_review_routes_to_critic() -> None:
    assert get_agent_for_component(ComponentType.QUALITY_REVIEW) == ComponentOwner.CRITIC


def test_security_assessment_routes_to_critic() -> None:
    assert get_agent_for_component(ComponentType.SECURITY_ASSESSMENT) == ComponentOwner.CRITIC


def test_fallback_for_architecture() -> None:
    assert get_fallback_agent(ComponentType.ARCHITECTURE_DESIGN) == ComponentOwner.ANALYST


def test_no_fallback_for_coder() -> None:
    assert get_fallback_agent(ComponentType.CODE_IMPLEMENTATION) is None


def test_no_fallback_for_researcher() -> None:
    assert get_fallback_agent(ComponentType.EXTERNAL_RESEARCH) is None
