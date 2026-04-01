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
        Launch mission using sub-team of specialized agents.

        This method spawns a sub-team to execute the mission in parallel,
        then aggregates their results.
        """
        from mindflow_backend.execution.agent_team_manager import AgentTeamManager

        self._logger.info(
            "launching_sub_team",
            extra={
                "agent_id": agent_id,
                "mission_type": mission_type.value,
                "task": task[:100],
            },
        )

        start_time = datetime.now()

        try:
            # Create team manager
            team_manager = AgentTeamManager(
                comm_bus=comm_bus,
                mission_launcher=self,
            )

            # Select agents for sub-team based on mission type
            sub_team_agents = self._select_sub_team_agents(mission_type, agent_id)

            if not sub_team_agents:
                # Fallback to single agent if no sub-team needed
                return await self._launch_with_execution_graph(
                    agent_id=agent_id,
                    mission_type=mission_type,
                    task=task,
                    session_id=session_id,
                    policy=policy,
                    metadata=metadata,
                )

            # Run sub-team session (skip discussion for efficiency)
            team_result = await team_manager.run_team_session(
                task=task,
                agent_ids=sub_team_agents,
                session_id=session_id,
                skip_discussion=True,  # Sub-teams execute directly
            )

            duration = (datetime.now() - start_time).total_seconds()

            # Convert team result to mission result
            result = MissionResult(
                agent_id=agent_id,
                mission_type=mission_type,
                success=team_result.success,
                result=team_result.synthesized_response,
                duration_seconds=duration,
                metadata={
                    "sub_team_agents": sub_team_agents,
                    "mission_count": len(team_result.mission_results),
                    "team_id": team_result.team_id,
                },
                memory_annotations=[],
                start_time=start_time,
                end_time=datetime.now(),
            )

            self._logger.info(
                "sub_team_completed",
                extra={
                    "agent_id": agent_id,
                    "success": result.success,
                    "duration": duration,
                    "sub_team_size": len(sub_team_agents),
                },
            )

            return result

        except Exception as exc:
            duration = (datetime.now() - start_time).total_seconds()
            self._logger.error(
                "sub_team_failed",
                extra={
                    "agent_id": agent_id,
                    "error": str(exc),
                    "mission_type": mission_type.value,
                },
            )

            return MissionResult(
                agent_id=agent_id,
                mission_type=mission_type,
                success=False,
                result=f"Sub-team execution failed: {exc}",
                duration_seconds=duration,
                metadata={"error": str(exc)},
                memory_annotations=[],
                start_time=start_time,
                end_time=datetime.now(),
            )

    def _select_sub_team_agents(
        self,
        mission_type: MissionGraphType,
        primary_agent_id: str,
    ) -> list[str]:
        """Select appropriate agents for a sub-team based on mission type.

        Args:
            mission_type: Type of mission
            primary_agent_id: Primary agent requesting the sub-team

        Returns:
            List of agent IDs for the sub-team
        """
        # Map mission types to agent combinations
        mission_to_agents = {
            MissionGraphType.CODING_TASK: ["coder", "analyst:critic"],
            MissionGraphType.RESEARCH: ["researcher", "analyst"],
            MissionGraphType.ANALYSIS: ["analyst", "analyst:critic"],
            MissionGraphType.ARCHITECTURE_DESIGN: ["coder:arch_tech", "analyst"],
            MissionGraphType.BUG_FIX: ["coder", "analyst:critic"],
            MissionGraphType.REFACTOR: ["coder:arch_tech", "analyst:critic"],
            MissionGraphType.IMPLEMENTATION: ["coder", "analyst"],
        }

        agents = mission_to_agents.get(mission_type, [])

        # Filter out the primary agent to avoid duplication
        agents = [a for a in agents if a != primary_agent_id]

        return agents

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