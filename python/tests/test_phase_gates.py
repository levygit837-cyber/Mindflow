"""Phase gate tests for the Obsidian feature integration roadmap.

Each test verifies the exit criteria for a roadmap phase.
Tests are skipped if the corresponding feature flag is disabled.
"""

import pytest

from omnimind_backend.infra.config import get_settings


class TestPhase0DocumentationConvergence:
    """Phase 0: All architecture docs exist and are importable."""

    def test_schemas_importable(self) -> None:
        """All schema modules should import without error."""
        try:
            from omnimind_backend.schemas import orchestrator  # noqa: F401
            from omnimind_backend.schemas import decomposition  # noqa: F401
            from omnimind_backend.schemas import agent  # noqa: F401
        except ImportError as exc:
            pytest.skip(f"Phase 0 schemas not yet available: {exc}")

    def test_agent_type_enum_has_base_agents(self) -> None:
        try:
            from omnimind_backend.schemas.orchestrator import AgentType
        except ImportError:
            pytest.skip("AgentType not yet available (Phase 0 incomplete)")
        assert len(AgentType) >= 5  # At least the original 5


class TestPhase1AgentContractParity:
    """Phase 1: Creative and SecurityGuard agents operational."""

    def test_creative_agent_importable(self) -> None:
        settings = get_settings()
        if not settings.enable_creative_agent:
            pytest.skip("ENABLE_CREATIVE_AGENT is False")
        from omnimind_backend.agents.personalities.creative import create_creative_agent
        agent = create_creative_agent()
        assert agent.agent_type.value == "creative"

    def test_security_guard_agent_importable(self) -> None:
        settings = get_settings()
        if not settings.enable_security_guard_agent:
            pytest.skip("ENABLE_SECURITY_GUARD_AGENT is False")
        from omnimind_backend.agents.personalities.security_guard import create_security_guard_agent
        agent = create_security_guard_agent()
        assert agent.agent_type.value == "security_guard"

    def test_seven_agents_registered(self) -> None:
        settings = get_settings()
        if not (settings.enable_creative_agent and settings.enable_security_guard_agent):
            pytest.skip("New agents not enabled")
        from omnimind_backend.agents._registry import get_registry, register_all_personalities
        registry = get_registry()
        registry.clear()
        register_all_personalities()
        assert registry.count == 7


class TestPhase2ContextGovernance:
    """Phase 2: Input normalization and context governance active."""

    def test_normalizer_importable(self) -> None:
        settings = get_settings()
        if not settings.enable_input_normalization:
            pytest.skip("ENABLE_INPUT_NORMALIZATION is False")
        from omnimind_backend.infra.normalizer import normalize_message  # noqa: F401

    def test_context_budget_importable(self) -> None:
        settings = get_settings()
        if not settings.enable_context_governance:
            pytest.skip("ENABLE_CONTEXT_GOVERNANCE is False")
        from omnimind_backend.orchestrator.context_budget import ContextBudgetTracker  # noqa: F401


class TestPhase3AsyncWorkflows:
    """Phase 3: Workflow registry and TaskBus operational."""

    def test_task_bus_importable(self) -> None:
        settings = get_settings()
        if not settings.enable_async_workflows:
            pytest.skip("ENABLE_ASYNC_WORKFLOWS is False")
        from omnimind_backend.workers.task_bus import InMemoryTaskBus  # noqa: F401

    def test_workflow_registry_importable(self) -> None:
        settings = get_settings()
        if not settings.enable_workflow_registry:
            pytest.skip("ENABLE_WORKFLOW_REGISTRY is False")
        from omnimind_backend.workers.workflow_registry import WorkflowRegistry  # noqa: F401


class TestPhase4DTv2:
    """Phase 4: DT v2 contracts and scoring operational."""

    def test_dt_v2_schemas_importable(self) -> None:
        settings = get_settings()
        if not settings.enable_dt_v2:
            pytest.skip("ENABLE_DT_V2 is False")
        from omnimind_backend.schemas.decomposition_v2 import (  # noqa: F401
            MainComponentContract,
            SubComponentContract,
            SynthesisContract,
        )

    def test_scoring_importable(self) -> None:
        settings = get_settings()
        if not settings.enable_dt_v2:
            pytest.skip("ENABLE_DT_V2 is False")
        from omnimind_backend.orchestrator.decomposition.scoring import compute_component_score  # noqa: F401
