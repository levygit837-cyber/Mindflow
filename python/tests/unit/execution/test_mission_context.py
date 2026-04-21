"""Tests for MissionContext dataclass."""

from __future__ import annotations

from datetime import datetime

import pytest

from mindflow_backend.execution.missions.mission_context import MissionContext
from mindflow_backend.schemas.orchestration.communication import MissionGraphType


class TestCreateContextDefaults:
    """Verify that all fields have correct defaults."""

    def test_create_context_defaults(self):
        """All fields except required should have sensible defaults."""
        ctx = MissionContext(
            agent_id="test-agent",
            mission_type=MissionGraphType.ANALYSIS,
            task="Do something",
            session_id="sess-123",
        )

        assert ctx.agent_id == "test-agent"
        assert ctx.mission_type == MissionGraphType.ANALYSIS
        assert ctx.task == "Do something"
        assert ctx.session_id == "sess-123"
        assert ctx.comm_bus is None
        assert ctx.memory_scope == "universal"
        assert ctx.parent_mission_id is None
        assert len(ctx.mission_id) == 12, "mission_id should be 12 hex chars"
        assert ctx.max_duration_seconds == 300.0
        assert ctx.max_iterations == 500
        assert ctx.metadata == {}

    def test_mission_id_is_unique(self):
        """Each context should get a unique mission_id."""
        ctx1 = MissionContext(
            agent_id="a1", mission_type=MissionGraphType.ANALYSIS,
            task="t", session_id="s1",
        )
        ctx2 = MissionContext(
            agent_id="a2", mission_type=MissionGraphType.ANALYSIS,
            task="t", session_id="s2",
        )
        assert ctx1.mission_id != ctx2.mission_id

    def test_custom_values(self):
        """Verify that custom values override defaults."""
        ctx = MissionContext(
            agent_id="agent-1",
            mission_type=MissionGraphType.DEEP_INVESTIGATION,
            task="Investigate thoroughly",
            session_id="session-456",
            memory_scope="project",
            parent_mission_id="parent-1",
            mission_id="custom-id",
            max_duration_seconds=600.0,
            max_iterations=1000,
            metadata={"key": "value"},
        )

        assert ctx.memory_scope == "project"
        assert ctx.parent_mission_id == "parent-1"
        assert ctx.mission_id == "custom-id"
        assert ctx.max_duration_seconds == 600.0
        assert ctx.max_iterations == 1000
        assert ctx.metadata == {"key": "value"}


class TestToGraphState:
    """Verify to_graph_state() returns a compatible dict."""

    def test_to_graph_state(self):
        """Returned dict should have expected keys and values."""
        ctx = MissionContext(
            agent_id="analyst",
            mission_type=MissionGraphType.CODE_REVIEW,
            task="Review this code",
            session_id="s-001",
            mission_id="m-001",
            memory_scope="workspace",
            parent_mission_id="parent-x",
            max_iterations=200,
            metadata={"extra": True},
        )

        state = ctx.to_graph_state()

        # Required keys should be present
        assert state["agent_id"] == "analyst"
        assert state["mission_type"] == "code_review"
        assert state["task"] == "Review this code"
        assert state["session_id"] == "s-001"
        assert state["mission_id"] == "m-001"
        assert state["parent_mission_id"] == "parent-x"
        assert state["memory_scope"] == "workspace"
        assert state["max_iterations"] == 200
        assert state["metadata"] == {"extra": True}

        # Graph state boilerplate
        assert state["messages"] == []
        assert state["result"] == ""
        assert state["annotations"] == []
        assert state["errors"] == []
        assert state["iteration"] == 0

    def test_to_graph_state_metadata_is_copy(self):
        """Modifying metadata in returned state shouldn't affect original."""
        ctx = MissionContext(
            agent_id="x",
            mission_type=MissionGraphType.ANALYSIS,
            task="t",
            session_id="s",
            metadata={"original": 1},
        )

        state = ctx.to_graph_state()
        state["metadata"]["original"] = 999

        assert ctx.metadata["original"] == 1  # Unchanged