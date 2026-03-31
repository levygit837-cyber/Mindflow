"""
Unit tests for SubTeamSession and SubTeamResult.

Tests session state tracking and result aggregation for sub-teams.
"""

import pytest
from datetime import datetime

from mindflow_backend.execution.sub_teams.sub_team_config import SubTeamConfig


class TestSubTeamSession:
    """Test SubTeamSession dataclass."""

    def test_create_sub_team_session(self):
        """Should be able to create SubTeamSession with required fields."""
        from mindflow_backend.execution.sub_teams.sub_team_session import (
            SubTeamSession,
        )

        config = SubTeamConfig(max_agents=3, timeout_seconds=45.0)

        session = SubTeamSession(
            session_id="sub-session-123",
            parent_agent_id="parent-789",
            sub_team_config=config,
            depth=1,
            model_tier="tier-2",
        )

        assert session.session_id == "sub-session-123"
        assert session.parent_agent_id == "parent-789"
        assert session.sub_team_config is config
        assert session.depth == 1
        assert session.model_tier == "tier-2"

    def test_sub_team_session_depth_validation(self):
        """Depth should be validated (must be 1 for sub-teams)."""
        from mindflow_backend.execution.sub_teams.sub_team_session import (
            SubTeamSession,
        )

        config = SubTeamConfig()

        # Depth 1 is valid
        session = SubTeamSession(
            session_id="sub-session-123",
            parent_agent_id="parent-789",
            sub_team_config=config,
            depth=1,
        )
        assert session.depth == 1

    def test_sub_team_session_with_timestamps(self):
        """SubTeamSession should track start and end times."""
        from mindflow_backend.execution.sub_teams.sub_team_session import (
            SubTeamSession,
        )

        config = SubTeamConfig()
        started_at = datetime.now()

        session = SubTeamSession(
            session_id="sub-session-123",
            parent_agent_id="parent-789",
            sub_team_config=config,
            depth=1,
            started_at=started_at,
        )

        assert session.started_at == started_at
        assert session.completed_at is None


class TestSubTeamResult:
    """Test SubTeamResult dataclass."""

    def test_create_sub_team_result(self):
        """Should be able to create SubTeamResult with aggregated data."""
        from mindflow_backend.execution.sub_teams.sub_team_session import (
            SubTeamResult,
        )

        result = SubTeamResult(
            sub_agent_count=3,
            success_count=3,
            total_duration=45.0,
            sub_agent_results=[
                {"agent_id": "sub-1", "success": True, "duration": 15.0},
                {"agent_id": "sub-2", "success": True, "duration": 15.0},
                {"agent_id": "sub-3", "success": True, "duration": 15.0},
            ],
        )

        assert result.sub_agent_count == 3
        assert result.success_count == 3
        assert result.total_duration == 45.0
        assert len(result.sub_agent_results) == 3

    def test_sub_team_result_with_failures(self):
        """SubTeamResult should handle partial failures."""
        from mindflow_backend.execution.sub_teams.sub_team_session import (
            SubTeamResult,
        )

        result = SubTeamResult(
            sub_agent_count=3,
            success_count=2,
            total_duration=50.0,
            sub_agent_results=[
                {"agent_id": "sub-1", "success": True, "duration": 15.0},
                {"agent_id": "sub-2", "success": True, "duration": 20.0},
                {"agent_id": "sub-3", "success": False, "duration": 15.0, "error": "Timeout"},
            ],
        )

        assert result.sub_agent_count == 3
        assert result.success_count == 2
        assert result.total_duration == 50.0

    def test_sub_team_result_synthesis(self):
        """SubTeamResult should include synthesis of sub-agent outputs."""
        from mindflow_backend.execution.sub_teams.sub_team_session import (
            SubTeamResult,
        )

        result = SubTeamResult(
            sub_agent_count=3,
            success_count=3,
            total_duration=45.0,
            sub_agent_results=[],
            synthesis="Combined research findings from 3 sub-agents",
        )

        assert result.synthesis == "Combined research findings from 3 sub-agents"

    def test_sub_team_result_default_values(self):
        """SubTeamResult should have sensible defaults."""
        from mindflow_backend.execution.sub_teams.sub_team_session import (
            SubTeamResult,
        )

        result = SubTeamResult(
            sub_agent_count=0,
            success_count=0,
            total_duration=0.0,
        )

        assert result.sub_agent_count == 0
        assert result.success_count == 0
        assert result.total_duration == 0.0
        assert result.sub_agent_results == []
        assert result.synthesis == ""


class TestSubTeamSessionIntegration:
    """Test integration between SubTeamSession and SubTeamResult."""

    def test_session_to_result_conversion(self):
        """Should be able to create SubTeamResult from SubTeamSession."""
        from mindflow_backend.execution.sub_teams.sub_team_session import (
            SubTeamSession,
            SubTeamResult,
        )

        config = SubTeamConfig(max_agents=3)
        started_at = datetime.now()

        session = SubTeamSession(
            session_id="sub-session-123",
            parent_agent_id="parent-789",
            sub_team_config=config,
            depth=1,
            started_at=started_at,
        )

        # Simulate completion
        completed_at = datetime.now()
        duration = (completed_at - started_at).total_seconds()

        result = SubTeamResult(
            sub_agent_count=3,
            success_count=3,
            total_duration=duration,
            sub_agent_results=[],
        )

        assert result.sub_agent_count == config.max_agents
        assert result.total_duration >= 0
