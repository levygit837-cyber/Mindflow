"""
SubTeamLauncher — Orchestrates sub-team lifecycle.

Re-uses TeamOrchestrator with skip_discussion=True for fast execution.
Enforces constraints: max depth 1, timeout ≤60s, tier-2 models.

Phase 1: SubTeamLauncher Core Infrastructure
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from mindflow_backend.execution.sub_teams.sub_team_config import SubTeamConfig
from mindflow_backend.execution.sub_teams.sub_team_session import (
    SubTeamResult,
    SubTeamSession,
)
from mindflow_backend.infra.logging import get_logger

if TYPE_CHECKING:
    from mindflow_backend.communication.bus.communication_bus import CommunicationBus
    from mindflow_backend.execution.missions.mission_launcher import MissionLauncher
    from mindflow_backend.execution.teams.team_orchestrator import TeamOrchestrator

logger = get_logger(__name__)


class SubTeamLauncher:
    """
    Launches and orchestrates sub-agent teams.

    Sub-teams execute without Discussion phase for faster execution,
    using tier-2 models for cost control.

    Constraints:
    - Max depth: 1 (no sub-sub-teams)
    - Timeout: ≤60s
    - Models: tier-2 (fast/cheap)
    - No Discussion phase
    """

    def __init__(
        self,
        team_orchestrator: TeamOrchestrator,
        mission_launcher: MissionLauncher,
        comm_bus: CommunicationBus,
    ) -> None:
        """
        Initialize SubTeamLauncher.

        Args:
            team_orchestrator: TeamOrchestrator instance for running team sessions
            mission_launcher: MissionLauncher for individual missions
            comm_bus: CommunicationBus for agent communication
        """
        self._team_orchestrator = team_orchestrator
        self._mission_launcher = mission_launcher
        self._comm_bus = comm_bus
        self._logger = get_logger(__name__)

    async def launch_sub_team(
        self,
        parent_agent_id: str,
        sub_team_config: SubTeamConfig,
        task: str,
        session_id: str,
        sub_agent_ids: list[str],
    ) -> SubTeamResult:
        """
        Launch a sub-team and aggregate results.

        Args:
            parent_agent_id: ID of the parent Specialist agent
            sub_team_config: Configuration for sub-team behavior
            task: Task description for the sub-team
            session_id: Session ID for tracking
            sub_agent_ids: List of sub-agent IDs to spawn

        Returns:
            SubTeamResult with aggregated results from all sub-agents

        Raises:
            ValueError: If sub_agent_ids count violates config constraints
            asyncio.TimeoutError: If execution exceeds timeout
        """
        # Validate agent count
        agent_count = len(sub_agent_ids)
        if agent_count < sub_team_config.min_agents:
            raise ValueError(
                f"sub_agent_ids count ({agent_count}) is less than "
                f"min_agents ({sub_team_config.min_agents})"
            )
        if agent_count > sub_team_config.max_agents:
            raise ValueError(
                f"sub_agent_ids count ({agent_count}) exceeds "
                f"max_agents ({sub_team_config.max_agents})"
            )

        # Create SubTeamSession
        sub_team_session = SubTeamSession(
            session_id=session_id,
            parent_agent_id=parent_agent_id,
            sub_team_config=sub_team_config,
            depth=1,  # Always 1 for sub-teams (no recursion)
            model_tier=sub_team_config.model_tier,
            sub_agent_ids=sub_agent_ids,
        )

        self._logger.info(
            "sub_team_launch_start",
            extra={
                "session_id": session_id,
                "parent_agent_id": parent_agent_id,
                "sub_agent_count": agent_count,
                "task": task[:100],
            },
        )

        try:
            # Execute team session with timeout enforcement
            team_result = await asyncio.wait_for(
                self._team_orchestrator.run_full_team_session(
                    task=task,
                    agent_ids=sub_agent_ids,
                    session_id=session_id,
                    skip_discussion=sub_team_config.skip_discussion,
                ),
                timeout=sub_team_config.timeout_seconds,
            )

            # Mark session as completed
            sub_team_session.mark_completed()

            # Aggregate results
            sub_team_result = self._aggregate_results(
                team_result=team_result,
                sub_agent_count=agent_count,
            )

            self._logger.info(
                "sub_team_launch_complete",
                extra={
                    "session_id": session_id,
                    "success_count": sub_team_result.success_count,
                    "total_count": sub_team_result.sub_agent_count,
                    "duration": sub_team_result.total_duration,
                },
            )

            return sub_team_result

        except asyncio.TimeoutError:
            self._logger.error(
                "sub_team_timeout",
                extra={
                    "session_id": session_id,
                    "timeout_seconds": sub_team_config.timeout_seconds,
                },
            )
            raise

        except Exception as exc:
            self._logger.error(
                "sub_team_launch_failed",
                extra={
                    "session_id": session_id,
                    "error": str(exc),
                },
            )
            # Return failure result instead of raising
            return SubTeamResult(
                sub_agent_count=agent_count,
                success_count=0,
                total_duration=0.0,
                sub_agent_results=[],
                synthesis="",
                errors=[str(exc)],
            )

    def _aggregate_results(
        self,
        team_result: Any,  # TeamSessionResult
        sub_agent_count: int,
    ) -> SubTeamResult:
        """
        Aggregate TeamSessionResult into SubTeamResult.

        Args:
            team_result: TeamSessionResult from TeamOrchestrator
            sub_agent_count: Expected number of sub-agents

        Returns:
            SubTeamResult with aggregated data
        """
        # Extract mission results
        sub_agent_results: list[dict[str, Any]] = []
        success_count = 0
        errors: list[str] = []

        for agent_id, mission_data in team_result.missions.items():
            sub_agent_results.append(mission_data)

            # Count successes
            if mission_data.get("status") == "completed":
                success_count += 1
            else:
                # Track failures
                error_msg = mission_data.get("error", f"Agent {agent_id} failed")
                errors.append(error_msg)

        # Add overall error if team session failed
        if not team_result.success and team_result.error:
            errors.append(team_result.error)

        # Extract synthesis from final_result
        synthesis = team_result.final_result if team_result.success else ""

        return SubTeamResult(
            sub_agent_count=sub_agent_count,
            success_count=success_count,
            total_duration=team_result.total_duration_seconds,
            sub_agent_results=sub_agent_results,
            synthesis=synthesis,
            errors=errors,
            metadata={
                "session_id": team_result.session_id,
                "chat_history_length": team_result.chat_history_length,
                "phases_completed": team_result.phases_completed,
            },
        )
