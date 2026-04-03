"""Decentralized Router — Main routing entry point.

Replaces the centralized IntelligentRouter with a proposal-based
system where agents volunteer for tasks. Falls back to
IntelligentRouter when no proposals are received.
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.orchestrator.routing.proposal_collector import (
    ProposalCollector,
    get_proposal_collector,
)
from mindflow_backend.orchestrator.routing.proposal_evaluator import (
    ProposalEvaluator,
    get_proposal_evaluator,
)
from mindflow_backend.schemas.orchestration.delegation import OrchestratorSession
from mindflow_backend.schemas.orchestration.orchestrator import (
    ExecutionStrategy,
    OrchestratorDecision,
)
from mindflow_backend.schemas.orchestration.workflow import WorkflowRouteDecision

_logger = get_logger(__name__)


class DecentralizedRouter:
    """Router descentralizado onde agentes propõem tarefas.

    Fluxo:
    1. Recebe mensagem do usuário
    2. Broadcast via CommunicationBus para todos os agentes
    3. Agentes avaliam e enviam propostas (timeout 5s)
    4. ProposalEvaluator decide a melhor delegação
    5. Fallback para IntelligentRouter se nenhum agente se propôs
    """

    def __init__(self) -> None:
        self.collector = get_proposal_collector()
        self.evaluator = get_proposal_evaluator()
        self._fallback_router: Any = None  # Lazy load IntelligentRouter

    @property
    def fallback(self) -> Any:
        """Lazy load IntelligentRouter as fallback."""
        if self._fallback_router is None:
            from mindflow_backend.orchestrator.routing.intelligent_router import (
                get_intelligent_router,
            )
            self._fallback_router = get_intelligent_router()
        return self._fallback_router

    async def route_message(
        self,
        message: str,
        session: OrchestratorSession | None = None,
        folder_path: str | None = None,
    ) -> OrchestratorDecision:
        """Route message using decentralized proposal system.

        Args:
            message: User message
            session: Current orchestrator session
            folder_path: Working directory

        Returns:
            OrchestratorDecision with routing info
        """
        settings = get_settings()
        timeout = getattr(settings, "proposal_timeout", 5.0)

        _logger.info(
            "decentralized_router_start",
            message_preview=message[:100],
            timeout=timeout,
        )

        # 1. Collect proposals from agents
        proposals = await self.collector.collect(
            message=message,
            session_id=session.session_id if session else "",
            folder_path=folder_path,
            timeout=timeout,
        )

        # 2. If proposals received, evaluate them
        if proposals:
            decision = await self.evaluator.evaluate(proposals, message)

            _logger.info(
                "decentralized_router_decided",
                strategy=decision.execution_strategy.value,
                agent=decision.agent.value,
                proposals_count=len(proposals),
            )
            return decision

        # 3. No proposals → fallback to IntelligentRouter
        _logger.info(
            "decentralized_router_fallback",
            reason="no_proposals",
        )
        return await self.fallback.route_message_intelligently(
            message=message,
            session=session,
            folder_path=folder_path,
        )

    async def route_message_strategy(
        self,
        message: str,
        session: OrchestratorSession | None = None,
        folder_path: str | None = None,
    ) -> WorkflowRouteDecision:
        """Route message and return WorkflowRouteDecision.

        Wraps route_message to match IntelligentRouter interface.
        """
        decision = await self.route_message(message, session, folder_path)

        return WorkflowRouteDecision(
            agent_role=decision.agent,
            specialist=decision.specialist,
            execution_strategy=decision.execution_strategy,
            task=decision.task,
            confidence=decision.confidence,
            tools=decision.tools,
            rationale=decision.rationale,
        )


# Singleton instance
_decentralized_router: DecentralizedRouter | None = None


def get_decentralized_router() -> DecentralizedRouter:
    """Get or create the global decentralized router."""
    global _decentralized_router
    if _decentralized_router is None:
        _decentralized_router = DecentralizedRouter()
    return _decentralized_router


async def route_message_decentralized(
    message: str,
    session: OrchestratorSession | None = None,
    folder_path: str | None = None,
) -> OrchestratorDecision:
    """Route a user message using the decentralized system.

    This is the main entry point replacing route_message_intelligently.
    """
    router = get_decentralized_router()
    return await router.route_message(message, session, folder_path)