"""Tests for HybridRouter — Two-Tier hybrid routing system.

Covers:
- Tier 1 direct delegation (high confidence)
- Tier 1 + Squad template (multi-agent, high confidence)
- Tier 2 auction escalation (low confidence)
- Targeted auction uses hint_agents
- Direct response (greetings)
- Fallback on error
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mindflow_backend.orchestrator.routing.squad_registry import (
    REFACTORING_SQUAD,
    SquadRegistry,
)
from mindflow_backend.schemas.orchestration.orchestrator import (
    AgentType,
    ExecutionStrategy,
    OrchestratorDecision,
)


# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------

def _make_intent(
    confidence: float = 0.9,
    is_multi_agent: bool = False,
    execution_strategy: ExecutionStrategy = ExecutionStrategy.DELEGATE,
    recommended_agent: AgentType = AgentType.CODER,
    agent_sequence: list[AgentType] | None = None,
    agent_sequence_ids: list[str] | None = None,
    recommended_agent_id: str | None = None,
    recommended_specialist: str | None = None,
    formulated_objective: str = "Implement feature X",
    user_intent: str = "User wants to implement feature X",
) -> MagicMock:
    """Build a mock IntentAnalysis object."""
    intent = MagicMock()
    intent.confidence = confidence
    intent.is_multi_agent = is_multi_agent
    intent.execution_strategy = execution_strategy
    intent.recommended_agent = recommended_agent
    intent.recommended_agent_id = recommended_agent_id
    intent.recommended_specialist = recommended_specialist
    intent.formulated_objective = formulated_objective
    intent.user_intent = user_intent
    intent.agent_sequence = agent_sequence or []
    intent.agent_sequence_ids = agent_sequence_ids or []
    return intent


# =========================================================================
# HybridRouter Tests
# =========================================================================


class TestHybridRouterTier1Direct:
    """Tests for Tier 1 direct delegation path (high confidence)."""

    @pytest.fixture
    def router(self):
        from mindflow_backend.orchestrator.routing.hybrid_router import HybridRouter
        return HybridRouter()

    @pytest.mark.asyncio
    async def test_high_confidence_single_agent_delegates_directly(
        self, router
    ) -> None:
        """High confidence + single agent → DELEGATE without auction."""
        intent = _make_intent(confidence=0.9, is_multi_agent=False)

        router.triage.analyze_intent_with_llm = AsyncMock(return_value=intent)
        router.auction.route_message = AsyncMock()  # must NOT be called

        decision = await router.route_message("Implement a new login endpoint")

        assert decision.execution_strategy == ExecutionStrategy.DELEGATE
        router.auction.route_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_direct_response_strategy_skips_auction(self, router) -> None:
        """DIRECT_RESPONSE strategy → no auction, returns orchestrator decision."""
        intent = _make_intent(
            confidence=0.95,
            execution_strategy=ExecutionStrategy.DIRECT_RESPONSE,
            recommended_agent=AgentType.ORCHESTRATOR,
        )

        router.triage.analyze_intent_with_llm = AsyncMock(return_value=intent)
        router.auction.route_message = AsyncMock()

        decision = await router.route_message("Olá, tudo bem?")

        assert decision.execution_strategy == ExecutionStrategy.DIRECT_RESPONSE
        assert decision.agent == AgentType.ORCHESTRATOR
        router.auction.route_message.assert_not_called()


class TestHybridRouterSquadPath:
    """Tests for Tier 1 Squad template path (high confidence + multi-agent)."""

    @pytest.fixture
    def router(self):
        from mindflow_backend.orchestrator.routing.hybrid_router import HybridRouter
        r = HybridRouter()
        # Mock a registry that always returns REFACTORING_SQUAD
        mock_registry = MagicMock(spec=SquadRegistry)
        mock_registry.find_squad.return_value = REFACTORING_SQUAD
        r._registry = mock_registry
        return r

    @pytest.mark.asyncio
    async def test_multi_agent_high_confidence_uses_squad(self, router) -> None:
        """Multi-agent + high confidence + squad match → TEAM_SESSION without auction."""
        intent = _make_intent(
            confidence=0.85,
            is_multi_agent=True,
            formulated_objective="Refactor the auth module removing code smells",
        )

        router.triage.analyze_intent_with_llm = AsyncMock(return_value=intent)
        router.auction.route_message = AsyncMock()

        decision = await router.route_message("Refactor auth module")

        assert decision.execution_strategy == ExecutionStrategy.TEAM_SESSION
        assert "squad_name" in decision.metadata
        assert decision.metadata["squad_name"] == REFACTORING_SQUAD.name
        router.auction.route_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_multi_agent_no_squad_match_falls_to_auction(self) -> None:
        """Multi-agent + high confidence + no squad match → escalate to Tier 2."""
        from mindflow_backend.orchestrator.routing.hybrid_router import HybridRouter

        router = HybridRouter()
        # Registry returns None (no squad found)
        mock_registry = MagicMock(spec=SquadRegistry)
        mock_registry.find_squad.return_value = None
        router._registry = mock_registry

        intent = _make_intent(
            confidence=0.88,
            is_multi_agent=True,
            agent_sequence=[AgentType.ANALYST, AgentType.CODER],
        )

        auction_decision = OrchestratorDecision(
            agent=AgentType.ANALYST,
            execution_strategy=ExecutionStrategy.TEAM_SESSION,
            rationale="Auction result",
        )

        router.triage.analyze_intent_with_llm = AsyncMock(return_value=intent)
        router.auction.route_message = AsyncMock(return_value=auction_decision)

        decision = await router.route_message("Complex multi-agent task")

        assert decision == auction_decision
        router.auction.route_message.assert_called_once()


class TestHybridRouterTier2Auction:
    """Tests for Tier 2 targeted auction path (low confidence)."""

    @pytest.fixture
    def router(self):
        from mindflow_backend.orchestrator.routing.hybrid_router import HybridRouter
        return HybridRouter()

    @pytest.mark.asyncio
    async def test_low_confidence_triggers_auction(self, router) -> None:
        """Low confidence → Tier 2 auction is called."""
        intent = _make_intent(
            confidence=0.4,  # below threshold
            recommended_agent=AgentType.ANALYST,
        )

        auction_decision = OrchestratorDecision(
            agent=AgentType.ANALYST,
            execution_strategy=ExecutionStrategy.DELEGATE,
            rationale="Auction selected analyst",
        )

        router.triage.analyze_intent_with_llm = AsyncMock(return_value=intent)
        router.auction.route_message = AsyncMock(return_value=auction_decision)

        decision = await router.route_message("Ambiguous and complex request")

        assert decision == auction_decision
        router.auction.route_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_tier2_receives_hint_agents_from_tier1(self, router) -> None:
        """Tier 2 auction receives hint_agents derived from Tier 1 intent."""
        intent = _make_intent(
            confidence=0.3,
            recommended_agent=AgentType.CODER,
            agent_sequence=[AgentType.ANALYST, AgentType.CODER],
        )

        auction_decision = OrchestratorDecision(
            agent=AgentType.CODER,
            execution_strategy=ExecutionStrategy.DELEGATE,
            rationale="Selected by auction",
        )

        router.triage.analyze_intent_with_llm = AsyncMock(return_value=intent)
        router.auction.route_message = AsyncMock(return_value=auction_decision)

        await router.route_message("Some request")

        # Verify auction was called with hint_agents
        call_kwargs = router.auction.route_message.call_args.kwargs
        assert "hint_agents" in call_kwargs
        # hint_agents should be derived from agent_sequence
        hints = call_kwargs["hint_agents"]
        assert "analyst" in hints or "coder" in hints

    @pytest.mark.asyncio
    async def test_confidence_exactly_at_threshold_goes_direct(self, router) -> None:
        """Confidence exactly at threshold (0.6) → direct delegation (not Tier 2)."""
        intent = _make_intent(confidence=0.6, is_multi_agent=False)

        router.triage.analyze_intent_with_llm = AsyncMock(return_value=intent)
        router.auction.route_message = AsyncMock()

        await router.route_message("Implement endpoint")

        # At threshold → direct, not auction
        router.auction.route_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_confidence_below_threshold_triggers_auction(self, router) -> None:
        """Confidence just below threshold (0.59) → auction triggered."""
        intent = _make_intent(confidence=0.59, is_multi_agent=False)

        auction_decision = OrchestratorDecision(
            agent=AgentType.ANALYST,
            execution_strategy=ExecutionStrategy.DELEGATE,
            rationale="Auction",
        )

        router.triage.analyze_intent_with_llm = AsyncMock(return_value=intent)
        router.auction.route_message = AsyncMock(return_value=auction_decision)

        await router.route_message("Implement endpoint")

        router.auction.route_message.assert_called_once()


class TestHybridRouterHintAgentExtraction:
    """Tests for _suggest_hint_agents logic."""

    @pytest.fixture
    def router(self):
        from mindflow_backend.orchestrator.routing.hybrid_router import HybridRouter
        return HybridRouter()

    def test_hints_from_agent_sequence_ids(self, router) -> None:
        intent = _make_intent(
            agent_sequence_ids=["custom_coder_001", "custom_analyst_002"],
        )
        hints = router._suggest_hint_agents(intent)
        assert hints == ["custom_coder_001", "custom_analyst_002"]

    def test_hints_from_agent_sequence(self, router) -> None:
        intent = _make_intent(
            agent_sequence=[AgentType.ANALYST, AgentType.CODER],
            agent_sequence_ids=[],
        )
        hints = router._suggest_hint_agents(intent)
        assert "analyst" in hints
        assert "coder" in hints

    def test_hints_from_recommended_agent_id(self, router) -> None:
        intent = _make_intent(
            recommended_agent_id="marketplace_agent_03",
            agent_sequence=[],
            agent_sequence_ids=[],
        )
        hints = router._suggest_hint_agents(intent)
        assert hints == ["marketplace_agent_03"]

    def test_hints_from_recommended_agent_fallback(self, router) -> None:
        intent = _make_intent(
            recommended_agent=AgentType.RESEARCHER,
            recommended_agent_id=None,
            agent_sequence=[],
            agent_sequence_ids=[],
        )
        hints = router._suggest_hint_agents(intent)
        assert "researcher" in hints

    def test_orchestrator_not_included_in_hints(self, router) -> None:
        intent = _make_intent(
            recommended_agent=AgentType.ORCHESTRATOR,
            recommended_agent_id=None,
            agent_sequence=[],
            agent_sequence_ids=[],
        )
        hints = router._suggest_hint_agents(intent)
        assert "orchestrator" not in hints


# =========================================================================
# Singleton Tests
# =========================================================================


class TestGetHybridRouter:
    """Tests for global singleton."""

    def test_singleton_returns_same_instance(self) -> None:
        from mindflow_backend.orchestrator.routing.hybrid_router import get_hybrid_router

        r1 = get_hybrid_router()
        r2 = get_hybrid_router()
        assert r1 is r2
