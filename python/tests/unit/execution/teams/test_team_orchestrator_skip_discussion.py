"""
Unit tests for TeamOrchestrator skip_discussion parameter.

Tests conditional Discussion phase execution for sub-team support.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestTeamOrchestratorSkipDiscussion:
    """Test skip_discussion parameter in TeamOrchestrator."""

    @pytest.mark.asyncio
    async def test_run_full_team_session_with_discussion_by_default(self):
        """By default, Discussion phase should run."""
        from mindflow_backend.execution.teams.team_orchestrator import (
            TeamOrchestrator,
        )

        # Mock dependencies
        team_manager = MagicMock()
        mission_launcher = MagicMock()
        comm_bus = MagicMock()

        orchestrator = TeamOrchestrator(team_manager, mission_launcher, comm_bus)

        # Mock all phase methods
        orchestrator._phase_formation = AsyncMock()
        orchestrator._phase_discussion = AsyncMock()
        orchestrator._phase_missions = AsyncMock()
        orchestrator._phase_synthesis = AsyncMock(return_value="Synthesis result")

        # Run without skip_discussion parameter (default behavior)
        result = await orchestrator.run_full_team_session(
            task="Test task",
            agent_ids=["agent-1", "agent-2"],
            session_id="session-123",
        )

        # Verify Discussion phase was called
        orchestrator._phase_discussion.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_full_team_session_skip_discussion_true(self):
        """When skip_discussion=True, Discussion phase should be skipped."""
        from mindflow_backend.execution.teams.team_orchestrator import (
            TeamOrchestrator,
        )

        # Mock dependencies
        team_manager = MagicMock()
        mission_launcher = MagicMock()
        comm_bus = MagicMock()

        orchestrator = TeamOrchestrator(team_manager, mission_launcher, comm_bus)

        # Mock all phase methods
        orchestrator._phase_formation = AsyncMock()
        orchestrator._phase_discussion = AsyncMock()
        orchestrator._phase_missions = AsyncMock()
        orchestrator._phase_synthesis = AsyncMock(return_value="Synthesis result")

        # Run with skip_discussion=True
        result = await orchestrator.run_full_team_session(
            task="Test task",
            agent_ids=["agent-1", "agent-2"],
            session_id="session-123",
            skip_discussion=True,
        )

        # Verify Discussion phase was NOT called
        orchestrator._phase_discussion.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_full_team_session_skip_discussion_false(self):
        """When skip_discussion=False explicitly, Discussion phase should run."""
        from mindflow_backend.execution.teams.team_orchestrator import (
            TeamOrchestrator,
        )

        # Mock dependencies
        team_manager = MagicMock()
        mission_launcher = MagicMock()
        comm_bus = MagicMock()

        orchestrator = TeamOrchestrator(team_manager, mission_launcher, comm_bus)

        # Mock all phase methods
        orchestrator._phase_formation = AsyncMock()
        orchestrator._phase_discussion = AsyncMock()
        orchestrator._phase_missions = AsyncMock()
        orchestrator._phase_synthesis = AsyncMock(return_value="Synthesis result")

        # Run with skip_discussion=False explicitly
        result = await orchestrator.run_full_team_session(
            task="Test task",
            agent_ids=["agent-1", "agent-2"],
            session_id="session-123",
            skip_discussion=False,
        )

        # Verify Discussion phase was called
        orchestrator._phase_discussion.assert_called_once()

    @pytest.mark.asyncio
    async def test_other_phases_run_when_discussion_skipped(self):
        """When Discussion is skipped, other phases should still run."""
        from mindflow_backend.execution.teams.team_orchestrator import (
            TeamOrchestrator,
        )

        # Mock dependencies
        team_manager = MagicMock()
        mission_launcher = MagicMock()
        comm_bus = MagicMock()

        orchestrator = TeamOrchestrator(team_manager, mission_launcher, comm_bus)

        # Mock all phase methods
        orchestrator._phase_formation = AsyncMock()
        orchestrator._phase_discussion = AsyncMock()
        orchestrator._phase_missions = AsyncMock()
        orchestrator._phase_synthesis = AsyncMock(return_value="Synthesis result")

        # Run with skip_discussion=True
        result = await orchestrator.run_full_team_session(
            task="Test task",
            agent_ids=["agent-1", "agent-2"],
            session_id="session-123",
            skip_discussion=True,
        )

        # Verify Formation, Missions, and Synthesis still ran
        orchestrator._phase_formation.assert_called_once()
        orchestrator._phase_missions.assert_called_once()
        orchestrator._phase_synthesis.assert_called_once()

        # But Discussion was skipped
        orchestrator._phase_discussion.assert_not_called()
