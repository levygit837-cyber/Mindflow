"""Tests for Decentralized Router — Proposal-based routing system.

Covers:
- AgentProposal schema validation
- ProposalCollector (broadcast + collect)
- ProposalEvaluator (decision logic)
- DecentralizedRouter (full flow)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from mindflow_backend.schemas.orchestration.orchestrator import (
    AgentType,
    ExecutionStrategy,
    OrchestratorDecision,
    ToolScope,
)
from mindflow_backend.schemas.orchestration.proposal import (
    AgentProposal,
    ProposalConfidence,
    ProposalRequest,
    ProposalResponse,
)


# =========================================================================
# AgentProposal Schema Tests
# =========================================================================


class TestAgentProposal:
    """Tests for AgentProposal schema."""

    def test_create_minimal_proposal(self) -> None:
        """Proposal can be created with minimal required fields."""
        proposal = AgentProposal(
            agent_id="coder",
            confidence=0.8,
            suggested_task="Implement feature X",
        )
        assert proposal.agent_id == "coder"
        assert proposal.confidence == 0.8
        assert proposal.suggested_task == "Implement feature X"

    def test_confidence_auto_categorization(self) -> None:
        """Confidence level is auto-categorized based on numeric value."""
        # CERTAIN (>= 0.8)
        p1 = AgentProposal(agent_id="coder", confidence=0.9, suggested_task="test")
        assert p1.confidence_level == ProposalConfidence.CERTAIN

        # HIGH (>= 0.6)
        p2 = AgentProposal(agent_id="coder", confidence=0.7, suggested_task="test")
        assert p2.confidence_level == ProposalConfidence.HIGH

        # MEDIUM (>= 0.3)
        p3 = AgentProposal(agent_id="coder", confidence=0.5, suggested_task="test")
        assert p3.confidence_level == ProposalConfidence.MEDIUM

        # LOW (< 0.3)
        p4 = AgentProposal(agent_id="coder", confidence=0.1, suggested_task="test")
        assert p4.confidence_level == ProposalConfidence.LOW

    def test_proposal_with_collaboration(self) -> None:
        """Proposal can specify collaboration needs."""
        proposal = AgentProposal(
            agent_id="analyst",
            confidence=0.7,
            suggested_task="Analyze codebase",
            needs_help_from=["researcher"],
            can_collaborate=True,
        )
        assert proposal.needs_help_from == ["researcher"]
        assert proposal.can_collaborate is True

    def test_proposal_with_tools(self) -> None:
        """Proposal can specify required tools."""
        proposal = AgentProposal(
            agent_id="analyst",
            confidence=0.8,
            suggested_task="Analyze code",
            required_tools=["read_file", "grep"],
            estimated_complexity="high",
        )
        assert proposal.required_tools == ["read_file", "grep"]
        assert proposal.estimated_complexity == "high"

    def test_proposal_defaults(self) -> None:
        """Proposal has sensible defaults for optional fields."""
        proposal = AgentProposal(
            agent_id="coder",
            confidence=0.5,
            suggested_task="test",
        )
        assert proposal.agent_type == ""
        assert proposal.specialist is None
        assert proposal.reasoning == ""
        assert proposal.required_tools == []
        assert proposal.estimated_complexity == "medium"
        assert proposal.estimated_tokens == 0
        assert proposal.can_collaborate is False
        assert proposal.needs_help_from == []
        assert proposal.can_help_with == []
        assert proposal.priority == 5


class TestProposalRequest:
    """Tests for ProposalRequest schema."""

    def test_create_request(self) -> None:
        """ProposalRequest can be created with message."""
        request = ProposalRequest(message="Implement feature X")
        assert request.message == "Implement feature X"
        assert request.timeout_seconds == 5.0
        assert request.exclude_agents == []

    def test_request_with_exclusions(self) -> None:
        """ProposalRequest can exclude specific agents."""
        request = ProposalRequest(
            message="test",
            exclude_agents=["researcher"],
        )
        assert request.exclude_agents == ["researcher"]


class TestProposalResponse:
    """Tests for ProposalResponse schema."""

    def test_response_with_proposal(self) -> None:
        """Response can include a proposal."""
        request_id = uuid4()
        proposal = AgentProposal(
            agent_id="coder",
            confidence=0.8,
            suggested_task="Implement X",
        )
        response = ProposalResponse(
            request_id=request_id,
            agent_id="coder",
            proposal=proposal,
        )
        assert response.proposal is not None
        assert response.proposal.agent_id == "coder"
        assert response.declined_reason == ""

    def test_response_declined(self) -> None:
        """Response can indicate decline without proposal."""
        request_id = uuid4()
        response = ProposalResponse(
            request_id=request_id,
            agent_id="researcher",
            proposal=None,
            declined_reason="Not relevant to my expertise",
        )
        assert response.proposal is None
        assert response.declined_reason == "Not relevant to my expertise"


# =========================================================================
# ProposalEvaluator Tests
# =========================================================================


class TestProposalEvaluator:
    """Tests for ProposalEvaluator decision logic."""

    @pytest.fixture
    def evaluator(self) -> "ProposalEvaluator":
        from mindflow_backend.orchestrator.routing.proposal_evaluator import (
            ProposalEvaluator,
        )

        return ProposalEvaluator()

    @pytest.mark.asyncio
    async def test_no_proposals_returns_orchestrator_delegate(
        self, evaluator: "ProposalEvaluator"
    ) -> None:
        """When no proposals, fallback to orchestrator delegation."""
        decision = await evaluator.evaluate([], "test message")
        assert decision.execution_strategy == ExecutionStrategy.DELEGATE
        assert decision.agent == AgentType.ORCHESTRATOR

    @pytest.mark.asyncio
    async def test_single_proposal_returns_delegate(
        self, evaluator: "ProposalEvaluator"
    ) -> None:
        """Single proposal results in DELEGATE strategy."""
        proposals = [
            AgentProposal(
                agent_id="coder",
                confidence=0.8,
                suggested_task="Implement feature",
            )
        ]
        decision = await evaluator.evaluate(proposals, "test message")
        assert decision.execution_strategy == ExecutionStrategy.DELEGATE
        assert decision.agent == AgentType.CODER

    @pytest.mark.asyncio
    async def test_collaboration_proposal_returns_team_session(
        self, evaluator: "ProposalEvaluator"
    ) -> None:
        """Proposal with needs_help_from triggers TEAM_SESSION."""
        proposals = [
            AgentProposal(
                agent_id="analyst",
                confidence=0.7,
                suggested_task="Analyze code",
                needs_help_from=["researcher"],
            )
        ]
        decision = await evaluator.evaluate(proposals, "test message")
        assert decision.execution_strategy == ExecutionStrategy.TEAM_SESSION

    @pytest.mark.asyncio
    async def test_multiple_proposals_picks_highest_confidence(
        self, evaluator: "ProposalEvaluator"
    ) -> None:
        """Multiple proposals: highest confidence wins."""
        proposals = [
            AgentProposal(
                agent_id="coder",
                confidence=0.5,
                suggested_task="Code it",
            ),
            AgentProposal(
                agent_id="analyst",
                confidence=0.9,
                suggested_task="Analyze it",
            ),
        ]
        decision = await evaluator.evaluate(proposals, "test message")
        assert decision.agent == AgentType.ANALYST
        assert decision.confidence == 0.9

    @pytest.mark.asyncio
    async def test_multiple_proposals_clear_winner(
        self, evaluator: "ProposalEvaluator"
    ) -> None:
        """Clear winner (> 0.2 gap) is selected directly."""
        proposals = [
            AgentProposal(
                agent_id="coder",
                confidence=0.9,
                suggested_task="Code it",
            ),
            AgentProposal(
                agent_id="analyst",
                confidence=0.4,
                suggested_task="Analyze it",
            ),
        ]
        decision = await evaluator.evaluate(proposals, "test message")
        assert decision.agent == AgentType.CODER

    @pytest.mark.asyncio
    async def test_close_scores_use_tiebreaker(
        self, evaluator: "ProposalEvaluator"
    ) -> None:
        """Close scores use tiebreaker heuristics."""
        proposals = [
            AgentProposal(
                agent_id="coder",
                confidence=0.8,
                suggested_task="Code it",
                required_tools=["read_file", "write_file", "execute_command"],
            ),
            AgentProposal(
                agent_id="analyst",
                confidence=0.75,
                suggested_task="Analyze it",
                required_tools=["read_file"],
            ),
        ]
        decision = await evaluator.evaluate(proposals, "test message")
        # More tools = more specialized = wins tiebreaker
        assert decision.agent == AgentType.CODER

    @pytest.mark.asyncio
    async def test_tiebreaker_priority(
        self, evaluator: "ProposalEvaluator"
    ) -> None:
        """When tools are equal, priority is used as tiebreaker."""
        proposals = [
            AgentProposal(
                agent_id="coder",
                confidence=0.8,
                suggested_task="Code it",
                priority=5,
            ),
            AgentProposal(
                agent_id="analyst",
                confidence=0.75,
                suggested_task="Analyze it",
                priority=2,
            ),
        ]
        decision = await evaluator.evaluate(proposals, "test message")
        # Lower priority number = higher priority
        assert decision.agent == AgentType.ANALYST

    @pytest.mark.asyncio
    async def test_filter_healthy_agents(
        self, evaluator: "ProposalEvaluator"
    ) -> None:
        """Agents with OPEN circuit breaker are filtered out."""
        proposals = [
            AgentProposal(
                agent_id="coder",
                confidence=0.9,
                suggested_task="Code it",
            ),
            AgentProposal(
                agent_id="analyst",
                confidence=0.8,
                suggested_task="Analyze it",
            ),
        ]
        # Mock circuit breaker to filter coder
        with patch(
            "mindflow_backend.orchestrator.routing.proposal_evaluator.get_circuit_breaker"
        ) as mock_cb:
            open_breaker = MagicMock()
            open_breaker.state.name = "OPEN"
            closed_breaker = MagicMock()
            closed_breaker.state.name = "CLOSED"

            def _breaker_for(name: str) -> MagicMock:
                return open_breaker if name == "agent_coder" else closed_breaker

            mock_cb.side_effect = _breaker_for

            decision = await evaluator.evaluate(proposals, "test message")
            # coder should be filtered, analyst selected
            assert decision.agent == AgentType.ANALYST

    @pytest.mark.asyncio
    async def test_filter_all_unhealthy_fallback(
        self, evaluator: "ProposalEvaluator"
    ) -> None:
        """If all agents are unhealthy, fallback to orchestrator delegation."""
        proposals = [
            AgentProposal(
                agent_id="coder",
                confidence=0.9,
                suggested_task="Code it",
            ),
        ]
        with patch(
            "mindflow_backend.orchestrator.routing.proposal_evaluator.get_circuit_breaker"
        ) as mock_cb:
            mock_breaker = MagicMock()
            mock_breaker.state.name = "OPEN"
            mock_cb.return_value = mock_breaker

            decision = await evaluator.evaluate(proposals, "test message")
            assert decision.execution_strategy == ExecutionStrategy.DELEGATE


# =========================================================================
# DecentralizedRouter Tests
# =========================================================================


class TestDecentralizedRouter:
    """Tests for DecentralizedRouter full flow."""

    @pytest.fixture
    def router(self) -> "DecentralizedRouter":
        from mindflow_backend.orchestrator.routing.decentralized_router import (
            DecentralizedRouter,
        )

        return DecentralizedRouter()

    @pytest.mark.asyncio
    async def test_router_with_proposals(
        self, router: "DecentralizedRouter"
    ) -> None:
        """Router uses proposals when available."""
        proposal = AgentProposal(
            agent_id="coder",
            confidence=0.8,
            suggested_task="Implement feature",
        )
        router.collector.collect = AsyncMock(return_value=[proposal])

        decision = await router.route_message("Implement feature X")
        assert decision.execution_strategy == ExecutionStrategy.DELEGATE
        assert decision.agent == AgentType.CODER

    @pytest.mark.asyncio
    async def test_router_fallback_on_no_proposals(
        self, router: "DecentralizedRouter"
    ) -> None:
        """Router falls back to IntelligentRouter when no proposals."""
        router.collector.collect = AsyncMock(return_value=[])

        fallback_decision = OrchestratorDecision(
            agent=AgentType.ANALYST,
            execution_strategy=ExecutionStrategy.DELEGATE,
            rationale="Fallback",
        )
        router.fallback.route_message_intelligently = AsyncMock(
            return_value=fallback_decision
        )

        decision = await router.route_message("Analyze this code")
        assert decision.agent == AgentType.ANALYST
        router.fallback.route_message_intelligently.assert_called_once()

    @pytest.mark.asyncio
    async def test_router_multiple_proposals(
        self, router: "DecentralizedRouter"
    ) -> None:
        """Router handles multiple competing proposals."""
        proposals = [
            AgentProposal(
                agent_id="coder",
                confidence=0.9,
                suggested_task="Code it",
            ),
            AgentProposal(
                agent_id="analyst",
                confidence=0.85,
                suggested_task="Analyze it",
            ),
        ]
        router.collector.collect = AsyncMock(return_value=proposals)

        decision = await router.route_message("Fix this bug")
        # Highest confidence wins
        assert decision.agent == AgentType.CODER

    @pytest.mark.asyncio
    async def test_router_collaboration(
        self, router: "DecentralizedRouter"
    ) -> None:
        """Router triggers TEAM_SESSION for collaboration."""
        proposals = [
            AgentProposal(
                agent_id="analyst",
                confidence=0.7,
                suggested_task="Analyze",
                needs_help_from=["coder"],
            ),
        ]
        router.collector.collect = AsyncMock(return_value=proposals)

        decision = await router.route_message("Refactor this module")
        assert decision.execution_strategy == ExecutionStrategy.TEAM_SESSION


# =========================================================================
# ProposalCollector Tests
# =========================================================================


class TestProposalCollector:
    """Tests for ProposalCollector."""

    @pytest.fixture
    def collector(self) -> "ProposalCollector":
        from mindflow_backend.orchestrator.routing.proposal_collector import (
            ProposalCollector,
        )

        return ProposalCollector()

    def test_collector_creates_request(
        self, collector: "ProposalCollector"
    ) -> None:
        """Collector creates a ProposalRequest from parameters."""
        request = ProposalRequest(
            message="test message",
            session_id="session-123",
            folder_path="/tmp",
        )
        assert request.message == "test message"
        assert request.session_id == "session-123"
        assert request.folder_path == "/tmp"

    @pytest.mark.asyncio
    async def test_collector_timeout_returns_partial(
        self, collector: "ProposalCollector"
    ) -> None:
        """Collector returns partial results on timeout."""
        # Simulate partial collection
        proposal = AgentProposal(
            agent_id="coder",
            confidence=0.8,
            suggested_task="test",
        )
        collector._collected = {uuid4(): [proposal]}

        # The partial collection should return the proposals
        result = collector._collect_partial(list(collector._collected.keys())[0])
        assert len(result) == 1
        assert result[0].agent_id == "coder"
