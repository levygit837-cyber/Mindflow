"""
MissionContext — Estado e dependências injetados em cada missão autônoma.

Dataclass que encapsula o contexto completo de execução de uma missão
autônoma, incluindo identificação do agente, tipo de missão, tarefa,
referência ao bus de comunicação e parâmetros de controle (timeout,
iterações, etc.). Fornece o método to_graph_state() para compatibilidade
com os Execution Graphs existentes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from mindflow_backend.schemas.orchestration.communication import MissionGraphType

if TYPE_CHECKING:
    from mindflow_backend.execution.sub_teams.sub_team_config import SubTeamConfig


@dataclass
class MissionContext:
    """Estado e dependências injetados em cada missão autônoma.

    Attributes:
        agent_id: Identificador do agente executor.
        mission_type: Tipo de missão (mapeia para um Execution Graph).
        task: Descrição textual da tarefa a executar.
        session_id: ID da sessão pai (para rastreamento de contexto).
        comm_bus: Referência ao bus de comunicação (opcional).
        memory_scope: Escopo de memória para a execução.
        parent_mission_id: ID da missão pai (para sub-missões).
        mission_id: Identificador único da missão (gerado automaticamente).
        max_duration_seconds: Timeout máximo em segundos.
        max_iterations: Limite de iterações do graph.
        metadata: Dicionário com metadados extras.
        is_sub_agent: Flag indicando se este é um sub-agente (previne recursão).
        parent_agent_id: ID do agente pai (para sub-agentes).
        sub_team_config: Configuração de sub-team (se aplicável).
    """

    agent_id: str
    mission_type: MissionGraphType
    task: str
    session_id: str
    comm_bus: Any | None = None
    memory_scope: str = "universal"
    parent_mission_id: str | None = None
    mission_id: str = field(default_factory=lambda: uuid4().hex[:12])
    max_duration_seconds: float = 300.0
    max_iterations: int = 500
    metadata: dict[str, Any] = field(default_factory=dict)
    is_sub_agent: bool = False
    parent_agent_id: str | None = None
    sub_team_config: SubTeamConfig | None = None

    def to_graph_state(self) -> dict[str, Any]:
        """Converte MissionContext para dict compatível com GraphState.

        Retorna um dicionário com os campos que os Execution Graphs
        esperam no estado inicial, incluindo identificação da missão,
        tarefa, sessão e metadados de controle.
        """
        # Copy metadata and add sub_team_config if present
        metadata = self.metadata.copy()
        if self.sub_team_config is not None:
            metadata["sub_team_config"] = self.sub_team_config

        return {
            "agent_id": self.agent_id,
            "mission_type": self.mission_type.value,
            "task": self.task,
            "session_id": self.session_id,
            "mission_id": self.mission_id,
            "parent_mission_id": self.parent_mission_id,
            "memory_scope": self.memory_scope,
            "max_iterations": self.max_iterations,
            "metadata": metadata,
            "messages": [],
            "result": "",
            "annotations": [],
            "errors": [],
            "iteration": 0,
            "is_sub_agent": self.is_sub_agent,
            "parent_agent_id": self.parent_agent_id,
        }