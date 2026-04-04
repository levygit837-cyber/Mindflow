"""Routing Metrics — Rastreamento de eficiência e custo do roteamento híbrido.

Registra por qual tier o request passou, confiança da triagem, tokens estimados,
e agentes consultados. Usado para observabilidade e análise de custo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic


@dataclass
class RoutingMetrics:
    """Métricas de uma decisão de roteamento híbrida.

    Attributes:
        tier_used: Qual tier foi utilizado para resolver a decisão.
            - "tier1_direct"  → IntelligentRouter delegou direto com alta confiança
            - "tier1_squad"   → IntelligentRouter + Squad template (multi-agente)
            - "tier2_auction" → DecentralizedRouter acionado por baixa confiança
            - "fallback"      → Erro / degradação graciosa
        triage_confidence: Score de confiança retornado pelo Tier 1 (0.0–1.0).
        triage_tokens_estimated: Tokens estimados para a chamada de triagem.
        auction_tokens_estimated: Tokens estimados para o leilão (0 se Tier 2 não acionado).
        agents_consulted: Quantos agentes foram consultados / receberam broadcast.
        squad_template: Nome do template de squad ativado (None se não aplicável).
        hint_agents: Lista de agentes hint enviados ao Tier 2 (None se broadcast total).
        total_latency_ms: Latência total do roteamento em milissegundos.
        message_preview: Primeiros 100 chars da mensagem roteada.
    """

    tier_used: str = "tier1_direct"
    triage_confidence: float = 0.0
    triage_tokens_estimated: int = 0
    auction_tokens_estimated: int = 0
    agents_consulted: int = 0
    squad_template: str | None = None
    hint_agents: list[str] = field(default_factory=list)
    total_latency_ms: float = 0.0
    message_preview: str = ""

    # Internal timer — not serialized
    _start: float = field(default_factory=monotonic, repr=False, compare=False)

    def finish(self) -> None:
        """Record final latency (call after routing decision is made)."""
        self.total_latency_ms = (monotonic() - self._start) * 1000

    def as_log_dict(self) -> dict[str, object]:
        """Return a structured dict suitable for structured logging."""
        return {
            "tier_used": self.tier_used,
            "triage_confidence": round(self.triage_confidence, 3),
            "triage_tokens_estimated": self.triage_tokens_estimated,
            "auction_tokens_estimated": self.auction_tokens_estimated,
            "agents_consulted": self.agents_consulted,
            "squad_template": self.squad_template,
            "hint_agents_count": len(self.hint_agents),
            "total_latency_ms": round(self.total_latency_ms, 1),
            "message_preview": self.message_preview[:100],
            "tokens_saved_vs_full_auction": max(
                0, self.auction_tokens_estimated - self.triage_tokens_estimated
            ),
        }
