"""
Tests unitários para Fase 3A — Team Protocol.

Testa:
- MissionDAG (waves, ciclos, parsing de dependências)
- TeamSession (transições de fase, resultados)
- MissionNode/MissionEdge
"""

from __future__ import annotations

import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock

from mindflow_backend.execution.teams.mission_dag import (
    MissionDAG,
    MissionNode,
    MissionEdge,
)
from mindflow_backend.execution.teams.team_session import (
    TeamPhase,
    TeamSession,
    TeamSessionResult,
)
from mindflow_backend.schemas.orchestration.communication import MissionGraphType


# ─────────────────────────────────────────────
# MissionDAG Tests
# ─────────────────────────────────────────────

class TestMissionDAG:
    """Tests para MissionDAG."""

    def test_single_wave_no_dependencies(self):
        """Missões sem dependências devem estar na mesma wave."""
        dag = MissionDAG()
        dag.add_mission(MissionNode(
            agent_id="analyst",
            mission_type=MissionGraphType.ANALYSIS,
            task_description="Analyze",
        ))
        dag.add_mission(MissionNode(
            agent_id="coder",
            mission_type=MissionGraphType.CODING_TASK,
            task_description="Code",
        ))
        waves = dag.get_execution_waves()
        assert len(waves) == 1
        assert set(waves[0]) == {"analyst", "coder"}

    def test_two_waves_with_dependency(self):
        """Coder depende de analyst → analyst na wave 0, coder na wave 1."""
        dag = MissionDAG()
        dag.add_mission(MissionNode(
            agent_id="analyst",
            mission_type=MissionGraphType.ANALYSIS,
            task_description="Analyze",
        ))
        dag.add_mission(MissionNode(
            agent_id="coder",
            mission_type=MissionGraphType.CODING_TASK,
            task_description="Code",
            declared_dependencies=["analyst"],
        ))
        waves = dag.get_execution_waves()
        assert len(waves) == 2
        assert waves[0] == ["analyst"]
        assert waves[1] == ["coder"]

    def test_three_waves_chain(self):
        """Researcher → analyst → coder → 3 waves."""
        dag = MissionDAG()
        dag.add_mission(MissionNode(
            agent_id="researcher",
            mission_type=MissionGraphType.WEB_RESEARCH,
            task_description="Research",
        ))
        dag.add_mission(MissionNode(
            agent_id="analyst",
            mission_type=MissionGraphType.ANALYSIS,
            task_description="Analyze",
            declared_dependencies=["researcher"],
        ))
        dag.add_mission(MissionNode(
            agent_id="coder",
            mission_type=MissionGraphType.CODING_TASK,
            task_description="Code",
            declared_dependencies=["analyst"],
        ))
        waves = dag.get_execution_waves()
        assert len(waves) == 3
        assert waves[0] == ["researcher"]
        assert waves[1] == ["analyst"]
        assert waves[2] == ["coder"]

    def test_cycle_fallback(self):
        """Ciclo detectado → todos os agentes em uma única wave de fallback."""
        dag = MissionDAG()
        dag.add_mission(MissionNode(
            agent_id="a",
            mission_type=MissionGraphType.ANALYSIS,
            task_description="A",
            declared_dependencies=["b"],
        ))
        dag.add_mission(MissionNode(
            agent_id="b",
            mission_type=MissionGraphType.CODING_TASK,
            task_description="B",
            declared_dependencies=["a"],
        ))
        waves = dag.get_execution_waves()
        # Ciclo detectado → fallback: agentes em wave única
        assert len(waves) == 1
        assert set(waves[0]) == {"a", "b"}

    def test_is_valid_no_cycle(self):
        """DAG sem ciclo é válido."""
        dag = MissionDAG()
        dag.add_mission(MissionNode(
            agent_id="a", mission_type=MissionGraphType.ANALYSIS,
            task_description="A",
        ))
        dag.add_mission(MissionNode(
            agent_id="b", mission_type=MissionGraphType.CODING_TASK,
            task_description="B",
            declared_dependencies=["a"],
        ))
        is_valid, error = dag.is_valid()
        assert is_valid is True
        assert error == ""

    def test_is_valid_cycle_detected(self):
        """DAG com ciclo é inválido."""
        dag = MissionDAG()
        dag.add_mission(MissionNode(
            agent_id="a", mission_type=MissionGraphType.ANALYSIS,
            task_description="A",
            declared_dependencies=["b"],
        ))
        dag.add_mission(MissionNode(
            agent_id="b", mission_type=MissionGraphType.CODING_TASK,
            task_description="B",
            declared_dependencies=["a"],
        ))
        is_valid, error = dag.is_valid()
        assert is_valid is False
        assert "Cycle" in error

    def test_get_dependents(self):
        """get_dependents_of retorna quem depende do agente."""
        dag = MissionDAG()
        dag.add_mission(MissionNode(
            agent_id="analyst", mission_type=MissionGraphType.ANALYSIS,
            task_description="A",
        ))
        dag.add_mission(MissionNode(
            agent_id="coder", mission_type=MissionGraphType.CODING_TASK,
            task_description="C",
            declared_dependencies=["analyst"],
        ))
        dag.add_mission(MissionNode(
            agent_id="reviewer", mission_type=MissionGraphType.CODE_REVIEW,
            task_description="R",
            declared_dependencies=["analyst", "coder"],
        ))
        assert set(dag.get_dependents_of("analyst")) == {"coder", "reviewer"}
        assert set(dag.get_dependents_of("coder")) == {"reviewer"}
        assert dag.get_dependents_of("reviewer") == []

    def test_node_properties(self):
        """MissionNode armazena signal_type corretamente."""
        node = MissionNode(
            agent_id="analyst",
            mission_type=MissionGraphType.ANALYSIS,
            task_description="Investigate",
            signal_type="memory_annotation",
        )
        assert node.signal_type == "memory_annotation"
        assert node.declared_dependencies == []

    def test_edge_properties(self):
        """MissionEdge armazena from_agent e to_agent corretamente."""
        edge = MissionEdge(
            from_agent="a",
            to_agent="b",
            signal_type="p2p_ready_signal",
        )
        assert edge.from_agent == "a"
        assert edge.to_agent == "b"

    def test_dag_node_get(self):
        """get_node retorna o node correto."""
        dag = MissionDAG()
        node = MissionNode(
            agent_id="coder",
            mission_type=MissionGraphType.CODING_TASK,
            task_description="Build",
        )
        dag.add_mission(node)
        assert dag.get_node("coder") is node
        assert dag.get_node("nonexistent") is None


# ─────────────────────────────────────────────
# TeamSession Tests
# ─────────────────────────────────────────────

class TestTeamSession:
    """Tests para TeamSession."""

    def test_initial_phase_is_formation(self):
        """Sessão começa na fase formation."""
        session = TeamSession(
            task="test",
            agent_ids=["a", "b"],
        )
        assert session.phase == TeamPhase.FORMATION

    def test_advance_phase(self):
        """Avançar fases funciona corretamente."""
        session = TeamSession(task="test", agent_ids=["a"])
        session.advance_phase(TeamPhase.DISCUSSION)
        assert session.phase == TeamPhase.DISCUSSION
        session.advance_phase(TeamPhase.MISSIONS)
        assert session.phase == TeamPhase.MISSIONS

    def test_all_missions_complete(self):
        """all_missions_complete é True quando todos têm resultado."""
        session = TeamSession(task="t", agent_ids=["a", "b"])
        assert not session.all_missions_complete()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.result = "done"
        session.record_mission_result("a", mock_result)
        assert not session.all_missions_complete()
        session.record_mission_result("b", mock_result)
        assert session.all_missions_complete()

    def test_get_duration(self):
        """get_duration retorna segundos."""
        session = TeamSession(task="t", agent_ids=["a"])
        duration = session.get_duration()
        assert isinstance(duration, float)
        assert duration >= 0

    def test_mark_completed(self):
        """mark_completed seta completed_at e phase COMPLETED."""
        session = TeamSession(task="t", agent_ids=["a"])
        assert session.completed_at is None
        session.mark_completed()
        assert session.completed_at is not None
        assert session.phase == TeamPhase.COMPLETED

    def test_to_summary(self):
        """to_summary retorna dict com campos corretos."""
        session = TeamSession(task="my task", agent_ids=["a", "b"])
        summary = session.to_summary()
        assert "session_id" in summary
        assert summary["task"] == "my task"
        assert summary["agents"] == ["a", "b"]
        assert summary["missions_total"] == 2
        assert summary["missions_complete"] == 0
        assert summary["phase"] == "formation"


# ─────────────────────────────────────────────
# TeamSessionResult Tests
# ─────────────────────────────────────────────

class TestTeamSessionResult:
    """Tests para TeamSessionResult."""

    def test_result_to_summary(self):
        """to_summary retorna resumo legível do resultado."""
        result = TeamSessionResult(
            session_id="abc123",
            task="Test task",
            final_result="Success!",
            success=True,
            missions={
                "a": {"status": "completed"},
                "b": {"status": "completed"},
            },
            chat_history_length=10,
            total_duration_seconds=45.2,
            phases_completed=["formation", "discussion", "missions", "synthesis"],
        )
        summary = result.to_summary()
        assert summary["success"] is True
        assert summary["missions_successful"] == 2
        assert summary["missions_total"] == 2
        assert summary["duration_seconds"] == 45.2
        assert len(summary["phases_completed"]) == 4

    def test_failed_mission_count(self):
        """Missions com status != completed não contam como successful."""
        result = TeamSessionResult(
            session_id="abc123",
            task="Test task",
            final_result="Partial",
            success=True,
            missions={
                "a": {"status": "completed"},
                "b": {"status": "failed"},
            },
            chat_history_length=5,
            total_duration_seconds=30.0,
            phases_completed=["formation", "discussion", "missions", "synthesis"],
        )
        summary = result.to_summary()
        assert summary["missions_successful"] == 1
        assert summary["missions_total"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])