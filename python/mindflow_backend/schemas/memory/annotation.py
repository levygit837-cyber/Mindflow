"""
MemoryAnnotation — Schema para anotações de memória universal criadas por observers.

Diferente de memory saves normais: anotações têm importance score,
source_agent_id (quem gerou o evento original) e observer_agent_id (quem anotou).

Fase 3B — SPADE Memory Observer Protocol
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MemoryAnnotation:
    """
    Anotação de memória criada por um agente em modo observer.

    Salva na memória universal com contexto de quem observou + quem gerou.
    """

    annotation_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    observer_agent_id: str = ""
    """Agente que criou a anotação (estava em modo OBSERVER)."""

    source_agent_id: str = ""
    """Agente cujo evento gerou a anotação."""

    mission_id: str = ""
    """ID da missão sendo observada."""

    session_id: str = ""
    """ID da sessão pai."""

    content: str = ""
    """Conteúdo da anotação — interpretação do observer sobre o evento."""

    raw_event_type: str = ""
    """Tipo do evento original (e.g. 'tool_result', 'agent_decision')."""

    importance: float = 0.5
    """Score 0.0–1.0. Anotações com importance < 0.3 são filtradas."""

    annotation_type: str = "observation"
    """Categoria: 'observation' | 'finding' | 'warning' | 'insight'"""

    timestamp: datetime = field(default_factory=datetime.now)
    tags: list[str] = field(default_factory=list)

    def to_memory_content(self) -> str:
        """Formata para salvar na memória universal."""
        return (
            f"[Observer: {self.observer_agent_id}] "
            f"[Source: {self.source_agent_id}] "
            f"[Type: {self.annotation_type}] "
            f"{self.content}"
        )

    def is_significant(self) -> bool:
        """True se deve ser salva (acima do threshold de importância)."""
        return self.importance >= 0.3


# ---------------------------------------------------------------------------
# Constantes de importância
# ---------------------------------------------------------------------------

IMPORTANCE_THRESHOLDS: dict[str, float] = {
    "observation": 0.3,
    "finding": 0.5,
    "warning": 0.7,
    "insight": 0.4,
}

EVENT_IMPORTANCE_MAP: dict[str, float] = {
    "tool_result": 0.4,
    "agent_decision": 0.6,
    "mission_complete": 0.8,
    "finding": 0.7,
    "error": 0.9,
    "WARNING": 0.8,
    "progress": 0.2,
    "debug": 0.1,
}