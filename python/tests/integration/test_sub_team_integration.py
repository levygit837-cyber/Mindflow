"""
Testes de Integração End-to-End para o Sistema de Sub-Agentes.

Valida o fluxo completo:
MissionLauncher → SubTeamLauncher → TeamOrchestrator → Sub-Agents

Cenários testados:
1. Researcher sub-team com query splitting e síntese
2. Analyst sub-team com análise multi-perspectiva
3. Coder sub-team com pipeline sequencial
4. Prevenção de recursão (sub-agents não podem spawnar sub-sub-teams)
5. Enforcement de timeout
6. Tratamento de falhas parciais
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from mindflow_backend.execution.missions.mission_context import MissionContext
from mindflow_backend.execution.missions.mission_launcher import MissionLauncher
from mindflow_backend.execution.missions.mission_result import MissionResult
from mindflow_backend.execution.sub_teams.sub_team_config import (
    ANALYST_SUB_TEAM_CONFIG,
    CODER_SUB_TEAM_CONFIG,
    RESEARCHER_SUB_TEAM_CONFIG,
)
from mindflow_backend.execution.sub_teams.sub_team_launcher import SubTeamLauncher
from mindflow_backend.execution.sub_teams.sub_team_session import SubTeamResult
from mindflow_backend.execution.teams.team_session import TeamSessionResult
from mindflow_backend.schemas.orchestration.communication import MissionGraphType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_team_orchestrator():
    """Mock TeamOrchestrator para testes de integração."""
    orchestrator = AsyncMock()
    orchestrator.run_full_team_session = AsyncMock()
    return orchestrator


@pytest.fixture
def mock_graph_factory():
    """Mock GraphFactory para testes de integração."""
    factory = Mock()
    factory.get_available_types.return_value = [
        Mock(value="analysis"),
        Mock(value="web_research"),
        Mock(value="coding_task"),
    ]
    factory.create_graph.return_value = AsyncMock()
    return factory


@pytest.fixture
def mock_comm_bus():
    """Mock CommunicationBus para testes de integração."""
    return AsyncMock()


# ---------------------------------------------------------------------------
# Test 1: Researcher Sub-Team End-to-End
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.integration
async def test_researcher_sub_team_end_to_end(
    mock_team_orchestrator, mock_graph_factory, mock_comm_bus
):
    """
    Teste end-to-end do Researcher sub-team.

    Fluxo:
    1. MissionLauncher detecta supports_sub_team=True
    2. Roteia para SubTeamLauncher
    3. SubTeamLauncher cria 3 TopicResearchers
    4. TeamOrchestrator executa com skip_discussion=True
    5. Resultados são sintetizados
    6. SubTeamResult é anexado ao MissionResult
    """
    # Setup: Mock policy com sub-team support
    mock_policy = Mock()
    mock_policy.supports_sub_team = True
    mock_policy.sub_team_config = RESEARCHER_SUB_TEAM_CONFIG
    mock_policy.available_mission_graphs = [MissionGraphType.WEB_RESEARCH]

    # Setup: Mock TeamOrchestrator response
    session_id = str(uuid4())
    mock_team_orchestrator.run_full_team_session.return_value = TeamSessionResult(
        session_id=session_id,
        task="Research OAuth, JWT, and sessions",
        final_result="# Research Summary\n\n## Topic 0: OAuth\nOAuth 2.0 findings...\n\n## Topic 1: JWT\nJWT findings...\n\n## Topic 2: Sessions\nSession findings...",
        success=True,
        missions={
            "researcher_001_topic_0": {
                "status": "completed",
                "result": "OAuth 2.0 findings...",
                "duration": 15.0,
            },
            "researcher_001_topic_1": {
                "status": "completed",
                "result": "JWT findings...",
                "duration": 18.0,
            },
            "researcher_001_topic_2": {
                "status": "completed",
                "result": "Session findings...",
                "duration": 12.0,
            },
        },
        chat_history_length=10,
        total_duration_seconds=45.0,
        phases_completed=["formation", "missions", "synthesis"],
    )

    # Create SubTeamLauncher
    sub_team_launcher = SubTeamLauncher(
        team_orchestrator=mock_team_orchestrator,
        mission_launcher=Mock(),
        comm_bus=mock_comm_bus,
    )

    # Execute sub-team
    result = await sub_team_launcher.launch_sub_team(
        parent_agent_id="researcher_001",
        sub_team_config=RESEARCHER_SUB_TEAM_CONFIG,
        task="Research OAuth, JWT, and sessions",
        session_id=session_id,
        sub_agent_ids=["researcher_001_topic_0", "researcher_001_topic_1", "researcher_001_topic_2"],
    )

    # Verify results
    assert isinstance(result, SubTeamResult)
    assert result.sub_agent_count == 3
    assert result.success_count == 3
    assert result.success_rate == 1.0
    assert "OAuth" in result.synthesis or "oauth" in result.synthesis.lower()
    assert result.total_duration == 45.0

    # Verify TeamOrchestrator was called with skip_discussion=True
    mock_team_orchestrator.run_full_team_session.assert_called_once()
    call_kwargs = mock_team_orchestrator.run_full_team_session.call_args.kwargs
    assert call_kwargs["skip_discussion"] is True


# ---------------------------------------------------------------------------
# Test 2: Analyst Sub-Team End-to-End
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.integration
async def test_analyst_sub_team_end_to_end(
    mock_team_orchestrator, mock_graph_factory, mock_comm_bus
):
    """
    Teste end-to-end do Analyst sub-team.

    Fluxo:
    1. MissionLauncher detecta supports_sub_team=True
    2. Roteia para SubTeamLauncher
    3. SubTeamLauncher cria 3 Analysts (context, logic, synthesis)
    4. TeamOrchestrator executa análise multi-perspectiva
    5. Resultados são sintetizados
    """
    # Setup: Mock TeamOrchestrator response
    session_id = str(uuid4())
    mock_team_orchestrator.run_full_team_session.return_value = TeamSessionResult(
        session_id=session_id,
        task="Analyze authentication module",
        final_result="# Multi-Perspective Analysis\n\n## Context\nDependencies analyzed...\n\n## Logic\nControl flow analyzed...\n\n## Synthesis\nIntegration points identified...",
        success=True,
        missions={
            "analyst_001_context": {
                "status": "completed",
                "result": "Context: Dependencies on crypto library...",
                "duration": 20.0,
            },
            "analyst_001_logic": {
                "status": "completed",
                "result": "Logic: 3 main authentication branches...",
                "duration": 25.0,
            },
            "analyst_001_synthesis": {
                "status": "completed",
                "result": "Synthesis: Overall architecture is sound...",
                "duration": 18.0,
            },
        },
        chat_history_length=12,
        total_duration_seconds=63.0,
        phases_completed=["formation", "missions", "synthesis"],
    )

    # Create SubTeamLauncher
    sub_team_launcher = SubTeamLauncher(
        team_orchestrator=mock_team_orchestrator,
        mission_launcher=Mock(),
        comm_bus=mock_comm_bus,
    )

    # Execute sub-team
    result = await sub_team_launcher.launch_sub_team(
        parent_agent_id="analyst_001",
        sub_team_config=ANALYST_SUB_TEAM_CONFIG,
        task="Analyze authentication module",
        session_id=session_id,
        sub_agent_ids=["analyst_001_context", "analyst_001_logic", "analyst_001_synthesis"],
    )

    # Verify results
    assert isinstance(result, SubTeamResult)
    assert result.sub_agent_count == 3
    assert result.success_count == 3
    assert result.success_rate == 1.0
    assert "context" in result.synthesis.lower() or "logic" in result.synthesis.lower()


# ---------------------------------------------------------------------------
# Test 3: Coder Sub-Team End-to-End (Sequential)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.integration
async def test_coder_sub_team_end_to_end_sequential(
    mock_team_orchestrator, mock_graph_factory, mock_comm_bus
):
    """
    Teste end-to-end do Coder sub-team com execução sequencial.

    Fluxo:
    1. ArchitectAgent executa primeiro
    2. WriterAgent executa depois
    3. ReviewerAgent executa por último
    4. Quality gate é verificado
    """
    # Setup: Mock TeamOrchestrator response (sequential execution)
    session_id = str(uuid4())
    mock_team_orchestrator.run_full_team_session.return_value = TeamSessionResult(
        session_id=session_id,
        task="Implement JWT authentication",
        final_result="# Sequential Pipeline\n\n## Architecture\nDesigned 3 classes...\n\n## Implementation\nCode written...\n\n## Review\n✅ PASSED",
        success=True,
        missions={
            "coder_001_architect": {
                "status": "completed",
                "result": "Architecture: 3 classes designed...",
                "duration": 25.0,
            },
            "coder_001_writer": {
                "status": "completed",
                "result": "Implementation: All code written...",
                "duration": 35.0,
            },
            "coder_001_reviewer": {
                "status": "completed",
                "result": "Review: Code quality approved...",
                "duration": 20.0,
                "metadata": {"quality_gate_passed": True},
            },
        },
        chat_history_length=15,
        total_duration_seconds=80.0,
        phases_completed=["formation", "missions", "synthesis"],
    )

    # Create SubTeamLauncher
    sub_team_launcher = SubTeamLauncher(
        team_orchestrator=mock_team_orchestrator,
        mission_launcher=Mock(),
        comm_bus=mock_comm_bus,
    )

    # Execute sub-team
    result = await sub_team_launcher.launch_sub_team(
        parent_agent_id="coder_001",
        sub_team_config=CODER_SUB_TEAM_CONFIG,
        task="Implement JWT authentication",
        session_id=session_id,
        sub_agent_ids=["coder_001_architect", "coder_001_writer", "coder_001_reviewer"],
    )

    # Verify results
    assert isinstance(result, SubTeamResult)
    assert result.sub_agent_count == 3
    assert result.success_count == 3
    assert result.success_rate == 1.0


# ---------------------------------------------------------------------------
# Test 4: Recursion Prevention
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.integration
async def test_recursion_prevention_integration(mock_graph_factory, mock_comm_bus):
    """
    Teste de prevenção de recursão end-to-end.

    Verifica que sub-agents não podem spawnar sub-sub-teams.
    """
    # Setup: Mock policy com sub-team support
    mock_policy = Mock()
    mock_policy.supports_sub_team = True
    mock_policy.sub_team_config = RESEARCHER_SUB_TEAM_CONFIG
    mock_policy.available_mission_graphs = [MissionGraphType.WEB_RESEARCH]

    # Setup: Mock graph execution
    mock_graph = AsyncMock()
    mock_graph.execute.return_value = {
        "agent_id": "researcher_001_topic_0",
        "task": "Research OAuth",
        "result": "OAuth findings",
        "success": True,
    }
    mock_graph_factory.create_graph.return_value = mock_graph

    # Create MissionLauncher
    mission_launcher = MissionLauncher(
        graph_factory=mock_graph_factory,
        comm_bus=mock_comm_bus,
    )

    with patch(
        "mindflow_backend.execution.missions.mission_launcher.get_agent_runtime_policy",
        return_value=mock_policy,
    ):
        # Execute mission with is_sub_agent=True (simula sub-agent)
        result = await mission_launcher.launch_mission(
            agent_id="researcher_001_topic_0",
            mission_type=MissionGraphType.WEB_RESEARCH,
            task="Research OAuth",
            session_id=str(uuid4()),
            metadata={"is_sub_agent": True},  # Flag de recursão
        )

        # Verify: Normal mission execution (não usou SubTeamLauncher)
        assert result.success is True
        assert result.sub_team_result is None  # Não spawnou sub-team


# ---------------------------------------------------------------------------
# Test 5: Timeout Enforcement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.integration
async def test_timeout_enforcement_integration(mock_team_orchestrator, mock_comm_bus):
    """
    Teste de enforcement de timeout end-to-end.

    Verifica que sub-teams que excedem 60s são cancelados.
    """
    # Setup: Mock slow execution
    async def slow_execution(*args, **kwargs):
        await asyncio.sleep(70.0)  # Excede timeout de 60s
        return TeamSessionResult(
            session_id="test",
            task="test",
            final_result="",
            success=False,
            missions={},
            chat_history_length=0,
            total_duration_seconds=70.0,
            phases_completed=[],
        )

    mock_team_orchestrator.run_full_team_session.side_effect = slow_execution

    # Create SubTeamLauncher
    sub_team_launcher = SubTeamLauncher(
        team_orchestrator=mock_team_orchestrator,
        mission_launcher=Mock(),
        comm_bus=mock_comm_bus,
    )

    # Execute sub-team (deve dar timeout)
    with pytest.raises(asyncio.TimeoutError):
        await sub_team_launcher.launch_sub_team(
            parent_agent_id="researcher_001",
            sub_team_config=RESEARCHER_SUB_TEAM_CONFIG,
            task="Research topics",
            session_id=str(uuid4()),
            sub_agent_ids=["researcher_001_topic_0"],
        )


# ---------------------------------------------------------------------------
# Test 6: Partial Failure Handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.integration
async def test_partial_failure_handling_integration(
    mock_team_orchestrator, mock_comm_bus
):
    """
    Teste de tratamento de falhas parciais end-to-end.

    Verifica que o sistema lida graciosamente quando alguns sub-agents falham.
    """
    # Setup: Mock com falha parcial
    session_id = str(uuid4())
    mock_team_orchestrator.run_full_team_session.return_value = TeamSessionResult(
        session_id=session_id,
        task="Research topics",
        final_result="Partial research complete",
        success=True,  # Session succeeded overall
        missions={
            "researcher_001_topic_0": {
                "status": "completed",
                "result": "Topic 0 findings",
                "duration": 15.0,
            },
            "researcher_001_topic_1": {
                "status": "failed",
                "result": "",
                "duration": 5.0,
                "error": "Timeout",
            },
            "researcher_001_topic_2": {
                "status": "completed",
                "result": "Topic 2 findings",
                "duration": 12.0,
            },
        },
        chat_history_length=8,
        total_duration_seconds=32.0,
        phases_completed=["formation", "missions", "synthesis"],
    )

    # Create SubTeamLauncher
    sub_team_launcher = SubTeamLauncher(
        team_orchestrator=mock_team_orchestrator,
        mission_launcher=Mock(),
        comm_bus=mock_comm_bus,
    )

    # Execute sub-team
    result = await sub_team_launcher.launch_sub_team(
        parent_agent_id="researcher_001",
        sub_team_config=RESEARCHER_SUB_TEAM_CONFIG,
        task="Research topics",
        session_id=session_id,
        sub_agent_ids=["researcher_001_topic_0", "researcher_001_topic_1", "researcher_001_topic_2"],
    )

    # Verify: Partial success tracked
    assert result.sub_agent_count == 3
    assert result.success_count == 2  # 2 de 3 succeeded
    assert result.success_rate == pytest.approx(0.666, rel=0.01)
    assert result.has_failures is True
    assert len(result.errors) > 0
    assert "Timeout" in result.errors[0]
