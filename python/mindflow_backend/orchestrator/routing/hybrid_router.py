"""HybridRouter — Roteador híbrido Two-Tier para MindFlow.

Tier 1: Triagem rápida via IntelligentRouter (1 chamada LLM barata)
Tier 2: Targeted Auction via DecentralizedRouter (acionado apenas quando necessário)

Fluxo de decisão:
    confidence >= threshold AND is_multi_agent=False → DELEGATE direto
    confidence >= threshold AND is_multi_agent=True  → Squad template (TEAM_SESSION)
    confidence <  threshold                          → Targeted Auction (Tier 2)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.orchestrator.routing.routing_metrics import RoutingMetrics
from mindflow_backend.orchestrator.routing.squad_registry import (
    SquadTemplate,
    get_squad_registry,
)
from mindflow_backend.schemas.orchestration.orchestrator import (
    AgentType,
    ExecutionStrategy,
    OrchestratorDecision,
)

if TYPE_CHECKING:
    from mindflow_backend.orchestrator.routing.decentralized_router import DecentralizedRouter
    from mindflow_backend.orchestrator.routing.intelligent_router import (
        IntelligentRouter,
        IntentAnalysis,
    )
    from mindflow_backend.schemas.orchestration.delegation import OrchestratorSession

_logger = get_logger(__name__)

# Confiança mínima para delegação direta sem leilão
DEFAULT_CONFIDENCE_THRESHOLD = 0.6


class HybridRouter:
    """Roteador híbrido Two-Tier.

    Orquestra IntelligentRouter (Tier 1) e DecentralizedRouter (Tier 2)
    para minimizar tokens gastos em roteamento sem perder precisão.
    """

    def __init__(self) -> None:
        self._triage: IntelligentRouter | None = None      # lazy
        self._auction: DecentralizedRouter | None = None   # lazy
        self._registry = get_squad_registry()

    # ------------------------------------------------------------------
    # Lazy loaders
    # ------------------------------------------------------------------

    @property
    def triage(self) -> IntelligentRouter:
        if self._triage is None:
            from mindflow_backend.orchestrator.routing.intelligent_router import (
                get_intelligent_router,
            )
            self._triage = get_intelligent_router()
        return self._triage

    @property
    def auction(self) -> DecentralizedRouter:
        if self._auction is None:
            from mindflow_backend.orchestrator.routing.decentralized_router import (
                get_decentralized_router,
            )
            self._auction = get_decentralized_router()
        return self._auction

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def route_message(
        self,
        message: str,
        session: OrchestratorSession | None = None,
        folder_path: str | None = None,
    ) -> OrchestratorDecision:
        """Rota uma mensagem usando a estratégia híbrida Two-Tier.

        Args:
            message: Mensagem do usuário.
            session: Sessão do orquestrador (opcional).
            folder_path: Caminho do workspace (opcional).

        Returns:
            OrchestratorDecision com a estratégia e agente escolhidos.
        """
        settings = get_settings()
        threshold = getattr(settings, "hybrid_confidence_threshold", DEFAULT_CONFIDENCE_THRESHOLD)
        metrics = RoutingMetrics(message_preview=message[:100])

        _logger.info(
            "hybrid_router_start",
            message_preview=message[:100],
            threshold=threshold,
        )

        # --- TIER 1: Triagem Rápida ---
        session_context = ""
        session_id = None
        if session is not None:
            session_context = (
                session.session_checkpoints[-1] if session.session_checkpoints else ""
            )
            session_id = str(session.session_id)

        intent = await self.triage.analyze_intent_with_llm(
            message,
            session_context=session_context,
            folder_path=folder_path,
            has_folder_path=bool(folder_path),
            session_id=session_id,
        )

        metrics.triage_confidence = intent.confidence
        metrics.triage_tokens_estimated = _estimate_tokens(message)

        _logger.info(
            "hybrid_router_tier1_complete",
            confidence=intent.confidence,
            is_multi_agent=intent.is_multi_agent,
            strategy=intent.execution_strategy.value,
            recommended_agent=intent.recommended_agent.value,
        )

        # --- Decisão baseada em confiança ---
        if intent.confidence >= threshold:
            # Alta confiança → decidir direto sem leilão
            decision = await self._resolve_high_confidence(
                intent=intent,
                message=message,
                session=session,
                folder_path=folder_path,
                metrics=metrics,
                session_id=session_id,
            )
        else:
            # Baixa confiança → escalar para Tier 2 (Targeted Auction)
            decision = await self._resolve_via_auction(
                intent=intent,
                message=message,
                session=session,
                folder_path=folder_path,
                metrics=metrics,
            )

        metrics.finish()
        _logger.info("hybrid_router_decision", **metrics.as_log_dict())
        return decision

    # ------------------------------------------------------------------
    # Tier 1 high-confidence paths
    # ------------------------------------------------------------------

    async def _resolve_high_confidence(
        self,
        intent: IntentAnalysis,
        message: str,
        session: OrchestratorSession | None,
        folder_path: str | None,
        metrics: RoutingMetrics,
        session_id: str | None,
    ) -> OrchestratorDecision:
        """Resolve routing com alta confiança sem acionar o leilão."""
        # Direct response (saudações, etc.)
        if intent.execution_strategy == ExecutionStrategy.DIRECT_RESPONSE:
            metrics.tier_used = "tier1_direct"
            metrics.agents_consulted = 0
            return self._build_direct_decision(intent)

        # Multi-agente com alta confiança → tentar Squad template
        if intent.is_multi_agent:
            return await self._resolve_squad_or_auction(
                intent=intent,
                message=message,
                session=session,
                folder_path=folder_path,
                metrics=metrics,
            )

        # Delegação direta para 1 agente
        metrics.tier_used = "tier1_direct"
        metrics.agents_consulted = 1
        return self._build_delegate_decision(intent, session_id)

    async def _resolve_squad_or_auction(
        self,
        intent: IntentAnalysis,
        message: str,
        session: OrchestratorSession | None,
        folder_path: str | None,
        metrics: RoutingMetrics,
    ) -> OrchestratorDecision:
        """Tenta usar Squad template; caso não encontre, escalona para leilão."""
        search_text = intent.formulated_objective or message
        squad = self._registry.find_squad(search_text)

        if squad is not None:
            metrics.tier_used = "tier1_squad"
            metrics.squad_template = squad.name
            metrics.agents_consulted = len(squad.agent_ids)
            _logger.info(
                "hybrid_router_squad_match",
                squad=squad.name,
                agents=list(squad.agent_ids),
            )
            return self._build_squad_decision(squad, intent)

        # Sem squad → delegar para Tier 2 com hints dos agent_sequence do intent
        _logger.info(
            "hybrid_router_no_squad_fallback_auction",
            intent_agents=[a.value for a in intent.agent_sequence],
        )
        return await self._resolve_via_auction(
            intent=intent,
            message=message,
            session=session,
            folder_path=folder_path,
            metrics=metrics,
        )

    # ------------------------------------------------------------------
    # Tier 2: Targeted Auction
    # ------------------------------------------------------------------

    async def _resolve_via_auction(
        self,
        intent: IntentAnalysis,
        message: str,
        session: OrchestratorSession | None,
        folder_path: str | None,
        metrics: RoutingMetrics,
    ) -> OrchestratorDecision:
        """Aciona o leilão descentralizado com hints do Tier 1."""
        hint_agents = self._suggest_hint_agents(intent)
        metrics.tier_used = "tier2_auction"
        metrics.hint_agents = hint_agents
        metrics.agents_consulted = len(hint_agents) if hint_agents else 0
        metrics.auction_tokens_estimated = _estimate_tokens(message) * max(1, len(hint_agents or []))

        _logger.info(
            "hybrid_router_tier2_start",
            hint_agents=hint_agents,
        )

        return await self.auction.route_message(
            message=message,
            session=session,
            folder_path=folder_path,
            hint_agents=hint_agents or None,
        )

    # ------------------------------------------------------------------
    # Decision builders
    # ------------------------------------------------------------------

    def _build_direct_decision(self, intent: IntentAnalysis) -> OrchestratorDecision:
        """Constrói decisão de resposta direta."""
        return OrchestratorDecision(
            agent=AgentType.ORCHESTRATOR,
            execution_strategy=ExecutionStrategy.DIRECT_RESPONSE,
            rationale="Direct response: no agent delegation needed",
            confidence=intent.confidence,
        )

    def _build_delegate_decision(
        self,
        intent: IntentAnalysis,
        session_id: str | None = None,
    ) -> OrchestratorDecision:
        """Constrói decisão de delegação a um único agente."""
        from contextlib import suppress

        from mindflow_backend.agents.specialists.runtime_policy import (
            get_agent_runtime_policy,
        )
        from mindflow_backend.schemas.orchestration.orchestrator import SpecialistType

        target_agent = intent.recommended_agent
        specialist = None
        agent_id_override = intent.recommended_agent_id

        with suppress(ValueError):
            if intent.recommended_specialist:
                specialist = SpecialistType(intent.recommended_specialist)

        if agent_id_override:
            with suppress(KeyError, ValueError):
                policy = get_agent_runtime_policy(
                    agent_id=agent_id_override,
                    session_id=session_id,
                )
                target_agent = policy.agent_role
                specialist = policy.specialist

        return OrchestratorDecision(
            agent=target_agent,
            specialist=specialist,
            agent_id_override=agent_id_override,
            execution_strategy=ExecutionStrategy.DELEGATE,
            rationale=(
                f"Tier-1 direct delegation to {agent_id_override or target_agent.value} "
                f"(confidence: {intent.confidence:.0%})"
            ),
            task=intent.formulated_objective,
            confidence=intent.confidence,
        )

    def _build_squad_decision(
        self,
        squad: SquadTemplate,
        intent: IntentAnalysis,
    ) -> OrchestratorDecision:
        """Constrói decisão de team session usando Squad template."""
        return OrchestratorDecision(
            agent=AgentType.ORCHESTRATOR,
            execution_strategy=ExecutionStrategy.TEAM_SESSION,
            rationale=(
                f"Squad '{squad.name}' selected for multi-agent task "
                f"(confidence: {intent.confidence:.0%}). "
                f"Agents: {', '.join(squad.agent_ids)}"
            ),
            task=intent.formulated_objective,
            confidence=intent.confidence,
            metadata={
                "squad_name": squad.name,
                "squad_agents": list(squad.agent_ids),
                "squad_leader": squad.leader,
                "skip_discussion": squad.skip_discussion,
            },
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _suggest_hint_agents(self, intent: IntentAnalysis) -> list[str]:
        """Extrai lista de agentes sugeridos pelo Tier 1 para o leilão direcionado."""
        hints: list[str] = []

        # Prefer explicit agent_sequence_ids (marketplace/plugin agents)
        if intent.agent_sequence_ids:
            return list(intent.agent_sequence_ids)

        # Fallback: agent_sequence (AgentType enum)
        if intent.agent_sequence:
            hints = [a.value for a in intent.agent_sequence]
        elif intent.recommended_agent_id:
            hints = [intent.recommended_agent_id]
        elif intent.recommended_agent and intent.recommended_agent != AgentType.ORCHESTRATOR:
            hints = [intent.recommended_agent.value]

        return hints


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_hybrid_router: HybridRouter | None = None


def get_hybrid_router() -> HybridRouter:
    """Retorna a instância global do HybridRouter (singleton)."""
    global _hybrid_router
    if _hybrid_router is None:
        _hybrid_router = HybridRouter()
    return _hybrid_router


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _estimate_tokens(text: str) -> int:
    """Estimativa grosseira de tokens (~4 chars/token)."""
    return max(1, len(text) // 4)
