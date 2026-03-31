"""
Unit tests for MissionResult sub-team tracking.

Tests the new sub_team_result field and its integration with
to_delegation_result_data() serialization.
"""

import pytest
from datetime import datetime

from mindflow_backend.execution.missions.mission_result import (
    MissionResult,
    MemoryAnnotationRef,
)
from mindflow_backend.execution.sub_teams.sub_team_config import SubTeamConfig
from mindflow_backend.schemas.orchestration.communication import MissionGraphType


# Mock SubTeamResult for testing (will be implemented in Phase 3)
class MockSubTeamResult:
    """Mock SubTeamResult for testing MissionResult integration."""

    def __init__(
        self,
        sub_agent_count: int = 3,
        success_count: int = 3,
        total_duration: float = 45.0,
    ):
        self.sub_agent_count = sub_agent_count
        self.success_count = success_count
        self.total_duration = total_duration
        self.sub_agent_results = [
            {"agent_id": f"sub-{i}", "success": True} for i in range(sub_agent_count)
        ]


class TestMissionResultSubTeamField:
    """Test sub_team_result field in MissionResult."""

    def test_default_sub_team_result_is_none(self):
        """sub_team_result should default to None."""
        result = MissionResult(
            agent_id="agent-123",
            mission_type=MissionGraphType.WEB_RESEARCH,
            success=True,
            result="Research complete",
        )

        assert result.sub_team_result is None

    def test_create_result_with_sub_team_result(self):
        """Should be able to create MissionResult with sub_team_result."""
        sub_team_result = MockSubTeamResult(
            sub_agent_count=3, success_count=3, total_duration=45.0
        )

        result = MissionResult(
            agent_id="agent-123",
            mission_type=MissionGraphType.WEB_RESEARCH,
            success=True,
            result="Research complete with sub-team",
            sub_team_result=sub_team_result,
        )

        assert result.sub_team_result is sub_team_result
        assert result.sub_team_result.sub_agent_count == 3
        assert result.sub_team_result.success_count == 3
        assert result.sub_team_result.total_duration == 45.0

    def test_sub_team_result_preserved_in_from_graph_state(self):
        """from_graph_state() should preserve sub_team_result from metadata."""
        sub_team_result = MockSubTeamResult()

        state = {
            "result": "Analysis complete",
            "errors": [],
            "annotations": [],
            "messages_sent": [],
            "iteration": 5,
            "metadata": {"sub_team_result": sub_team_result},
        }

        result = MissionResult.from_graph_state(
            state=state,
            agent_id="agent-123",
            mission_type=MissionGraphType.ANALYSIS,
        )

        assert result.sub_team_result is sub_team_result


class TestMissionResultToDelegationResultData:
    """Test to_delegation_result_data() includes sub-team data."""

    def test_to_delegation_result_without_sub_team(self):
        """to_delegation_result_data() should work without sub_team_result."""
        result = MissionResult(
            agent_id="agent-123",
            mission_type=MissionGraphType.ANALYSIS,
            success=True,
            result="Analysis complete",
            duration_seconds=30.0,
            iterations=5,
        )

        data = result.to_delegation_result_data()

        assert data["status"] == "completed"
        assert data["full_output"] == "Analysis complete"
        assert "sub_team_summary" not in data

    def test_to_delegation_result_with_sub_team(self):
        """to_delegation_result_data() should include sub_team_summary."""
        sub_team_result = MockSubTeamResult(
            sub_agent_count=3, success_count=3, total_duration=45.0
        )

        result = MissionResult(
            agent_id="agent-123",
            mission_type=MissionGraphType.WEB_RESEARCH,
            success=True,
            result="Research complete",
            sub_team_result=sub_team_result,
        )

        data = result.to_delegation_result_data()

        assert data["status"] == "completed"
        assert "sub_team_summary" in data
        assert data["sub_team_summary"]["sub_agent_count"] == 3
        assert data["sub_team_summary"]["success_count"] == 3
        assert data["sub_team_summary"]["total_duration"] == 45.0

    def test_to_delegation_result_with_failed_sub_team(self):
        """to_delegation_result_data() should handle partial sub-team failures."""
        sub_team_result = MockSubTeamResult(
            sub_agent_count=3, success_count=2, total_duration=50.0
        )

        result = MissionResult(
            agent_id="agent-123",
            mission_type=MissionGraphType.WEB_RESEARCH,
            success=True,  # Parent can still succeed with partial sub-team failure
            result="Research complete (partial)",
            sub_team_result=sub_team_result,
        )

        data = result.to_delegation_result_data()

        assert data["status"] == "completed"
        assert data["sub_team_summary"]["sub_agent_count"] == 3
        assert data["sub_team_summary"]["success_count"] == 2


class TestMissionResultEdgeCases:
    """Test edge cases for sub_team_result."""

    def test_failed_mission_with_sub_team_result(self):
        """Failed mission can still have sub_team_result."""
        sub_team_result = MockSubTeamResult(
            sub_agent_count=3, success_count=1, total_duration=60.0
        )

        result = MissionResult(
            agent_id="agent-123",
            mission_type=MissionGraphType.WEB_RESEARCH,
            success=False,
            result="",
            error="Sub-team timeout",
            sub_team_result=sub_team_result,
        )

        assert result.success is False
        assert result.sub_team_result is not None
        assert result.error == "Sub-team timeout"

    def test_sub_team_result_in_metadata(self):
        """sub_team_result can be stored in metadata for serialization."""
        sub_team_result = MockSubTeamResult()

        result = MissionResult(
            agent_id="agent-123",
            mission_type=MissionGraphType.WEB_RESEARCH,
            success=True,
            result="Research complete",
            metadata={"custom_key": "custom_value"},
            sub_team_result=sub_team_result,
        )

        # Metadata should be independent of sub_team_result
        assert result.metadata["custom_key"] == "custom_value"
        assert result.sub_team_result is sub_team_result
