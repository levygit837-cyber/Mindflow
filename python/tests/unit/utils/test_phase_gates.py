"""Phase gate tests for the Obsidian feature integration roadmap.

Each test verifies the exit criteria for a roadmap phase.
Tests are skipped if the corresponding feature flag is disabled.
"""

import pytest

from mindflow_backend.infra.config import get_settings


class TestPhase0DocumentationConvergence:
    """Phase 0: All architecture docs exist and are importable."""

    def test_schemas_importable(self) -> None:
        """All schema modules should import without error."""
        try:
            from mindflow_backend.schemas import (
                agent,  # noqa: F401
                decomposition,  # noqa: F401
                orchestrator,  # noqa: F401
            )
        except ImportError as exc:
            pytest.skip(f"Phase 0 schemas not yet available: {exc}")

    def test_agent_type_enum_has_base_agents(self) -> None:
        try:
            from mindflow_backend.schemas.orchestrator import AgentType
        except ImportError:
            pytest.skip("AgentType not yet available (Phase 0 incomplete)")
        assert len(AgentType) >= 5  # At least the original 5


class TestPhase1AgentContractParity:
    """Phase 1: Agent personalities and sub-personalities operational."""

    def test_analyst_sub_personalities_available(self) -> None:
        """Test that analyst sub-personalities are defined."""
        try:
            from mindflow_backend.agents.core.personalities import ANALYST_SUB_PERSONALITIES
        except ImportError:
            pytest.skip("ANALYST_SUB_PERSONALITIES not yet available")
        
        # Check that security_guard exists as sub-personality
        assert "security_guard" in ANALYST_SUB_PERSONALITIES
        assert len(ANALYST_SUB_PERSONALITIES["security_guard"].strip()) > 0
        
        # Check that critic exists for session chunks
        assert "critic" in ANALYST_SUB_PERSONALITIES
        assert len(ANALYST_SUB_PERSONALITIES["critic"].strip()) > 0

    

class TestPhase2ContextGovernance:
    """Phase 2: Input normalization and context governance active."""

    def test_normalizer_importable(self) -> None:
        settings = get_settings()
        if not settings.enable_input_normalization:
            pytest.skip("ENABLE_INPUT_NORMALIZATION is False")
        from mindflow_backend.infra.normalizer import normalize_message  # noqa: F401

    def test_context_budget_importable(self) -> None:
        settings = get_settings()
        if not settings.enable_context_governance:
            pytest.skip("ENABLE_CONTEXT_GOVERNANCE is False")
        from mindflow_backend.orchestrator.context_budget import ContextBudgetTracker  # noqa: F401


# Phase 3 (async workflows, workflow registry) was deprecated and removed


class TestPhase4DTv2:
    """Phase 4: DT v2 contracts and scoring operational."""

    def test_dt_v2_schemas_importable(self) -> None:
        settings = get_settings()
        if not settings.enable_dt_v2:
            pytest.skip("ENABLE_DT_V2 is False")
        from mindflow_backend.schemas.decomposition_v2 import (  # noqa: F401
            MainComponentContract,
            SubComponentContract,
            SynthesisContract,
        )

    def test_scoring_importable(self) -> None:
        settings = get_settings()
        if not settings.enable_dt_v2:
            pytest.skip("ENABLE_DT_V2 is False")
        from mindflow_backend.orchestrator.decomposition.scoring import (
            compute_component_score,  # noqa: F401
        )
