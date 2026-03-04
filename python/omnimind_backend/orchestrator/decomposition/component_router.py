"""DT v2 component-to-agent routing.

Maps component types to primary and fallback agent types as specified in
decomposition-thinking-contracts-v2.md.
"""

from __future__ import annotations

from enum import StrEnum

from omnimind_backend.schemas.orchestration.decomposition.decomposition_v2 import ComponentOwner


class ComponentType(StrEnum):
    """Types of work a DT component can represent."""

    CODE_IMPLEMENTATION = "code_implementation"
    ARCHITECTURE_DESIGN = "architecture_design"
    CODE_ANALYSIS = "code_analysis"
    EXTERNAL_RESEARCH = "external_research"
    QUALITY_REVIEW = "quality_review"
    SECURITY_ASSESSMENT = "security_assessment"


_PRIMARY_AGENT: dict[ComponentType, ComponentOwner] = {
    ComponentType.CODE_IMPLEMENTATION: ComponentOwner.CODER,
    ComponentType.ARCHITECTURE_DESIGN: ComponentOwner.ARCH_TECH,
    ComponentType.CODE_ANALYSIS: ComponentOwner.ANALYST,
    ComponentType.EXTERNAL_RESEARCH: ComponentOwner.RESEARCHER,
    ComponentType.QUALITY_REVIEW: ComponentOwner.CRITIC,
    ComponentType.SECURITY_ASSESSMENT: ComponentOwner.CRITIC,
}

_FALLBACK_AGENT: dict[ComponentType, ComponentOwner | None] = {
    ComponentType.CODE_IMPLEMENTATION: None,
    ComponentType.ARCHITECTURE_DESIGN: ComponentOwner.ANALYST,
    ComponentType.CODE_ANALYSIS: ComponentOwner.CODER,
    ComponentType.EXTERNAL_RESEARCH: None,
    ComponentType.QUALITY_REVIEW: ComponentOwner.ANALYST,
    ComponentType.SECURITY_ASSESSMENT: ComponentOwner.ANALYST,
}


def get_agent_for_component(component_type: ComponentType) -> ComponentOwner:
    """Return the primary agent for a given component type."""
    return _PRIMARY_AGENT[component_type]


def get_fallback_agent(component_type: ComponentType) -> ComponentOwner | None:
    """Return the fallback agent, or None if no fallback is available."""
    return _FALLBACK_AGENT.get(component_type)
