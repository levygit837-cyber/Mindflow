"""
TeamOrchestrator — Coordena sessões colaborativas multi-agente.

Fases: Formation → Discussion → Missions → Synthesis

Fase 3A — SPADE Team Protocol
Fase 3B — Memory Observer Integration
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, TYPE_CHECKING

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.orchestration.communication import MissionGraphType

from .mission_dag import MissionDAG, MissionNode
from .team_session import TeamPhase, TeamSession, TeamSessionResult

# Lazy imports to avoid circular import chain
if TYPE_CHECKING:
    from mindflow_backend.agents.specialists.runtime_policy import get_agent_runtime_policy
    from mindflow_backend.communication.teams.team import Team
    from mindflow_backend.communication.teams.team_chat import TeamChat, TeamMessage

if TYPE_CHECKING:
    from mindflow_backend.communication.bus.communication_bus import CommunicationBus
    from mindflow_backend.execution.missions.mission_launcher import MissionLauncher
    from mindflow_backend.execution.missions.mission_result import MissionResult
    from mindflow_backend.execution.observers.memory_observer import MemoryObserver

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Configurações
# ---------------------------------------------------------------------------

MAX_DISCUSSION_ROUNDS = 3
DISCUSSION_TIMEOUT_SECONDS = 60.0
MISSION_SIGNAL_TIMEOUT = 120.0


class TeamOrchestrator:
    """
    Coordena sessões colaborativas entre múltiplos agentes.

    O Orchestrator é sempre o LEADER.
    Especialistas discutem, declaram dependências, e lançam missões autônomas.
    """

    def __init__(
        self,
        team_manager: TeamManager,
        mission_launcher: MissionLauncher,
        comm_bus: CommunicationBus,
    ) -> None:
        self._team_manager = team_manager
        self._mission_launcher = mission_launcher
        self._comm_bus = comm_bus

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    async def run_full_team_session(
        self,
        task: str,
        agent_ids: list[str],
        session_id: str,
        skip_discussion: bool = False,
    ) -> TeamSessionResult:
        """
        Executa uma team session completa pelas 4 fases.

        Args:
            task: Tarefa a ser executada pelo time.
            agent_ids: IDs dos agentes participantes.
            session_id: ID da sessão.
            skip_discussion: Se True, pula a fase Discussion (usado por sub-teams).

        Returns TeamSessionResult com resultado sintetizado.
        """
        session = TeamSession(
            task=task,
            agent_ids=agent_ids,
            session_id=session_id,
        )

        logger.info(
            "team_session_start",
            extra={
                "session_id": session_id,
                "task": task[:100],
                "agents": agent_ids,
                "skip_discussion": skip_discussion,
            },
        )

        try:
            # FASE 1: Formation
            await self._phase_formation(session)

            # FASE 2: Discussion (condicional para sub-teams)
            if not skip_discussion:
                await self._phase_discussion(session)
            else:
                logger.info(
                    "team_session_skip_discussion",
                    extra={"session_id": session_id, "reason": "sub_team"},
                )

            # FASE 3: Missions
            await self._phase_missions(session)

            # FASE 4: Synthesis
            final_result = await self._phase_synthesis(session)

            session.mark_completed()

            logger.info(
                "team_session_completed",
                extra={
                    "session_id": session_id,
                    "success": True,
                    "duration": session.get_duration(),
                },
            )

            return TeamSessionResult(
                session_id=session.session_id,
                task=task,
                final_result=final_result,
                success=True,
                missions={
                    agent_id: result.to_delegation_result_data()
                    for agent_id, result in session.missions.items()
                },
                chat_history_length=len(session.chat_history),
                total_duration_seconds=session.get_duration(),
                phases_completed=[p.value for p in TeamPhase if p != TeamPhase.COMPLETED],
            )

        except Exception as exc:
            logger.error(
                "team_session_failed",
                extra={
                    "session_id": session_id,
                    "phase": session.phase.value,
                    "error": str(exc),
                },
            )
            session.mark_completed()

            return TeamSessionResult(
                session_id=session.session_id,
                task=task,
                final_result="",
                success=False,
                missions={
                    agent_id: result.to_delegation_result_data()
                    for agent_id, result in session.missions.items()
                },
                chat_history_length=len(session.chat_history),
                total_duration_seconds=session.get_duration(),
                phases_completed=[session.phase.value],
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Phase 1: Formation
    # ------------------------------------------------------------------

    async def _phase_formation(self, session: TeamSession) -> None:
        """Cria o time e registra agentes no bus."""
        session.advance_phase(TeamPhase.FORMATION)
        logger.info(
            "team_formation_start",
            extra={"session_id": session.session_id, "agents": session.agent_ids},
        )

        # Criar team
        team = self._team_manager.create_team(
            name=f"session_{session.session_id[:8]}",
            description=f"Team for: {session.task[:50]}",
        )

        # Adicionar membros
        for agent_id in session.agent_ids:
            team.add_member(agent_id, role="specialist")

        session.team = team

        # Registrar agentes no bus e entrar na room
        room_id = team.team_id
        for agent_id in [*session.agent_ids]:
            await self._comm_bus.register_agent(agent_id)
            self._comm_bus.join_room(agent_id, room_id)

        logger.info(
            "team_formed",
            extra={
                "session_id": session.session_id,
                "team_id": team.team_id,
                "agents": session.agent_ids,
            },
        )

    # ------------------------------------------------------------------
    # Phase 2: Discussion
    # ------------------------------------------------------------------

    async def _phase_discussion(self, session: TeamSession) -> None:
        """Facilita discussion e extrai MissionDAG."""
        session.advance_phase(TeamPhase.DISCUSSION)

        if session.team is None:
            raise RuntimeError("Team not formed — cannot start discussion.")

        team_chat = TeamChat(session.team.team_id, session.team.team_id)

        # Round 0: Orchestrator apresenta a tarefa
        intro_msg = team_chat.create_message(
            sender_jid="orchestrator",
            content=(
                f"Task: {session.task}\n\n"
                f"Please declare: (1) what you will do, "
                f"(2) what you need from other agents first."
            ),
        )
        session.chat_history.append(intro_msg)

        # Rounds de discussão (máx MAX_DISCUSSION_ROUNDS)
        for round_num in range(MAX_DISCUSSION_ROUNDS):
            round_messages = await self._collect_agent_declarations(
                session=session,
                round_num=round_num,
                team_chat=team_chat,
            )
            session.chat_history.extend(round_messages)

            # Verificar consenso (todos declararam pelo menos 1 vez)
            if self._consensus_reached(session.chat_history, session.agent_ids):
                logger.info(
                    "team_consensus_reached",
                    extra={
                        "session_id": session.session_id,
                        "rounds": round_num + 1,
                    },
                )
                break

        # Extrair MissionDAG das declarações
        session.mission_dag = MissionDAG.from_discussion(
            chat_messages=session.chat_history,
            agent_ids=session.agent_ids,
            session_id=session.session_id,
        )

        # Validar DAG
        is_valid, error_msg = session.mission_dag.is_valid()
        if not is_valid:
            logger.warning(
                "team_dag_invalid",
                extra={"session_id": session.session_id, "error": error_msg},
            )
            # Fallback: DAG sem dependências
            session.mission_dag = self._build_fallback_dag(
                session.agent_ids,
                session.session_id,
            )

        waves = session.mission_dag.get_execution_waves()
        logger.info(
            "team_discussion_complete",
            extra={
                "session_id": session.session_id,
                "dag_waves": len(waves),
                "dag_valid": is_valid,
            },
        )

    # ------------------------------------------------------------------
    # Phase 3: Missions
    # ------------------------------------------------------------------

    async def _phase_missions(self, session: TeamSession) -> None:
        """Executa missões em paralelo seguindo o MissionDAG."""
        session.advance_phase(TeamPhase.MISSIONS)

        dag = session.mission_dag
        if dag is None:
            raise RuntimeError("MissionDAG not available — cannot start missions.")

        waves = dag.get_execution_waves()
        logger.info(
            "team_missions_start",
            extra={
                "session_id": session.session_id,
                "waves": len(waves),
            },
        )

        # Track active observers for cleanup
        active_observers: list[Any] = []

        for wave_idx, wave in enumerate(waves):
            logger.info(
                "team_wave_start",
                extra={
                    "wave": wave_idx,
                    "agents": wave,
                    "session_id": session.session_id,
                },
            )

            # Executar todos os agentes desta wave em paralelo
            tasks = []
            for agent_id in wave:
                node = dag.get_node(agent_id)
                if node and node.mission_type is not None:
                    tasks.append(
                        self._run_agent_mission(
                            session=session,
                            agent_id=agent_id,
                            mission_type=node.mission_type,
                        )
                    )
                else:
                    # Sem node/mission_type — registrar como falha
                    from mindflow_backend.execution.missions.mission_result import (
                        MissionResult,
                    )
                    tasks.append(
                        asyncio.ensure_future(self._fake_failed_result(agent_id, "No mission type available"))
                    )

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for agent_id, result in zip(wave, results):
                if isinstance(result, Exception):
                    logger.error(
                        "team_mission_error",
                        extra={
                            "agent_id": agent_id,
                            "session_id": session.session_id,
                            "error": str(result),
                        },
                    )
                    from mindflow_backend.execution.missions.mission_result import (
                        MissionResult,
                    )
                    session.record_mission_result(
                        agent_id,
                        MissionResult(
                            agent_id=agent_id,
                            mission_type=MissionGraphType.ANALYSIS,
                            success=False,
                            error=str(result),
                        ),
                    )
                else:
                    session.record_mission_result(agent_id, result)

                    # Notificar dependentes que esta missão completou
                    dependents = dag.get_dependents_of(agent_id)
                    for dep in dependents:
                        if self._comm_bus.is_available:
                            from mindflow_backend.communication.mixins.agent_communication import (
                                AgentCommunicationMixin,
                            )
                            comm = AgentCommunicationMixin(
                                agent_id=agent_id, bus=self._comm_bus
                            )
                            await comm.notify(
                                to_agent=dep,
                                event="mission_complete",
                                data={"agent": agent_id},
                            )

                    # Ativar Memory Observer para agente que completou missão com sucesso
                    if result.success:
                        # Obter IDs de missões ativas (próximas waves)
                        active_mission_ids = []
                        for future_wave in waves[wave_idx + 1:]:
                            for future_agent_id in future_wave:
                                future_node = dag.get_node(future_agent_id)
                                if future_node:
                                    active_mission_ids.append(f"{future_agent_id}_mission")

                        if active_mission_ids:
                            observer = await self._start_observer_for_completed_agent(
                                completed_agent_id=agent_id,
                                session=session,
                                active_mission_ids=active_mission_ids,
                            )
                            if observer:
                                active_observers.append(observer)

            logger.info(
                "team_wave_complete",
                extra={
                    "wave": wave_idx,
                    "completed": len(wave),
                    "session_id": session.session_id,
                },
            )

        # Parar todos os observers no final da fase de missões
        for observer in active_observers:
            await self._stop_observer(observer, session)

    # ------------------------------------------------------------------
    # Phase 4: Synthesis
    # ------------------------------------------------------------------

    async def _phase_synthesis(self, session: TeamSession) -> str:
        """Orquestrador sintetiza todos os resultados em resposta final."""
        session.advance_phase(TeamPhase.SYNTHESIS)

        # Construir resumo das missões
        mission_summaries = []
        for agent_id in session.agent_ids:
            result = session.missions.get(agent_id)
            if result:
                status = "SUCCESS" if result.success else f"FAILED ({result.error})"
                mission_summaries.append(
                    f"### {agent_id} [{status}]\n{result.result}"
                )
            else:
                mission_summaries.append(f"### {agent_id} [NO RESULT]\n")

        results_section = "\n\n".join(mission_summaries)

        # Synthesis via concatenação estruturada
        synthesis = (
            f"# Team Session Results\n\n"
            f"**Task:** {session.task}\n"
            f"**Session:** {session.session_id}\n"
            f"**Agents:** {', '.join(session.agent_ids)}\n"
            f"**Duration:** {session.get_duration():.1f}s\n\n"
            f"---\n\n"
            f"{results_section}"
        )

        logger.info(
            "team_synthesis_complete",
            extra={
                "session_id": session.session_id,
                "missions_successful": sum(
                    1 for r in session.missions.values() if r.success
                ),
                "missions_total": len(session.agent_ids),
            },
        )

        return synthesis

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _run_agent_mission(
        self,
        session: TeamSession,
        agent_id: str,
        mission_type: MissionGraphType,
    ) -> MissionResult:
        """Lança missão de um agente específico."""
        return await self._mission_launcher.launch_mission(
            agent_id=agent_id,
            mission_type=mission_type,
            task=session.task,
            session_id=session.session_id,
            comm_bus=self._comm_bus,
        )

    async def _collect_agent_declarations(
        self,
        session: TeamSession,
        round_num: int,
        team_chat: TeamChat,
    ) -> list[TeamMessage]:
        """Coleta declarações de todos os agentes no round."""
        msgs: list[TeamMessage] = []
        for agent_id in session.agent_ids:
            try:
                policy = get_agent_runtime_policy(
                    agent_id=agent_id,
                    session_id=session.session_id,
                )
                graphs = [g.value for g in policy.available_mission_graphs[:3]]
            except (KeyError, ValueError):
                graphs = ["unknown"]

            declaration = (
                f"[Round {round_num + 1}] {agent_id}: "
                f"I can handle {graphs}. "
                f"Starting immediately."
            )
            msg = team_chat.create_message(sender_jid=agent_id, content=declaration)
            msgs.append(msg)

        return msgs

    @staticmethod
    def _consensus_reached(
        messages: list[Any],
        agent_ids: list[str],
    ) -> bool:
        """Verifica se todos os agentes fizeram pelo menos 1 declaração."""
        declaring_agents: set[str] = set()
        for m in messages:
            sender = getattr(m, "sender_jid", None) or ""
            if sender != "orchestrator" and sender in set(agent_ids):
                declaring_agents.add(sender)
        return declaring_agents.issuperset(set(agent_ids))

    @staticmethod
    def _build_fallback_dag(
        agent_ids: list[str],
        session_id: str | None = None,
    ) -> MissionDAG:
        """Cria DAG sem dependências (todas missões em paralelo)."""
        dag = MissionDAG()
        for agent_id in agent_ids:
            try:
                policy = get_agent_runtime_policy(
                    agent_id=agent_id,
                    session_id=session_id,
                )
                mission_type = policy.available_mission_graphs[0] if policy.available_mission_graphs else None
            except (KeyError, ValueError, IndexError):
                mission_type = None

            if mission_type is not None:
                dag.add_mission(MissionNode(
                    agent_id=agent_id,
                    mission_type=mission_type,
                    task_description=f"Mission for {agent_id}",
                    declared_dependencies=[],
                ))
        return dag

    @staticmethod
    async def _fake_failed_result(agent_id: str, error: str) -> MissionResult:
        """Retorna MissionResult de falha para agentes sem missão."""
        from mindflow_backend.execution.missions.mission_result import MissionResult
        return MissionResult(
            agent_id=agent_id,
            mission_type=MissionGraphType.ANALYSIS,
            success=False,
            error=error,
            started_at=datetime.now(),
        )

    # ------------------------------------------------------------------
    # Memory Observer (Fase 3B)
    # ------------------------------------------------------------------

    async def _start_observer_for_completed_agent(
        self,
        completed_agent_id: str,
        session: "TeamSession",
        active_mission_ids: list[str],
    ) -> "MemoryObserver | None":
        """Ativa modo observer para agente que completou sua missão.

        Fase 3B — SPADE Memory Observer Protocol:
        - Verifica se agente tem can_observe=True
        - Cria MemoryObserver e registra no AgentLogBus
        - Observer escuta eventos das missões ativas e anota memória
        """
        from mindflow_backend.execution.observers.memory_observer import MemoryObserver

        try:
            policy = get_agent_runtime_policy(
                agent_id=completed_agent_id,
                session_id=session.session_id,
            )
            if not policy.can_observe:
                return None

            from mindflow_backend.memory import get_memory_service

            observer = MemoryObserver(
                observer_agent_id=completed_agent_id,
                memory_facade=get_memory_service(),
                session_id=session.session_id,
            )

            await observer.start_observing(active_mission_ids)

            # Registrar observer no AgentLogBus para receber eventos
            from mindflow_backend.runtime.monitoring.log_bus import log_bus

            for mission_id in active_mission_ids:
                log_bus.subscribe_to_mission(
                    mission_id=mission_id,
                    observer_id=completed_agent_id,
                    handler=observer.receive_event,
                )

            logger.info(
                "observer_activated",
                extra={
                    "observer_id": completed_agent_id,
                    "missions": active_mission_ids,
                    "session_id": session.session_id,
                },
            )
            return observer

        except Exception as exc:
            logger.debug(
                "observer_start_failed",
                extra={
                    "agent_id": completed_agent_id,
                    "error": str(exc),
                },
            )
            return None

    async def _stop_observer(
        self,
        observer: "MemoryObserver",
        session: "TeamSession",
    ) -> None:
        """Para observer e remove subscriptions do AgentLogBus."""
        from mindflow_backend.runtime.monitoring.log_bus import log_bus

        observer_id = observer._observer_id
        stats = observer.get_stats()

        # Remover subscriptions
        log_bus.unsubscribe_all(observer_id)

        # Parar observer
        await observer.stop_observing()

        logger.info(
            "observer_stopped",
            extra={
                "observer_id": observer_id,
                "total_annotations": stats.get("total_annotations", 0),
                "session_id": session.session_id,
            },
        )
