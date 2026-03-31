"""
MissionResult — Resultado estruturado de uma missão autônoma.

Fornece MissionResult (resultado final da missão) e MemoryAnnotationRef
(anotações de memória criadas durante a execução). Inclui métodos de
conversão para compatibilidade com o estado final dos graphs e com
o DelegationResult existente.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from mindflow_backend.schemas.orchestration.communication import MissionGraphType


@dataclass
class MemoryAnnotationRef:
    """Referência a anotação de memória criada durante a missão.

    Attributes:
        content: Conteúdo textual da anotação.
        importance: Importância da anotação (0.0 a 1.0).
        iteration: Iteração do graph em que foi criada.
        timestamp: Momento de criação da anotação.
        tags: Tags associadas para classificação.
    """

    content: str
    importance: float = 0.5
    iteration: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    tags: list[str] = field(default_factory=list)


@dataclass
class MissionResult:
    """Resultado de uma missão autônoma.

    Dataclass que encapsula todos os dados relevantes ao final de uma
    missão: identificação do agente e tipo de missão, estado de sucesso,
    resultado textual, anotações de memória, métricas de execução e erros.

    Attributes:
        agent_id: Identificador do agente executor.
        mission_type: Tipo de missão executada.
        mission_id: ID único da missão.
        success: Indica se a missão completou com sucesso.
        result: Conteúdo textual principal do resultado.
        annotations: Lista de anotações de memória geradas.
        messages_sent: Mensagens P2P enviadas durante a execução.
        duration_seconds: Duração total da execução em segundos.
        iterations: Número de iterações executadas.
        error: Mensagem de erro, se a missão falhou.
        started_at: Timestamp de início da execução.
        completed_at: Timestamp de conclusão (None se ainda em execução).
        metadata: Metadados extras associados à missão.
    """

    agent_id: str
    mission_type: MissionGraphType
    mission_id: str = field(default_factory=lambda: uuid4().hex[:12])
    success: bool = False
    result: str = ""
    annotations: list[MemoryAnnotationRef] = field(default_factory=list)
    messages_sent: list[dict] = field(default_factory=list)
    duration_seconds: float = 0.0
    iterations: int = 0
    error: str | None = None
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_graph_state(
        cls,
        state: dict[str, Any],
        agent_id: str,
        mission_type: MissionGraphType,
        started_at: datetime | None = None,
    ) -> MissionResult:
        """Cria um MissionResult a partir do estado final do graph.

        Extrai informações relevantes do estado final do Execution Graph
        para construir um MissionResult completo.

        Args:
            state: Estado final retornado pelo graph executado.
            agent_id: ID do agente executor.
            mission_type: Tipo de missão executada.
            started_at: Timestamp de início (opcional, usa o de state se presente).

        Returns:
            MissionResult preenchido com os dados do graph.
        """
        started = started_at or state.get("started_at", datetime.now())
        completed = datetime.now()

        # Calcular duração se possível
        if isinstance(started, datetime):
            duration = (completed - started).total_seconds()
        else:
            duration = 0.0

        # Extrair anotações do estado
        raw_annotations = state.get("annotations", [])
        annotations = []
        for ann in raw_annotations:
            if isinstance(ann, dict):
                annotations.append(
                    MemoryAnnotationRef(
                        content=ann.get("content", ""),
                        importance=ann.get("importance", 0.5),
                        iteration=ann.get("iteration", 0),
                        tags=ann.get("tags", []),
                    )
                )
            elif isinstance(ann, MemoryAnnotationRef):
                annotations.append(ann)

        errors = state.get("errors", [])
        error_text = "; ".join(errors) if errors else None

        return cls(
            agent_id=agent_id,
            mission_type=mission_type,
            mission_id=state.get("mission_id", uuid4().hex[:12]),
            success=not errors and bool(state.get("result", "")),
            result=state.get("result", ""),
            annotations=annotations,
            messages_sent=state.get("messages_sent", []),
            duration_seconds=duration,
            iterations=state.get("iteration", 0),
            error=error_text,
            started_at=started if isinstance(started, datetime) else datetime.now(),
            completed_at=completed,
            metadata=state.get("metadata", {}),
        )

    def to_delegation_result_data(self) -> dict[str, Any]:
        """Converte para formato compatível com DelegationResult.

        Retorna um dicionário com os campos que a engine de delegação
        espera, permitindo integração transparente entre MissionLauncher
        e o sistema de delegação existente.
        """
        return {
            "status": "completed" if self.success else "failed",
            "full_output": self.result,
            "key_findings": self.result,
            "confidence": 0.9 if self.success else 0.0,
            "error_message": self.error,
            "tokens_consumed": self.iterations * 100,  # Estimativa
            "mission_annotations": [
                {
                    "content": ann.content,
                    "importance": ann.importance,
                    "iteration": ann.iteration,
                    "tags": ann.tags,
                }
                for ann in self.annotations
            ],
            "messages_sent": self.messages_sent,
            "duration_seconds": self.duration_seconds,
            "iterations": self.iterations,
        }