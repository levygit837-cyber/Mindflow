"""
TeamSession — Estado de uma sessão colaborativa completa entre agentes.

Passa pelas fases: Formation → Discussion → Missions → Synthesis → Completed

Fase 3A — SPADE Team Protocol
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from mindflow_backend.communication.teams.team import Team
    from mindflow_backend.communication.teams.team_chat import TeamMessage
    from mindflow_backend.execution.missions.mission_result import MissionResult
    from .mission_dag import MissionDAG


class TeamPhase(str, Enum):
    """Fases de uma team session."""
    FORMATION = "formation"
    DISCUSSION = "discussion"
    MISSIONS = "missions"
    SYNTHESIS = "synthesis"
    COMPLETED = "completed"


@dataclass
class TeamSessionResult:
    """Resultado final de uma team session completa."""
    session_id: str
    task: str
    final_result: str
    success: bool
    missions: dict[str, Any]  # agent_id → MissionResult serialized
    chat_history_length: int
    total_duration_seconds: float
    phases_completed: list[str]
    error: str | None = None

    def to_summary(self) -> dict[str, Any]:
        """Retorna um resumo legível do resultado."""
        return {
            "session_id": self.session_id,
            "task": self.task,
            "success": self.success,
            "missions_successful": sum(
                1 for m in self.missions.values()
                if m.get("status") == "completed"
            ),
            "missions_total": len(self.missions),
            "chat_history_length": self.chat_history_length,
            "phases_completed": self.phases_completed,
            "duration_seconds": self.total_duration_seconds,
            "error": self.error,
        }


@dataclass
class TeamSession:
    """
    Sessão colaborativa entre múltiplos agentes.

    Gerenciada pelo TeamOrchestrator através de 4 fases.
    """
    task: str
    agent_ids: list[str]
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    team: Any | None = None  # Team
    phase: TeamPhase = TeamPhase.FORMATION
    mission_dag: MissionDAG | None = None
    missions: dict[str, MissionResult] = field(default_factory=dict)  # agent_id → MissionResult
    chat_history: list[Any] = field(default_factory=list)  # list[TeamMessage]
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Phase management
    # ------------------------------------------------------------------

    def advance_phase(self, next_phase: TeamPhase) -> None:
        """Avança para a próxima fase da sessão."""
        self.phase = next_phase

    # ------------------------------------------------------------------
    # Mission tracking
    # ------------------------------------------------------------------

    def record_mission_result(self, agent_id: str, result: MissionResult) -> None:
        """Registra o resultado de umamissão de um agente."""
        self.missions[agent_id] = result

    def all_missions_complete(self) -> bool:
        """Verifica se todas as missões da sessão foram completadas."""
        return len(self.missions) == len(self.agent_ids)

    def get_successful_missions(self) -> list[str]:
        """Retorna lista de agent_ids com missões bem sucedidas."""
        return [
            agent_id
            for agent_id, result in self.missions.items()
            if result.success
        ]

    # ------------------------------------------------------------------
    # Timing
    # ------------------------------------------------------------------

    def get_duration(self) -> float:
        """Retorna duração total da sessão em segundos."""
        end = self.completed_at or datetime.now()
        return (end - self.started_at).total_seconds()

    def mark_completed(self) -> None:
        """Marca a sessão como completada e registra o timestamp."""
        self.completed_at = datetime.now()
        self.phase = TeamPhase.COMPLETED

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def to_summary(self) -> dict[str, Any]:
        """Retorna um resumo da sessão atual."""
        return {
            "session_id": self.session_id,
            "task": self.task,
            "phase": self.phase.value,
            "agents": self.agent_ids,
            "missions_complete": len(self.missions),
            "missions_total": len(self.agent_ids),
            "missions_successful": len(self.get_successful_missions()),
            "duration_seconds": self.get_duration(),
        }