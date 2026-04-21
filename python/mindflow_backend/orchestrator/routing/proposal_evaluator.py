"""Proposal Evaluator — Evaluates agent proposals and decides delegation.

Takes collected proposals and produces an OrchestratorDecision.
Uses heuristics first, LLM as fallback for complex cases.
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.orchestration.orchestrator import (
    AgentType,
    ExecutionStrategy,
    OrchestratorDecision,
    Priority,
    ThinkingLevel,
)
from mindflow_backend.schemas.orchestration.proposal import (
    AgentProposal,
    ProposalConfidence,
)
from mindflow_backend.schemas.orchestration.specialists import SpecialistType

_logger = get_logger(__name__)


def get_circuit_breaker(name: str) -> Any:
    """Resolve circuit breaker lazily to keep routing imports lightweight."""
    from mindflow_backend.infra.resilience.circuit_breaker.core import (
        get_circuit_breaker as _get_circuit_breaker,
    )

    return _get_circuit_breaker(name)


class ProposalEvaluator:
    """Evaluates agent proposals and produces routing decisions.

    Decision logic:
    - 0 proposals → DELEGATE back to orchestrator
    - 1 proposal → DELEGATE to that agent
    - N proposals, 1 clear winner → DELEGATE to winner
    - N proposals, close scores → LLM tiebreaker or TEAM_SESSION
    - Any proposal with needs_help_from → TEAM_SESSION
    """

    async def evaluate(
        self,
        proposals: list[AgentProposal],
        message: str,
    ) -> OrchestratorDecision:
        """Evaluate proposals and return routing decision.

        Args:
            proposals: List of agent proposals
            message: Original user message

        Returns:
            OrchestratorDecision with routing info
        """
        # Filter out unhealthy agents (circuit breaker check)
        healthy_proposals = self._filter_healthy(proposals)

        _logger.info(
            "proposal_evaluation_started",
            total=len(proposals),
            healthy=len(healthy_proposals),
        )

        # No proposals → delegate back to orchestrator
        if not healthy_proposals:
            _logger.info("no_proposals_fallback_orchestrator")
            return OrchestratorDecision(
                agent=AgentType.ORCHESTRATOR,
                agent_id="orchestrator",
                execution_strategy=ExecutionStrategy.DELEGATE,
                rationale="Nenhum agente se propôs a ajudar. A solicitação volta ao orquestrador.",
                task=message,
                confidence=0.5,
            )

        # Check for collaboration needs
        collaboration_proposals = [
            p for p in healthy_proposals if p.needs_help_from
        ]
        if collaboration_proposals:
            return self._team_session_decision(collaboration_proposals, healthy_proposals)

        # Single proposal → delegate directly
        if len(healthy_proposals) == 1:
            return self._single_proposal_decision(healthy_proposals[0])

        # Multiple proposals → find best
        return self._multi_proposal_decision(healthy_proposals, message)

    def _filter_healthy(self, proposals: list[AgentProposal]) -> list[AgentProposal]:
        """Filter out proposals from agents with open circuit breakers."""
        try:
            healthy = []
            for p in proposals:
                cb = get_circuit_breaker(f"agent_{p.agent_id}")
                if cb.state.name != "OPEN":
                    healthy.append(p)
                else:
                    _logger.warning(
                        "proposal_filtered_unhealthy",
                        agent=p.agent_id,
                        cb_state=cb.state.name,
                    )
            return healthy
        except Exception:
            # If circuit breaker not available, accept all
            return proposals

    def _single_proposal_decision(self, proposal: AgentProposal) -> OrchestratorDecision:
        """Create decision from single proposal."""
        agent_type = self._resolve_agent_type(proposal.agent_id)
        specialist = self._resolve_specialist(proposal.specialist)

        _logger.info(
            "single_proposal_accepted",
            agent=proposal.agent_id,
            confidence=proposal.confidence,
        )

        return OrchestratorDecision(
            agent=agent_type,
            specialist=specialist,
            execution_strategy=ExecutionStrategy.DELEGATE,
            task=proposal.suggested_task,
            rationale=f"Agente {proposal.agent_id} propôs: {proposal.reasoning or proposal.suggested_task}",
            confidence=proposal.confidence,
            priority=Priority.NORMAL if proposal.confidence >= 0.5 else Priority.LOW,
            thinking=ThinkingLevel.MEDIUM,
        )

    def _team_session_decision(
        self,
        collaboration: list[AgentProposal],
        all_proposals: list[AgentProposal],
    ) -> OrchestratorDecision:
        """Create TEAM_SESSION decision when collaboration is needed."""
        primary = max(collaboration, key=lambda p: p.confidence)
        agent_type = self._resolve_agent_type(primary.agent_id)
        specialist = self._resolve_specialist(primary.specialist)

        helpers = ", ".join(primary.needs_help_from)

        _logger.info(
            "team_session_decision",
            primary=primary.agent_id,
            helpers=helpers,
        )

        return OrchestratorDecision(
            agent=agent_type,
            specialist=specialist,
            execution_strategy=ExecutionStrategy.TEAM_SESSION,
            task=primary.suggested_task,
            rationale=(
                f"Agente {primary.agent_id} precisa de ajuda de {helpers}. "
                f"Iniciando sessão colaborativa."
            ),
            confidence=primary.confidence,
            priority=Priority.HIGH,
            thinking=ThinkingLevel.HIGH,
        )

    def _multi_proposal_decision(
        self,
        proposals: list[AgentProposal],
        message: str,
    ) -> OrchestratorDecision:
        """Handle multiple competing proposals."""
        # Sort by confidence (desc) then priority (asc)
        sorted_proposals = sorted(
            proposals,
            key=lambda p: (-p.confidence, p.priority),
        )

        best = sorted_proposals[0]
        second = sorted_proposals[1] if len(sorted_proposals) > 1 else None

        # Clear winner (confidence gap > 0.2)
        if second is None or (best.confidence - second.confidence) > 0.2:
            return self._single_proposal_decision(best)

        # Close scores → use heuristic or LLM tiebreaker
        return self._tiebreaker_decision(sorted_proposals, message)

    def _tiebreaker_decision(
        self,
        proposals: list[AgentProposal],
        message: str,
    ) -> OrchestratorDecision:
        """Break ties between close proposals.

        Heuristics:
        1. Prefer agent with more required_tools (more specialized)
        2. Prefer agent with higher self-priority
        3. If still tied, pick first (highest confidence)
        """
        # Heuristic 1: More tools = more specialized
        tool_counts = [(p, len(p.required_tools)) for p in proposals[:3]]
        tool_counts.sort(key=lambda x: -x[1])

        if tool_counts[0][1] > tool_counts[1][1]:
            winner = tool_counts[0][0]
            _logger.info("tiebreaker_tools", winner=winner.agent_id)
            return self._single_proposal_decision(winner)

        # Heuristic 2: Higher priority
        winner = min(proposals[:3], key=lambda p: p.priority)
        _logger.info("tiebreaker_priority", winner=winner.agent_id)
        return self._single_proposal_decision(winner)

    def _resolve_agent_type(self, agent_id: str) -> AgentType:
        """Resolve agent ID to AgentType enum."""
        try:
            return AgentType(agent_id)
        except ValueError:
            return AgentType.CODER

    def _resolve_specialist(self, specialist_str: str | None) -> SpecialistType | None:
        """Resolve specialist string to SpecialistType enum."""
        if not specialist_str:
            return None
        try:
            return SpecialistType(specialist_str)
        except ValueError:
            return None


# Singleton instance
_evaluator: ProposalEvaluator | None = None


def get_proposal_evaluator() -> ProposalEvaluator:
    """Get or create the global proposal evaluator."""
    global _evaluator
    if _evaluator is None:
        _evaluator = ProposalEvaluator()
    return _evaluator
