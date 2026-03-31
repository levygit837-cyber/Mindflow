"""
Tests for MissionLauncher sub-team integration.

Phase 2: MissionLauncher Integration
Tests sub-team detection, routing, and recursion prevention.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

from mindflow_backend.execution.missions.mission_context import MissionContext
from mindflow_backend.execution.missions.mission_result import MissionResult
from mindflow_backend.execution.sub_teams.sub_team_config import SubTeamConfig
from mindflow_backend.execution.sub_teams.sub_team_session import SubTeamResult
from mindflow_backend.schemas.orchestration.communication import MissionGraphType


@pytest.fixture
def mock_graph_factory():
    """Mock GraphFactory for testing."""
    factory = Mock()
    factory.get_available_types.return_value = [
        MagicMock(value="analysis"),
        MagicMock(value="web_research"),
    ]
    factory.create_graph.return_value = AsyncMock()
    return factory


@pytest.fixture
def mock_comm_bus():
    """Mock CommunicationBus for testing."""
    return AsyncMock()


@pytest.fixture
def mission_launcher(mock_graph_factory, mock_comm_bus):
    """MissionLauncher instance with mocked dependencies."""
    from mindflow_backend.execution.missions.mission_launcher import MissionLauncher

    return MissionLauncher(
        graph_factory=mock_graph_factory,
        comm_bus=mock_comm_bus,
    )


# ---------------------------------------------------------------------------
# Test 1: Detect Sub-Team Support
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_sub_team_support_true(mission_launcher):
    """Test detection when agent supports sub-teams."""
    agent_id = "researcher_001"
    mission_type = MissionGraphType.WEB_RESEARCH
    task = "Research topic A"
    session_id = str(uuid4())

    # Mock RuntimePolicy with sub-team support
    mock_policy = Mock()
    mock_policy.supports_sub_team = True
    mock_policy.sub_team_config = SubTeamConfig()
    mock_policy.available_mission_graphs = [MissionGraphType.WEB_RESEARCH]

    with patch(
        "mindflow_backend.execution.missions.mission_launcher.get_agent_runtime_policy",
        return_value=mock_policy,
    ):
        # Should detect sub-team support
        # (We'll verify this by checking if SubTeamLauncher is called in next test)
        pass


@pytest.mark.asyncio
async def test_detect_sub_team_support_false(mission_launcher):
    """Test detection when agent does not support sub-teams."""
    agent_id = "analyst_001"
    mission_type = MissionGraphType.ANALYSIS
    task = "Analyze code"
    session_id = str(uuid4())

    # Mock RuntimePolicy without sub-team support
    mock_policy = Mock()
    mock_policy.supports_sub_team = False
    mock_policy.sub_team_config = None
    mock_policy.available_mission_graphs = [MissionGraphType.ANALYSIS]

    with patch(
        "mindflow_backend.execution.missions.mission_launcher.get_agent_runtime_policy",
        return_value=mock_policy,
    ):
        # Should NOT use sub-team launcher
        pass


# ---------------------------------------------------------------------------
# Test 2: Route to SubTeamLauncher
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_route_to_sub_team_launcher(mission_launcher, mock_graph_factory):
    """Test routing to SubTeamLauncher when sub-team is supported."""
    agent_id = "researcher_001"
    mission_type = MissionGraphType.WEB_RESEARCH
    task = "Research multiple topics"
    session_id = str(uuid4())

    # Mock RuntimePolicy with sub-team support
    mock_policy = Mock()
    mock_policy.supports_sub_team = True
    mock_policy.sub_team_config = SubTeamConfig()
    mock_policy.available_mission_graphs = [MissionGraphType.WEB_RESEARCH]

    # Mock SubTeamLauncher
    mock_sub_team_result = SubTeamResult(
        sub_agent_count=3,
        success_count=3,
        total_duration=45.0,
        synthesis="Research complete",
    )

    with patch(
        "mindflow_backend.execution.missions.mission_launcher.get_agent_runtime_policy",
        return_value=mock_policy,
    ), patch(
        "mindflow_backend.execution.missions.mission_launcher.SubTeamLauncher"
    ) as mock_launcher_class:
        mock_launcher_instance = AsyncMock()
        mock_launcher_instance.launch_sub_team.return_value = mock_sub_team_result
        mock_launcher_class.return_value = mock_launcher_instance

        result = await mission_launcher.launch_mission(
            agent_id=agent_id,
            mission_type=mission_type,
            task=task,
            session_id=session_id,
        )

        # Verify SubTeamLauncher was used
        mock_launcher_class.assert_called_once()
        mock_launcher_instance.launch_sub_team.assert_called_once()

        # Verify SubTeamResult is attached to MissionResult
        assert result.sub_team_result is not None
        assert result.sub_team_result == mock_sub_team_result


# ---------------------------------------------------------------------------
# Test 3: Prevent Sub-Agent Recursion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prevent_sub_agent_recursion(mission_launcher, mock_graph_factory):
    """Test that sub-agents cannot spawn sub-sub-teams."""
    agent_id = "topic_researcher_a"
    mission_type = MissionGraphType.WEB_RESEARCH
    task = "Research sub-topic"
    session_id = str(uuid4())

    # Mock RuntimePolicy with sub-team support
    mock_policy = Mock()
    mock_policy.supports_sub_team = True
    mock_policy.sub_team_config = SubTeamConfig()
    mock_policy.available_mission_graphs = [MissionGraphType.WEB_RESEARCH]

    # Mock graph execution
    mock_graph = AsyncMock()
    mock_graph.execute.return_value = {
        "agent_id": agent_id,
        "task": task,
        "result": "Done",
        "success": True,
        "is_sub_agent": True,  # This agent is already a sub-agent
    }
    mock_graph_factory.create_graph.return_value = mock_graph

    with patch(
        "mindflow_backend.execution.missions.mission_launcher.get_agent_runtime_policy",
        return_value=mock_policy,
    ), patch(
        "mindflow_backend.execution.missions.mission_launcher.SubTeamLauncher"
    ) as mock_launcher_class:
        # Pass is_sub_agent=True in metadata to simulate sub-agent context
        result = await mission_launcher.launch_mission(
            agent_id=agent_id,
            mission_type=mission_type,
            task=task,
            session_id=session_id,
            metadata={"is_sub_agent": True},
        )

        # Verify SubTeamLauncher was NOT called (recursion prevented)
        mock_launcher_class.assert_not_called()

        # Verify normal mission execution happened instead
        assert result.success is True
        assert result.sub_team_result is None


# ---------------------------------------------------------------------------
# Test 4: Fallback to Normal Mission
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fallback_to_normal_mission(mission_launcher, mock_graph_factory):
    """Test fallback when sub-team not supported."""
    agent_id = "analyst_001"
    mission_type = MissionGraphType.ANALYSIS
    task = "Analyze code"
    session_id = str(uuid4())

    # Mock RuntimePolicy without sub-team support
    mock_policy = Mock()
    mock_policy.supports_sub_team = False
    mock_policy.sub_team_config = None
    mock_policy.available_mission_graphs = [MissionGraphType.ANALYSIS]

    # Mock graph execution
    mock_graph = AsyncMock()
    mock_graph.execute.return_value = {
        "agent_id": agent_id,
        "task": task,
        "result": "Analysis complete",
        "success": True,
    }
    mock_graph_factory.create_graph.return_value = mock_graph

    with patch(
        "mindflow_backend.execution.missions.mission_launcher.get_agent_runtime_policy",
        return_value=mock_policy,
    ):
        result = await mission_launcher.launch_mission(
            agent_id=agent_id,
            mission_type=mission_type,
            task=task,
            session_id=session_id,
        )

        # Verify normal execution
        assert result.success is True
        assert result.sub_team_result is None


# ---------------------------------------------------------------------------
# Test 5: SubTeamResult in MissionResult
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sub_team_result_in_mission_result(mission_launcher):
    """Test SubTeamResult is properly attached to MissionResult."""
    agent_id = "researcher_001"
    mission_type = MissionGraphType.WEB_RESEARCH
    task = "Research topics"
    session_id = str(uuid4())

    # Mock RuntimePolicy
    mock_policy = Mock()
    mock_policy.supports_sub_team = True
    mock_policy.sub_team_config = SubTeamConfig()
    mock_policy.available_mission_graphs = [MissionGraphType.WEB_RESEARCH]

    # Mock SubTeamResult with specific data
    mock_sub_team_result = SubTeamResult(
        sub_agent_count=3,
        success_count=2,
        total_duration=50.0,
        synthesis="Partial research complete",
        errors=["Agent 3 failed"],
    )

    with patch(
        "mindflow_backend.execution.missions.mission_launcher.get_agent_runtime_policy",
        return_value=mock_policy,
    ), patch(
        "mindflow_backend.execution.missions.mission_launcher.SubTeamLauncher"
    ) as mock_launcher_class:
        mock_launcher_instance = AsyncMock()
        mock_launcher_instance.launch_sub_team.return_value = mock_sub_team_result
        mock_launcher_class.return_value = mock_launcher_instance

        result = await mission_launcher.launch_mission(
            agent_id=agent_id,
            mission_type=mission_type,
            task=task,
            session_id=session_id,
        )

        # Verify SubTeamResult details are preserved
        assert result.sub_team_result is not None
        assert result.sub_team_result.sub_agent_count == 3
        assert result.sub_team_result.success_count == 2
        assert result.sub_team_result.success_rate == pytest.approx(0.666, rel=0.01)
        assert len(result.sub_team_result.errors) == 1


# ---------------------------------------------------------------------------
# Test 6: Sub-Team Config Validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sub_team_config_required(mission_launcher):
    """Test that sub_team_config must be present when supports_sub_team=True."""
    agent_id = "researcher_001"
    mission_type = MissionGraphType.WEB_RESEARCH
    task = "Research topic"
    session_id = str(uuid4())

    # Mock RuntimePolicy with supports_sub_team=True but no config
    mock_policy = Mock()
    mock_policy.supports_sub_team = True
    mock_policy.sub_team_config = None  # Missing config
    mock_policy.available_mission_graphs = [MissionGraphType.WEB_RESEARCH]

    # Mock graph for fallback
    mock_graph = AsyncMock()
    mock_graph.execute.return_value = {
        "agent_id": agent_id,
        "task": task,
        "result": "Done",
        "success": True,
    }
    mission_launcher._graph_factory.create_graph.return_value = mock_graph

    with patch(
        "mindflow_backend.execution.missions.mission_launcher.get_agent_runtime_policy",
        return_value=mock_policy,
    ):
        result = await mission_launcher.launch_mission(
            agent_id=agent_id,
            mission_type=mission_type,
            task=task,
            session_id=session_id,
        )

        # Should fallback to normal mission when config is missing
        assert result.success is True
        assert result.sub_team_result is None
