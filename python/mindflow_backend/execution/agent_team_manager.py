"""Agent Team Manager - Unified interface for team-based execution.

This module provides the AgentTeamManager class, which integrates all
team-related components into a single, cohesive interface:

- TeamOrchestrator (4-phase team sessions)
- TeamChat (MUC communication)
- MissionDAG (dependency extraction)
- CommunicationBus (P2P messaging)
- AgentCommunicationMixin (injected into agents)

The AgentTeamManager is used by UnifiedExecutionEngine when executing
TEAM_SESSION strategies.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from mindflow_backend.infra.logging import get_logger

if TYPE_CHECKING:
    from mindflow_backend.communication.bus.communication_bus import CommunicationBus
    from mindflow_backend.communication.teams.team import Team
    from mindflow_backend.communication.teams.team_manager import TeamManager
    from mindflow_backend.execution.missions.mission_dag import MissionDAG
    from mindflow_backend.execution.missions.mission_launcher import MissionLauncher
    from mindflow_backend.execution.teams.team_orchestrator import TeamOrchestrator
    from mindflow_backend.execution.teams.team_session import TeamSessionResult

_logger = get_logger(__name__)


class AgentTeamManager:
    """Manages collaborative agent teams.

    This class provides a unified interface for creating and managing
    teams of agents that work together to solve complex tasks.

    Features:
    - Team formation (create teams, assign roles)
    - Discussion phase (structured multi-round discussion)
    - Mission extraction (build MissionDAG from discussion)
    - Parallel execution (execute missions respecting dependencies)
    - Result synthesis (aggregate results into final response)

    Integration:
    - Uses TeamOrchestrator for 4-phase workflow
    - Uses TeamManager for team lifecycle
    - Uses CommunicationBus for P2P messaging
    - Uses MissionLauncher for mission execution
    """

    def __init__(
        self,
        team_manager: TeamManager | None = None,
        comm_bus: CommunicationBus | None = None,
        mission_launcher: MissionLauncher | None = None,
    ):
        """Initialize the team manager.

        Args:
            team_manager: Team lifecycle manager (lazy-loaded if None)
            comm_bus: Communication bus for P2P (lazy-loaded if None)
            mission_launcher: Mission launcher (lazy-loaded if None)
        """
        self._team_manager = team_manager
        self._comm_bus = comm_bus
        self._mission_launcher = mission_launcher
        self._team_orchestrator: TeamOrchestrator | None = None

    async def run_team_session(
        self,
        task: str,
        agent_ids: list[str],
        session_id: str,
        skip_discussion: bool = False,
    ) -> TeamSessionResult:
        """Run a complete team session.

        This is the main entry point for team-based execution.

        Args:
            task: Task description
            agent_ids: List of agent IDs to include in team
            session_id: Session ID for tracking
            skip_discussion: Skip discussion phase (for sub-teams)

        Returns:
            TeamSessionResult with synthesized response and metadata
        """
        _logger.info(
            "agent_team_manager_session_start",
            task=task[:100],
            agent_count=len(agent_ids),
            session_id=session_id,
            skip_discussion=skip_discussion,
        )

        # Get orchestrator
        orchestrator = self._get_orchestrator()

        # Run full 4-phase session
        result = await orchestrator.run_full_team_session(
            task=task,
            agent_ids=agent_ids,
            session_id=session_id,
            skip_discussion=skip_discussion,
        )

        _logger.info(
            "agent_team_manager_session_complete",
            success=result.success,
            mission_count=len(result.mission_results),
            session_id=session_id,
        )

        return result

    async def create_team(
        self,
        task: str,
        agent_ids: list[str],
        session_id: str,
    ) -> Team:
        """Create a new team (Phase 1: Formation).

        Args:
            task: Task description
            agent_ids: Agent IDs to include
            session_id: Session ID

        Returns:
            Created Team object
        """
        team_manager = self._get_team_manager()

        # Generate team name from task
        team_name = self._generate_team_name(task, session_id)

        # Create team
        team = await team_manager.create_team(
            name=team_name,
            agent_ids=agent_ids,
            session_id=session_id,
        )

        _logger.info(
            "team_created",
            team_id=team.team_id,
            team_name=team_name,
            agent_count=len(agent_ids),
        )

        return team

    async def run_discussion_phase(
        self,
        team: Team,
        task: str,
        max_rounds: int = 3,
    ) -> MissionDAG:
        """Run discussion phase and extract MissionDAG (Phase 2).

        Args:
            team: Team object
            task: Task to discuss
            max_rounds: Maximum discussion rounds

        Returns:
            MissionDAG extracted from discussion
        """
        orchestrator = self._get_orchestrator()

        # Run discussion via orchestrator
        # (orchestrator handles the discussion internally)
        # For now, create a simple DAG as placeholder
        from mindflow_backend.execution.missions.mission_dag import MissionDAG

        dag = MissionDAG()

        _logger.info(
            "discussion_phase_complete",
            team_id=team.team_id,
            rounds=max_rounds,
            missions=len(dag.nodes),
        )

        return dag

    async def execute_missions(
        self,
        dag: MissionDAG,
        team: Team,
        session_id: str,
    ) -> list[Any]:
        """Execute missions in parallel respecting DAG (Phase 3).

        Args:
            dag: Mission dependency graph
            team: Team object
            session_id: Session ID

        Returns:
            List of MissionResult objects
        """
        mission_launcher = self._get_mission_launcher()

        # Get ordered missions from DAG
        ordered_missions = dag.get_ordered_missions()

        results = []

        # Execute missions (simplified - real implementation would respect dependencies)
        for mission_node in ordered_missions:
            _logger.info(
                "executing_mission",
                mission_type=mission_node.mission_type,
                agent_id=mission_node.agent_id,
            )

            # Launch mission
            result = await mission_launcher.launch_mission(
                agent_id=mission_node.agent_id,
                mission_type=mission_node.mission_type,
                task=mission_node.task,
                session_id=session_id,
            )

            results.append(result)

        _logger.info(
            "missions_complete",
            total=len(results),
            successful=sum(1 for r in results if r.success),
        )

        return results

    def inject_communication_mixin(
        self,
        agent: Any,
        agent_id: str,
    ) -> None:
        """Inject AgentCommunicationMixin into an agent.

        This gives the agent P2P communication capabilities.

        Args:
            agent: Agent instance
            agent_id: Agent identifier
        """
        comm_bus = self._get_comm_bus()

        if comm_bus is None or not comm_bus.is_available:
            _logger.debug(
                "communication_mixin_skip",
                agent_id=agent_id,
                reason="bus_unavailable",
            )
            return

        try:
            from mindflow_backend.communication.mixins.agent_communication import (
                AgentCommunicationMixin,
            )

            agent.comm = AgentCommunicationMixin(
                agent_id=agent_id,
                bus=comm_bus,
            )

            _logger.debug(
                "communication_mixin_injected",
                agent_id=agent_id,
            )

        except Exception as exc:
            _logger.warning(
                "communication_mixin_injection_failed",
                agent_id=agent_id,
                error=str(exc),
            )

    # ─────────────────────────────────────────────────────────────────
    # Lazy Initialization
    # ─────────────────────────────────────────────────────────────────

    def _get_team_manager(self) -> TeamManager:
        """Get or create TeamManager (lazy init)."""
        if self._team_manager is None:
            from mindflow_backend.communication.teams.team_manager import TeamManager

            self._team_manager = TeamManager()

        return self._team_manager

    def _get_comm_bus(self) -> CommunicationBus | None:
        """Get or create CommunicationBus (lazy init)."""
        if self._comm_bus is None:
            try:
                from mindflow_backend.communication.bus.communication_bus import (
                    get_communication_bus,
                )

                self._comm_bus = get_communication_bus()
            except Exception as exc:
                _logger.debug(
                    "communication_bus_unavailable",
                    error=str(exc),
                )
                return None

        return self._comm_bus

    def _get_mission_launcher(self) -> MissionLauncher:
        """Get or create MissionLauncher (lazy init)."""
        if self._mission_launcher is None:
            from mindflow_backend.execution.missions.mission_launcher import (
                get_mission_launcher,
            )

            self._mission_launcher = get_mission_launcher(
                comm_bus=self._get_comm_bus()
            )

        return self._mission_launcher

    def _get_orchestrator(self) -> TeamOrchestrator:
        """Get or create TeamOrchestrator (lazy init)."""
        if self._team_orchestrator is None:
            from mindflow_backend.execution.teams.team_orchestrator import (
                TeamOrchestrator,
            )

            self._team_orchestrator = TeamOrchestrator(
                team_manager=self._get_team_manager(),
                mission_launcher=self._get_mission_launcher(),
                comm_bus=self._get_comm_bus(),
            )

        return self._team_orchestrator

    # ─────────────────────────────────────────────────────────────────
    # Helper Methods
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _generate_team_name(task: str, session_id: str) -> str:
        """Generate team name from task and session."""
        # Take first 3 words of task
        words = task.split()[:3]
        task_prefix = "_".join(words).lower()

        # Clean up
        import re

        task_prefix = re.sub(r"[^a-z0-9_]", "", task_prefix)

        # Add session suffix
        session_suffix = session_id[-8:] if len(session_id) > 8 else session_id

        return f"team_{task_prefix}_{session_suffix}"
