"""
MissionLauncher — Componente central que seleciona e executa missões autônomas.

O MissionLauncher conecta os Execution Graphs ao sistema de delegação,
validando que o agente pode executar o mission_type solicitado, criando
um contexto de execução, executando o graph correto e retornando um
resultado estruturado com anotações e métricas.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from mindflow_backend.agents.specialists.runtime_policy import get_agent_runtime_policy
from mindflow_backend.execution.missions.mission_context import MissionContext
from mindflow_backend.execution.missions.mission_result import (
    MemoryAnnotationRef,
    MissionResult,
)
from mindflow_backend.graphs.base.types import GraphType
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.orchestration.communication import MissionGraphType

if TYPE_CHECKING:
    from mindflow_backend.communication.bus.communication_bus import CommunicationBus
    from mindflow_backend.graphs.factory import GraphFactory

logger = get_logger(__name__)

# Mapeamento MissionGraphType → GraphType string
_MISSION_TO_GRAPH_TYPE: dict[MissionGraphType, GraphType] = {
    MissionGraphType.ANALYSIS: GraphType.ANALYSIS,
    MissionGraphType.DEEP_INVESTIGATION: GraphType.DEEP_INVESTIGATION,
    MissionGraphType.SECURITY_AUDIT: GraphType.SECURITY_AUDIT,
    MissionGraphType.CODE_REVIEW: GraphType.CODE_REVIEW,
    MissionGraphType.IDEATION: GraphType.ANALYSIS,
    MissionGraphType.MULTI_PASS_ANALYSIS: GraphType.DEEP_INVESTIGATION,
    MissionGraphType.VULNERABILITY_SCAN: GraphType.SECURITY_AUDIT,
    MissionGraphType.EXPLORATION: GraphType.ANALYSIS,
    MissionGraphType.CODING_TASK: GraphType.CODING_TASK,
    MissionGraphType.BUG_FIX: GraphType.BUG_FIX,
    MissionGraphType.REFACTOR: GraphType.REFACTOR,
    MissionGraphType.IMPLEMENTATION: GraphType.CODING_TASK,
    MissionGraphType.ARCHITECTURE_DESIGN: GraphType.CODING_TASK,
    MissionGraphType.STRUCTURAL_REFACTOR: GraphType.REFACTOR,
    MissionGraphType.WEB_RESEARCH: GraphType.WEB_RESEARCH,
    MissionGraphType.DOCUMENTATION_LOOKUP: GraphType.WEB_RESEARCH,
    MissionGraphType.COMPARISON_ANALYSIS: GraphType.COMPARISON,
}


class MissionLauncher:
    """Lança missões autônomas via Execution Graphs.

    O ciclo de vida de uma missão é:
        1. Validar que o agente pode executar o mission_type via RuntimePolicy.
        2. Resolver o GraphType correspondente ao MissionGraphType.
        3. Criar MissionContext com todos os dados de controle.
        4. Instanciar o graph via GraphFactory com um ID único.
        5. Executar o graph com o estado inicial derivado do context.
        6. Capturar o estado final e construir MissionResult.
        7. Limpar o graph do factory (remove_graph no finally).
    """

    def __init__(
        self,
        graph_factory: GraphFactory | None = None,
        comm_bus: CommunicationBus | None = None,
    ) -> None:
        """Inicializa o MissionLauncher.

        Args:
            graph_factory: Fábrica de graphs (usa singleton se None).
            comm_bus: Bus de comunicação para mensagens P2P (opcional).
        """
        if graph_factory is None:
            from mindflow_backend.graphs.factory import get_graph_factory
            graph_factory = get_graph_factory()

        self._graph_factory = graph_factory
        self._comm_bus = comm_bus
        self._logger = get_logger(__name__)

    def can_agent_run(
        self, agent_id: str, mission_type: MissionGraphType
    ) -> bool:
        """Verifica se o agente pode executar o mission_type via RuntimePolicy.

        Args:
            agent_id: Identificador do agente (ex: "analyst", "coder:arch_tech").
            mission_type: Tipo de missão desejado.

        Returns:
            True se mission_type está nos available_mission_graphs do agente.
        """
        try:
            policy = get_agent_runtime_policy(agent_id=agent_id)
        except Exception:
            self._logger.warning(
                "runtime_policy_not_found",
                extra={"agent_id": agent_id},
            )
            return False

        return mission_type in policy.available_mission_graphs

    async def launch_mission(
        self,
        agent_id: str,
        mission_type: MissionGraphType,
        task: str,
        session_id: str,
        *,
        comm_bus: CommunicationBus | None = None,
        max_duration_seconds: float = 300.0,
        max_iterations: int = 500,
        metadata: dict[str, Any] | None = None,
    ) -> MissionResult:
        """Lança uma missão autônoma e retorna o resultado.

        Fluxo:
            1. Valida agente (can_agent_run). Se não pode, retorna MissionResult com erro.
            2. Resolve GraphType via _MISSION_TO_GRAPH_TYPE.
            3. Cria graph via factory com ID único.
            4. Executa graph com estado inicial de MissionContext.
            5. Constrói MissionResult do estado final.
            6. Remove graph do factory (cleanup).

        Args:
            agent_id: ID do agente executor.
            mission_type: Tipo de missão a executar.
            task: Descrição da tarefa a ser executada.
            session_id: ID da sessão pai.
            comm_bus: Bus de comunicação (usado se fornecido).
            max_duration_seconds: Timeout da execução em segundos.
            max_iterations: Limite de iterações do graph.
            metadata: Metadados extras anexados ao contexto.

        Returns:
            MissionResult com o resultado completo da execução.
        """
        # Validar agente
        if not self.can_agent_run(agent_id, mission_type):
            self._logger.warning(
                "agent_cannot_run_mission",
                extra={
                    "agent_id": agent_id,
                    "mission_type": mission_type.value,
                },
            )
            return MissionResult(
                agent_id=agent_id,
                mission_type=mission_type,
                success=False,
                error=f"Agente {agent_id} não possui {mission_type.value} em available_mission_graphs",
            )

        # Resolver GraphType
        graph_type = _MISSION_TO_GRAPH_TYPE.get(mission_type)
        if graph_type is None:
            return MissionResult(
                agent_id=agent_id,
                mission_type=mission_type,
                success=False,
                error=f"Mission type {mission_type.value} não tem mapeamento para GraphType",
            )

        # Verificar se o graph_type está registrado no factory
        if graph_type not in self._graph_factory.get_available_types():
            return MissionResult(
                agent_id=agent_id,
                mission_type=mission_type,
                success=False,
                error=f"Graph type {graph_type.value} não registrado no GraphFactory",
            )

        # Criar contexto e estado inicial
        mission_id = uuid4().hex[:12]
        context = MissionContext(
            agent_id=agent_id,
            mission_type=mission_type,
            task=task,
            session_id=session_id,
            comm_bus=comm_bus or self._comm_bus,
            mission_id=mission_id,
            max_duration_seconds=max_duration_seconds,
            max_iterations=max_iterations,
            metadata=metadata or {},
        )
        initial_state = context.to_graph_state()
        initial_state["started_at"] = __import__("datetime").datetime.now()

        # Criar graph via factory
        graph_id = f"mission-{mission_id}"
        graph = None
        start_time = initial_state["started_at"]

        try:
            graph = self._graph_factory.create_graph(
                graph_type=graph_type,
                graph_id=graph_id,
            )
        except Exception as exc:
            self._logger.error(
                "graph_creation_failed",
                extra={"graph_id": graph_id, "error": str(exc)},
            )
            return MissionResult(
                agent_id=agent_id,
                mission_type=mission_type,
                mission_id=mission_id,
                success=False,
                error=f"Falha ao criar graph ({graph_type.value}): {exc}",
                started_at=start_time,
            )

        # Executar graph
        self._logger.debug(
            "mission_execution_started",
            extra={"graph_id": graph_id, "graph_type": graph_type.value},
        )

        try:
            final_state = await graph.execute(initial_state)
        except Exception as exc:
            self._logger.error(
                "graph_execution_failed",
                extra={"graph_id": graph_id, "error": str(exc)},
            )
            final_state = initial_state
            final_state["errors"] = [str(exc)]

        # Construir MissionResult
        result = MissionResult.from_graph_state(
            state=final_state,
            agent_id=agent_id,
            mission_type=mission_type,
            started_at=start_time,
        )
        result.mission_id = mission_id

        # Registrar mensagens enviadas se comm_bus disponível
        bus = comm_bus or self._comm_bus
        if bus and getattr(bus, "is_available", False):
            try:
                sent = getattr(bus, "_sent_log", [])
                if sent:
                    result.messages_sent = [
                        dict(m) if hasattr(m, "model_dump") else m for m in sent
                    ]
            except Exception:
                pass

        self._logger.info(
            "mission_completed",
            extra={
                "mission_id": mission_id,
                "graph_id": graph_id,
                "success": result.success,
                "duration": result.duration_seconds,
            },
        )

        return result

    def create_context(
        self,
        agent_id: str,
        mission_type: MissionGraphType,
        task: str,
        session_id: str,
        *,
        comm_bus: CommunicationBus | None = None,
        max_duration_seconds: float = 300.0,
        max_iterations: int = 500,
        metadata: dict[str, Any] | None = None,
    ) -> MissionContext:
        """Cria um MissionContext (factory method para uso direto).

        Útil quando o caller precisa apenas do contexto sem lançar
        a execução (ex: passar para outro executor).
        """
        return MissionContext(
            agent_id=agent_id,
            mission_type=mission_type,
            task=task,
            session_id=session_id,
            comm_bus=comm_bus or self._comm_bus,
            mission_id=uuid4().hex[:12],
            max_duration_seconds=max_duration_seconds,
            max_iterations=max_iterations,
            metadata=metadata or {},
        )


# ── Singleton global ──────────────────────────────────────────────────
_mission_launcher: MissionLauncher | None = None


def get_mission_launcher(
    graph_factory: Any | None = None,
    comm_bus: CommunicationBus | None = None,
) -> MissionLauncher:
    """Retorna o singleton MissionLauncher com lazy init.

    Args:
        graph_factory: Fábrica de graphs (usa singleton se None).
        comm_bus: Bus de comunicação (tenta singleton se None).

    Returns:
        Instância singleton do MissionLauncher.
    """
    global _mission_launcher
    if _mission_launcher is None:
        _mission_launcher = MissionLauncher(
            graph_factory=graph_factory,
            comm_bus=comm_bus,
        )
    return _mission_launcher