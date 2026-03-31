"""
Unit tests for MissionContext sub-agent fields.

Tests the new fields added for sub-agent support:
- is_sub_agent: bool
- parent_agent_id: str | None
- sub_team_config: SubTeamConfig | None
"""

import pytest

from mindflow_backend.execution.missions.mission_context import MissionContext
from mindflow_backend.execution.sub_teams.sub_team_config import (
    RESEARCHER_SUB_TEAM_CONFIG,
    SubTeamConfig,
)
from mindflow_backend.schemas.orchestration.communication import MissionGraphType


class TestMissionContextSubAgentFields:
    """Test sub-agent related fields in MissionContext."""

    def test_default_values_for_sub_agent_fields(self):
        """New sub-agent fields should have correct default values."""
        context = MissionContext(
            agent_id="agent-123",
            mission_type=MissionGraphType.ANALYSIS,
            task="Analyze code",
            session_id="session-456",
        )

        assert context.is_sub_agent is False
        assert context.parent_agent_id is None
        assert context.sub_team_config is None

    def test_create_sub_agent_context(self):
        """Should be able to create context with is_sub_agent=True."""
        context = MissionContext(
            agent_id="sub-agent-123",
            mission_type=MissionGraphType.WEB_RESEARCH,
            task="Research topic A",
            session_id="session-456",
            is_sub_agent=True,
            parent_agent_id="parent-agent-789",
        )

        assert context.is_sub_agent is True
        assert context.parent_agent_id == "parent-agent-789"
        assert context.sub_team_config is None

    def test_create_context_with_sub_team_config(self):
        """Should be able to create context with SubTeamConfig."""
        config = SubTeamConfig(
            model_tier="tier-2", max_agents=3, timeout_seconds=45.0
        )

        context = MissionContext(
            agent_id="agent-123",
            mission_type=MissionGraphType.WEB_RESEARCH,
            task="Research with sub-team",
            session_id="session-456",
            sub_team_config=config,
        )

        assert context.sub_team_config is config
        assert context.sub_team_config.max_agents == 3
        assert context.sub_team_config.timeout_seconds == 45.0

    def test_create_context_with_predefined_config(self):
        """Should work with predefined SubTeamConfig instances."""
        context = MissionContext(
            agent_id="researcher-123",
            mission_type=MissionGraphType.WEB_RESEARCH,
            task="Research with predefined config",
            session_id="session-456",
            sub_team_config=RESEARCHER_SUB_TEAM_CONFIG,
        )

        assert context.sub_team_config is RESEARCHER_SUB_TEAM_CONFIG
        assert context.sub_team_config.timeout_seconds == 45.0

    def test_parent_agent_id_without_is_sub_agent(self):
        """parent_agent_id can be set even if is_sub_agent=False (no validation)."""
        context = MissionContext(
            agent_id="agent-123",
            mission_type=MissionGraphType.ANALYSIS,
            task="Analyze",
            session_id="session-456",
            is_sub_agent=False,
            parent_agent_id="parent-789",  # Allowed but semantically odd
        )

        assert context.is_sub_agent is False
        assert context.parent_agent_id == "parent-789"


class TestMissionContextToGraphState:
    """Test that to_graph_state() includes sub-agent fields."""

    def test_to_graph_state_includes_sub_agent_fields(self):
        """to_graph_state() should include is_sub_agent and parent_agent_id."""
        context = MissionContext(
            agent_id="sub-agent-123",
            mission_type=MissionGraphType.WEB_RESEARCH,
            task="Research topic",
            session_id="session-456",
            is_sub_agent=True,
            parent_agent_id="parent-789",
        )

        state = context.to_graph_state()

        assert state["is_sub_agent"] is True
        assert state["parent_agent_id"] == "parent-789"

    def test_to_graph_state_default_sub_agent_fields(self):
        """to_graph_state() should include default values for sub-agent fields."""
        context = MissionContext(
            agent_id="agent-123",
            mission_type=MissionGraphType.ANALYSIS,
            task="Analyze",
            session_id="session-456",
        )

        state = context.to_graph_state()

        assert state["is_sub_agent"] is False
        assert state["parent_agent_id"] is None

    def test_to_graph_state_with_sub_team_config(self):
        """to_graph_state() should include sub_team_config in metadata."""
        config = SubTeamConfig(max_agents=4, timeout_seconds=50.0)

        context = MissionContext(
            agent_id="agent-123",
            mission_type=MissionGraphType.WEB_RESEARCH,
            task="Research",
            session_id="session-456",
            sub_team_config=config,
        )

        state = context.to_graph_state()

        # sub_team_config should be in metadata
        assert "sub_team_config" in state["metadata"]
        assert state["metadata"]["sub_team_config"] is config


class TestMissionContextEdgeCases:
    """Test edge cases for sub-agent context."""

    def test_sub_agent_without_parent_id(self):
        """is_sub_agent=True without parent_agent_id is allowed (no validation)."""
        context = MissionContext(
            agent_id="sub-agent-123",
            mission_type=MissionGraphType.WEB_RESEARCH,
            task="Research",
            session_id="session-456",
            is_sub_agent=True,
            parent_agent_id=None,  # Semantically odd but allowed
        )

        assert context.is_sub_agent is True
        assert context.parent_agent_id is None

    def test_multiple_contexts_with_same_parent(self):
        """Multiple sub-agent contexts can share the same parent_agent_id."""
        parent_id = "parent-789"

        context1 = MissionContext(
            agent_id="sub-1",
            mission_type=MissionGraphType.WEB_RESEARCH,
            task="Task 1",
            session_id="session-456",
            is_sub_agent=True,
            parent_agent_id=parent_id,
        )

        context2 = MissionContext(
            agent_id="sub-2",
            mission_type=MissionGraphType.WEB_RESEARCH,
            task="Task 2",
            session_id="session-456",
            is_sub_agent=True,
            parent_agent_id=parent_id,
        )

        assert context1.parent_agent_id == context2.parent_agent_id == parent_id
        assert context1.agent_id != context2.agent_id
