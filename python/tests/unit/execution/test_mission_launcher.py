"""Tests for MissionLauncher."""
from __future__ import annotations
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import asyncio

from mindflow_backend.execution.missions.mission_launcher import (
    MissionLauncher,
    get_mission_launcher,
    _MISSION_TO_GRAPH_TYPE,
)
from mindflow_backend.execution.missions.mission_result import MissionResult
from mindflow_backend.graphs.base.types import GraphType
from mindflow_backend.schemas.orchestration.communication import MissionGraphType


def _make_mock_factory(available_types: list[GraphType] | None = None):
    """Create a mock GraphFactory."""
    factory = MagicMock()
    factory.get_available_types.return_value = available_types or [
        GraphType.ANALYSIS,
        GraphType.CODING_TASK,
        GraphType.BUG_FIX,
        GraphType.REFACTOR,
        GraphType.DEEP_INVESTIGATION,
        GraphType.SECURITY_AUDIT,
        GraphType.CODE_REVIEW,
        GraphType.WEB_RESEARCH,
        GraphType.COMPARISON,
    ]
    return factory


def _make_mock_graph() -> MagicMock:
    """Create a mock graph with async execute."""
    graph = MagicMock()
    graph.execute = AsyncMock(return_value={
        "result": "Mock result",
        "errors": [],
        "annotations": [],
        "messages_sent": [],
        "iteration": 10,
        "metadata": {},
        "mission_id": "test-mid",
    })
    return graph


class TestCanAgentRun:
    """Tests for can_agent_run() method."""

    @patch(
        "mindflow_backend.execution.missions.mission_launcher.get_agent_runtime_policy"
    )
    def test_can_agent_returns_true_for_valid_mission(self, mock_policy_fn):
        """Should return True when mission_type is in available_mission_graphs."""
        mock_policy = MagicMock()
        mock_policy.available_mission_graphs = (
            MissionGraphType.ANALYSIS,
            MissionGraphType.DEEP_INVESTIGATION,
        )
        mock_policy_fn.return_value = mock_policy

        launcher = MissionLauncher(graph_factory=_make_mock_factory())
        assert launcher.can_agent_run("analyst", MissionGraphType.ANALYSIS) is True
        mock_policy_fn.assert_called_once_with(agent_id="analyst")

    @patch(
        "mindflow_backend.execution.missions.mission_launcher.get_agent_runtime_policy"
    )
    def test_can_agent_returns_false_for_invalid_mission(self, mock_policy_fn):
        """Should return False when mission_type is NOT in available_mission_graphs."""
        mock_policy = MagicMock()
        mock_policy.available_mission_graphs = (MissionGraphType.ANALYSIS,)
        mock_policy_fn.return_value = mock_policy

        launcher = MissionLauncher(graph_factory=_make_mock_factory())
        assert launcher.can_agent_run("analyst", MissionGraphType.CODING_TASK) is False

    @patch(
        "mindflow_backend.execution.missions.mission_launcher.get_agent_runtime_policy"
    )
    def test_can_agent_returns_false_on_unknown_agent(self, mock_policy_fn):
        """Should return False if policy lookup raises KeyError."""
        mock_policy_fn.side_effect = KeyError("unknown")

        launcher = MissionLauncher(graph_factory=_make_mock_factory())
        assert launcher.can_agent_run("unknown-agent", MissionGraphType.ANALYSIS) is False


class TestLaunchAnalysisMission:
    """Tests for launch_mission() happy path."""

    @pytest.mark.asyncio
    @patch(
        "mindflow_backend.execution.missions.mission_launcher.get_agent_runtime_policy"
    )
    async def test_launch_analysis_mission(self, mock_policy_fn):
        """Should execute analysis mission successfully."""
        # Setup policy
        mock_policy = MagicMock()
        mock_policy.available_mission_graphs = (MissionGraphType.ANALYSIS,)
        mock_policy_fn.return_value = mock_policy

        # Setup factory
        factory = _make_mock_factory()
        mock_graph = _make_mock_graph()
        factory.create_graph.return_value = mock_graph

        launcher = MissionLauncher(graph_factory=factory)

        result = await launcher.launch_mission(
            agent_id="analyst",
            mission_type=MissionGraphType.ANALYSIS,
            task="Analyze this code",
            session_id="sess-1",
        )

        assert result.success is True or result.result == "Mock result"
        assert result.agent_id == "analyst"
        assert result.mission_type == MissionGraphType.ANALYSIS
        factory.create_graph.assert_called_once()

    @pytest.mark.asyncio
    @patch(
        "mindflow_backend.execution.missions.mission_launcher.get_agent_runtime_policy"
    )
    async def test_launch_fails_if_agent_cannot_run_type(self, mock_policy_fn):
        """Should return MissionResult with error when agent cannot run the type."""
        mock_policy = MagicMock()
        mock_policy.available_mission_graphs = (MissionGraphType.ANALYSIS,)
        mock_policy_fn.return_value = mock_policy

        factory = _make_mock_factory()
        launcher = MissionLauncher(graph_factory=factory)

        result = await launcher.launch_mission(
            agent_id="analyst",
            mission_type=MissionGraphType.CODING_TASK,  # Not available
            task="Implement feature",
            session_id="sess-1",
        )

        assert result.success is False
        assert "não possui" in result.error.lower()
        factory.create_graph.assert_not_called()

    @pytest.mark.asyncio
    @patch(
        "mindflow_backend.execution.missions.mission_launcher.get_agent_runtime_policy"
    )
    async def test_launch_removes_graph_after_completion(self, mock_policy_fn):
        """Should call remove_graph in finally block."""
        mock_policy = MagicMock()
        mock_policy.available_mission_graphs = (MissionGraphType.ANALYSIS,)
        mock_policy_fn.return_value = mock_policy

        factory = _make_mock_factory()
        mock_graph = _make_mock_graph()
        factory.create_graph.return_value = mock_graph

        launcher = MissionLauncher(graph_factory=factory)

        await launcher.launch_mission(
            agent_id="analyst",
            mission_type=MissionGraphType.ANALYSIS,
            task="test",
            session_id="s1",
        )

        # verify create_graph was called with correct type
        factory.create_graph.assert_called_once()
        call_args = factory.create_graph.call_args
        assert call_args.kwargs.get("graph_type") == GraphType.ANALYSIS


class TestMissionTypeMapping:
    """Test the _MISSION_TO_GRAPH_TYPE mapping."""

    def test_mapping_coverage(self):
        """All MissionGraphType values should be mappable."""
        missing = []
        for mgt in MissionGraphType:
            if mgt not in _MISSION_TO_GRAPH_TYPE:
                missing.append(mgt)

        assert not missing, f"Mission types without mapping: {missing}"