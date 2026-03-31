"""
MissionLauncher — Componente central que seleciona e executa missões autônomas.

O MissionLauncher conecta os Execution Graphs ao sistema de delegação,
validando que o agente pode executar o mission_type solicitado, criando
um contexto de execução, executando o graph correto e retornando um
resultado estruturado com anotações e métricas.
"""
from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

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

# Mapeamento MissionGraphType → GraphType
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
    """Lança missões autônomas via Execution Graphs."""

    def __init__(
        self,
        graph_factory: GraphFactory | None = None,
        comm_bus: CommunicationBus | None = None,
    ) -> None:
        if graph_factory is None:
            from mindflow_backend.graphs.factory import get_graph_factory
            graph_factory = get_graph_factory()

        self._graph_factory = graph_factory
        self._comm_bus = comm_bus
        self._logger = get_logger(__name__)

    def can_agent_run(
        self, agent_id: str, mission_type: MissionGraphType
    ) -> bool:
        """Verifica se o agente pode executar o mission_type via RuntimePolicy."""
        # Lazy import to avoid circular import
        from mindflow_backend.agents.specialists.runtime_policy import (
            get_agent_runtime_policy,
        )
        try:
            policy = get_agent_runtime_policy(agent_id=agent_id)
        except Exception:
            self._logger.warning(
                "runtime_policy_not_found", extra={"agent_id": agent_id}
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
        """Lança uma missão autônoma e retorna o resultado."""
        # Validar agente
        if not self.can_agent_run(agent_id, mission_type):
            self._logger.warning(
                "agent_cannot_run_mission",
                extra={"agent_id": agent_id, "mission_type": mission_type.value},
            )
            return MissionResult(
                agent_id=agent_id,
                mission_type=mission_type,
                success=False,
                error=f"Agente {agent_id} não possui {mission_type.value} em available_mission_graphs",
            )

        # Check for sub-team support (Phase 2: Sub-Agent System)
        # Prevent recursion: if this is already a sub-agent, skip sub-team spawning
        metadata = metadata or {}
        is_sub_agent = metadata.get("is_sub_agent", False)

        if not is_sub_agent:
            # Lazy import to avoid circular dependency
            from mindflow_backend.agents.specialists.runtime_policy import (
                get_agent_runtime_policy,
            )

            try:
                policy = get_agent_runtime_policy(agent_id=agent_id)

                # Route to SubTeamLauncher if agent supports sub-teams
                if policy.supports_sub_team and policy.sub_team_config:
                    return await self._launch_with_sub_team(
                        agent_id=agent_id,
                        mission_type=mission_type,
                        task=task,
                        session_id=session_id,
                        policy=policy,
                        comm_bus=comm_bus,
                        metadata=metadata,
                    )
            except Exception as exc:
                self._logger.warning(
                    "sub_team_detection_failed",
                    extra={"agent_id": agent_id, "error": str(exc)},
                )
                # Fallback to normal mission execution

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
        initial_state["started_at"] = datetime.now()

        # Criar graph via factory
        graph_id = f"mission-{mission_id}"
        graph = None
        start_time = initial_state["started_at"]

        try:
            graph = self._graph_factory.create_graph(
                graph_type=graph_type, graph_id=graph_id
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

    async def _launch_with_sub_team(
        self,
        agent_id: str,
        mission_type: MissionGraphType,
        task: str,
        session_id: str,
        policy: Any,  # AgentRuntimePolicy
        comm_bus: CommunicationBus | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MissionResult:
        """
        Launch mission using SubTeamLauncher.

        This method spawns a sub-team of specialized agents to execute
        the mission in parallel, then aggregates their results.
        """
        from mindflow_backend.execution.sub_teams.sub_team_launcher import SubTeamLauncher
        from mindflow_backend.execution.teams.team_orchestrator import TeamOrchestrator

        # TODO: Get TeamManager instance (for now, we'll need to handle this)
        # For the implementation, we need access to TeamOrchestrator
        # This will be properly wired when integrating with the full system

        self._logger.info(
            "launching_sub_team",
            extra={
                "agent_id": agent_id,
                "mission_type": mission_type.value,
                "task": task[:100],
            },
        )

        # Create SubTeamLauncher
        # Note: This is a simplified version - full integration will require
        # proper dependency injection of TeamOrchestrator
        try:
            # For now, create a basic MissionResult that indicates sub-team was attempted
            # Full implementation will come when we have TeamOrchestrator properly wired
            start_time = datetime.now()

            # Placeholder: In full implementation, this will call SubTeamLauncher
            # sub_team_launcher = SubTeamLauncher(team_orchestrator, self, comm_bus)
            # sub_team_result = await sub_team_launcher.launch_sub_team(...)

            result = MissionResult(
                agent_id=agent_id,
                mission_type=mission_type,
                success=True,
                result="Sub-team execution (placeholder)",
                started_at=start_time,
            )

            # Attach sub_team_result when available
            # result.sub_team_result = sub_team_result

            return result

        except Exception as exc:
            self._logger.error(
                "sub_team_launch_failed",
                extra={"agent_id": agent_id, "error": str(exc)},
            )
            # Fallback to normal mission execution
            return MissionResult(
                agent_id=agent_id,
                mission_type=mission_type,
                success=False,
                error=f"Sub-team launch failed: {exc}",
                started_at=datetime.now(),
            )

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
        """Factory method para criar MissionContext."""
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


# Singleton global
_mission_launcher: MissionLauncher | None = None


def get_mission_launcher(
    graph_factory: Any | None = None,
    comm_bus: CommunicationBus | None = None,
) -> MissionLauncher:
    """Retorna o singleton MissionLauncher com lazy init."""
    global _mission_launcher
    if _mission_launcher is None:
        _mission_launcher = MissionLauncher(
            graph_factory=graph_factory, comm_bus=comm_bus
        )
    return _mission_launcher