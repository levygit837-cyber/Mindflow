"""
Tests for SubTeamLauncher — orchestrates sub-team lifecycle.

Phase 1: SubTeamLauncher Core Infrastructure
Following TDD approach: write tests first, then implementation.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest

from mindflow_backend.execution.sub_teams.sub_team_config import SubTeamConfig
from mindflow_backend.execution.sub_teams.sub_team_session import (
    SubTeamResult,
    SubTeamSession,
)
from mindflow_backend.execution.teams.team_session import TeamSessionResult


@pytest.fixture
def mock_team_orchestrator():
    """Mock TeamOrchestrator for testing."""
    orchestrator = AsyncMock()
    orchestrator.run_full_team_session = AsyncMock()
    return orchestrator


@pytest.fixture
def mock_mission_launcher():
    """Mock MissionLauncher for testing."""
    launcher = Mock()
    return launcher


@pytest.fixture
def mock_comm_bus():
    """Mock CommunicationBus for testing."""
    bus = AsyncMock()
    return bus


@pytest.fixture
def sub_team_config():
    """Standard SubTeamConfig for testing."""
    return SubTeamConfig(
        model_tier="tier-2",
        max_agents=3,
        timeout_seconds=60.0,
        skip_discussion=True,
    )


@pytest.fixture
def sub_team_launcher(mock_team_orchestrator, mock_mission_launcher, mock_comm_bus):
    """SubTeamLauncher instance with mocked dependencies."""
    from mindflow_backend.execution.sub_teams.sub_team_launcher import SubTeamLauncher

    return SubTeamLauncher(
        team_orchestrator=mock_team_orchestrator,
        mission_launcher=mock_mission_launcher,
        comm_bus=mock_comm_bus,
    )


# ---------------------------------------------------------------------------
# Test 1: Initialization
# ---------------------------------------------------------------------------


def test_sub_team_launcher_initialization(
    mock_team_orchestrator, mock_mission_launcher, mock_comm_bus
):
    """Test SubTeamLauncher accepts required dependencies."""
    from mindflow_backend.execution.sub_teams.sub_team_launcher import SubTeamLauncher

    launcher = SubTeamLauncher(
        team_orchestrator=mock_team_orchestrator,
        mission_launcher=mock_mission_launcher,
        comm_bus=mock_comm_bus,
    )

    assert launcher._team_orchestrator is mock_team_orchestrator
    assert launcher._mission_launcher is mock_mission_launcher
    assert launcher._comm_bus is mock_comm_bus


# ---------------------------------------------------------------------------
# Test 2: Session Creation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_launch_sub_team_creates_session(
    sub_team_launcher, mock_team_orchestrator, sub_team_config
):
    """Test launch_sub_team creates SubTeamSession with depth=1."""
    parent_agent_id = "analyst_001"
    task = "Analyze authentication flow"
    session_id = str(uuid4())
    sub_agent_ids = ["context_analyst", "logic_analyst", "synthesis_analyst"]

    # Mock successful team session
    mock_team_orchestrator.run_full_team_session.return_value = TeamSessionResult(
        session_id=session_id,
        task=task,
        final_result="Analysis complete",
        success=True,
        missions={},
        chat_history_length=5,
        total_duration_seconds=30.0,
        phases_completed=["formation", "missions", "synthesis"],
    )

    result = await sub_team_launcher.launch_sub_team(
        parent_agent_id=parent_agent_id,
        sub_team_config=sub_team_config,
        task=task,
        session_id=session_id,
        sub_agent_ids=sub_agent_ids,
    )

    # Verify SubTeamResult was created
    assert isinstance(result, SubTeamResult)
    assert result.sub_agent_count == 3


# ---------------------------------------------------------------------------
# Test 3: Skip Discussion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_launch_sub_team_skips_discussion(
    sub_team_launcher, mock_team_orchestrator, sub_team_config
):
    """Test skip_discussion=True is passed to TeamOrchestrator."""
    parent_agent_id = "researcher_001"
    task = "Research topic A"
    session_id = str(uuid4())
    sub_agent_ids = ["topic_researcher_a", "topic_researcher_b"]

    mock_team_orchestrator.run_full_team_session.return_value = TeamSessionResult(
        session_id=session_id,
        task=task,
        final_result="Research complete",
        success=True,
        missions={},
        chat_history_length=3,
        total_duration_seconds=25.0,
        phases_completed=["formation", "missions", "synthesis"],
    )

    await sub_team_launcher.launch_sub_team(
        parent_agent_id=parent_agent_id,
        sub_team_config=sub_team_config,
        task=task,
        session_id=session_id,
        sub_agent_ids=sub_agent_ids,
    )

    # Verify skip_discussion=True was passed
    mock_team_orchestrator.run_full_team_session.assert_called_once()
    call_kwargs = mock_team_orchestrator.run_full_team_session.call_args.kwargs
    assert call_kwargs["skip_discussion"] is True


# ---------------------------------------------------------------------------
# Test 4: Timeout Enforcement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_launch_sub_team_enforces_timeout(
    sub_team_launcher, mock_team_orchestrator, sub_team_config
):
    """Test timeout ≤60s is enforced via asyncio.wait_for."""
    parent_agent_id = "coder_001"
    task = "Write unit tests"
    session_id = str(uuid4())
    sub_agent_ids = ["architect_agent", "writer_agent"]

    # Mock slow execution that exceeds timeout
    async def slow_execution(*args, **kwargs):
        await asyncio.sleep(70.0)  # Exceeds 60s timeout
        return TeamSessionResult(
            session_id=session_id,
            task=task,
            final_result="",
            success=False,
            missions={},
            chat_history_length=0,
            total_duration_seconds=70.0,
            phases_completed=[],
        )

    mock_team_orchestrator.run_full_team_session.side_effect = slow_execution

    # Should raise TimeoutError
    with pytest.raises(asyncio.TimeoutError):
        await sub_team_launcher.launch_sub_team(
            parent_agent_id=parent_agent_id,
            sub_team_config=sub_team_config,
            task=task,
            session_id=session_id,
            sub_agent_ids=sub_agent_ids,
        )


# ---------------------------------------------------------------------------
# Test 5: Result Aggregation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_launch_sub_team_aggregates_results(
    sub_team_launcher, mock_team_orchestrator, sub_team_config
):
    """Test SubTeamResult aggregates individual MissionResults."""
    parent_agent_id = "analyst_001"
    task = "Analyze codebase"
    session_id = str(uuid4())
    sub_agent_ids = ["context_analyst", "logic_analyst"]

    # Mock team session with mission results
    mock_team_orchestrator.run_full_team_session.return_value = TeamSessionResult(
        session_id=session_id,
        task=task,
        final_result="Analysis complete",
        success=True,
        missions={
            "context_analyst": {
                "status": "completed",
                "result": "Context analyzed",
                "duration": 15.0,
            },
            "logic_analyst": {
                "status": "completed",
                "result": "Logic analyzed",
                "duration": 20.0,
            },
        },
        chat_history_length=5,
        total_duration_seconds=35.0,
        phases_completed=["formation", "missions", "synthesis"],
    )

    result = await sub_team_launcher.launch_sub_team(
        parent_agent_id=parent_agent_id,
        sub_team_config=sub_team_config,
        task=task,
        session_id=session_id,
        sub_agent_ids=sub_agent_ids,
    )

    # Verify aggregation
    assert result.sub_agent_count == 2
    assert result.success_count == 2
    assert result.success_rate == 1.0
    assert result.total_duration == 35.0
    assert len(result.sub_agent_results) == 2


# ---------------------------------------------------------------------------
# Test 6: Partial Failure Handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_launch_sub_team_handles_partial_failures(
    sub_team_launcher, mock_team_orchestrator, sub_team_config
):
    """Test graceful handling when some sub-agents fail."""
    parent_agent_id = "researcher_001"
    task = "Research multiple topics"
    session_id = str(uuid4())
    sub_agent_ids = ["topic_a", "topic_b", "topic_c"]

    # Mock team session with partial failures
    mock_team_orchestrator.run_full_team_session.return_value = TeamSessionResult(
        session_id=session_id,
        task=task,
        final_result="Partial research complete",
        success=True,  # Overall session succeeded
        missions={
            "topic_a": {"status": "completed", "result": "Success", "duration": 10.0},
            "topic_b": {"status": "failed", "result": "", "duration": 5.0},
            "topic_c": {"status": "completed", "result": "Success", "duration": 12.0},
        },
        chat_history_length=8,
        total_duration_seconds=27.0,
        phases_completed=["formation", "missions", "synthesis"],
    )

    result = await sub_team_launcher.launch_sub_team(
        parent_agent_id=parent_agent_id,
        sub_team_config=sub_team_config,
        task=task,
        session_id=session_id,
        sub_agent_ids=sub_agent_ids,
    )

    # Verify partial success tracking
    assert result.sub_agent_count == 3
    assert result.success_count == 2  # Only 2 succeeded
    assert result.success_rate == pytest.approx(0.666, rel=0.01)
    assert result.has_failures is True
    assert len(result.errors) > 0


# ---------------------------------------------------------------------------
# Test 7: Complete Failure Handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_launch_sub_team_handles_complete_failure(
    sub_team_launcher, mock_team_orchestrator, sub_team_config
):
    """Test handling when entire sub-team session fails."""
    parent_agent_id = "coder_001"
    task = "Write complex feature"
    session_id = str(uuid4())
    sub_agent_ids = ["architect", "writer"]

    # Mock complete failure
    mock_team_orchestrator.run_full_team_session.return_value = TeamSessionResult(
        session_id=session_id,
        task=task,
        final_result="",
        success=False,
        missions={},
        chat_history_length=2,
        total_duration_seconds=5.0,
        phases_completed=["formation"],
        error="Team formation failed",
    )

    result = await sub_team_launcher.launch_sub_team(
        parent_agent_id=parent_agent_id,
        sub_team_config=sub_team_config,
        task=task,
        session_id=session_id,
        sub_agent_ids=sub_agent_ids,
    )

    # Verify failure tracking
    assert result.sub_agent_count == 2
    assert result.success_count == 0
    assert result.success_rate == 0.0
    assert result.has_failures is True
    assert "Team formation failed" in result.errors


# ---------------------------------------------------------------------------
# Test 8: Session Metadata
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_launch_sub_team_tracks_metadata(
    sub_team_launcher, mock_team_orchestrator, sub_team_config
):
    """Test SubTeamResult includes metadata from team session."""
    parent_agent_id = "analyst_001"
    task = "Analyze system"
    session_id = str(uuid4())
    sub_agent_ids = ["sub_agent_1", "sub_agent_2"]

    mock_team_orchestrator.run_full_team_session.return_value = TeamSessionResult(
        session_id=session_id,
        task=task,
        final_result="Done",
        success=True,
        missions={
            "sub_agent_1": {"status": "completed", "result": "OK", "duration": 10.0},
            "sub_agent_2": {"status": "completed", "result": "OK", "duration": 10.0},
        },
        chat_history_length=3,
        total_duration_seconds=20.0,
        phases_completed=["formation", "missions", "synthesis"],
    )

    result = await sub_team_launcher.launch_sub_team(
        parent_agent_id=parent_agent_id,
        sub_team_config=sub_team_config,
        task=task,
        session_id=session_id,
        sub_agent_ids=sub_agent_ids,
    )

    # Verify metadata was captured in result
    assert result.metadata["session_id"] == session_id
    assert result.metadata["chat_history_length"] == 3
    assert result.metadata["phases_completed"] == ["formation", "missions", "synthesis"]


# ---------------------------------------------------------------------------
# Test 9: Agent ID Validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_launch_sub_team_validates_agent_count(
    sub_team_launcher, mock_team_orchestrator
):
    """Test validation of sub_agent_ids count against config."""
    parent_agent_id = "researcher_001"
    task = "Research topic"
    session_id = str(uuid4())

    # Config allows max 3 agents, but we provide 5
    config = SubTeamConfig(max_agents=3, min_agents=2)
    sub_agent_ids = ["agent_1", "agent_2", "agent_3", "agent_4", "agent_5"]

    # Should raise ValueError for too many agents
    with pytest.raises(ValueError, match="sub_agent_ids count"):
        await sub_team_launcher.launch_sub_team(
            parent_agent_id=parent_agent_id,
            sub_team_config=config,
            task=task,
            session_id=session_id,
            sub_agent_ids=sub_agent_ids,
        )


# ---------------------------------------------------------------------------
# Test 10: Synthesis Extraction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_launch_sub_team_extracts_synthesis(
    sub_team_launcher, mock_team_orchestrator, sub_team_config
):
    """Test synthesis field is extracted from TeamSessionResult."""
    parent_agent_id = "analyst_001"
    task = "Analyze patterns"
    session_id = str(uuid4())
    sub_agent_ids = ["sub_1", "sub_2"]

    synthesis_text = "Combined analysis shows pattern X and Y"

    mock_team_orchestrator.run_full_team_session.return_value = TeamSessionResult(
        session_id=session_id,
        task=task,
        final_result=synthesis_text,
        success=True,
        missions={
            "sub_1": {"status": "completed", "result": "Pattern X", "duration": 10.0},
            "sub_2": {"status": "completed", "result": "Pattern Y", "duration": 12.0},
        },
        chat_history_length=6,
        total_duration_seconds=22.0,
        phases_completed=["formation", "missions", "synthesis"],
    )

    result = await sub_team_launcher.launch_sub_team(
        parent_agent_id=parent_agent_id,
        sub_team_config=sub_team_config,
        task=task,
        session_id=session_id,
        sub_agent_ids=sub_agent_ids,
    )

    # Verify synthesis was extracted
    assert result.synthesis == synthesis_text
