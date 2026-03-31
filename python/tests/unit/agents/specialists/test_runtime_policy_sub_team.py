"""
Unit tests for AgentRuntimePolicy sub-team capability fields.

Tests the new fields added for sub-team support without triggering
circular imports in the existing codebase.
"""

import pytest

from mindflow_backend.execution.sub_teams.sub_team_config import (
    ANALYST_SUB_TEAM_CONFIG,
    CODER_SUB_TEAM_CONFIG,
    RESEARCHER_SUB_TEAM_CONFIG,
    SubTeamConfig,
)
from mindflow_backend.schemas.orchestration.orchestrator import AgentType


class TestAgentRuntimePolicySubTeamFields:
    """Test sub-team capability fields in AgentRuntimePolicy dataclass."""

    def test_default_values_for_sub_team_fields(self):
        """New sub-team fields should have correct default values."""
        # Import inside test to avoid circular import at module level
        from mindflow_backend.agents.specialists.runtime_policy import (
            AgentRuntimePolicy,
        )

        policy = AgentRuntimePolicy(
            agent_role=AgentType.ANALYST,
            system_prompt="Test prompt",
        )

        assert policy.supports_sub_team is False
        assert policy.sub_team_config is None

    def test_create_policy_with_sub_team_support(self):
        """Should be able to create policy with supports_sub_team=True."""
        from mindflow_backend.agents.specialists.runtime_policy import (
            AgentRuntimePolicy,
        )

        config = SubTeamConfig(max_agents=3, timeout_seconds=45.0)

        policy = AgentRuntimePolicy(
            agent_role=AgentType.RESEARCHER,
            system_prompt="Researcher prompt",
            supports_sub_team=True,
            sub_team_config=config,
        )

        assert policy.supports_sub_team is True
        assert policy.sub_team_config is config
        assert policy.sub_team_config.max_agents == 3

    def test_create_policy_with_predefined_config(self):
        """Should work with predefined SubTeamConfig instances."""
        from mindflow_backend.agents.specialists.runtime_policy import (
            AgentRuntimePolicy,
        )

        policy = AgentRuntimePolicy(
            agent_role=AgentType.RESEARCHER,
            system_prompt="Researcher prompt",
            supports_sub_team=True,
            sub_team_config=RESEARCHER_SUB_TEAM_CONFIG,
        )

        assert policy.supports_sub_team is True
        assert policy.sub_team_config is RESEARCHER_SUB_TEAM_CONFIG
        assert policy.sub_team_config.timeout_seconds == 45.0

    def test_supports_sub_team_without_config(self):
        """supports_sub_team=True without config is allowed."""
        from mindflow_backend.agents.specialists.runtime_policy import (
            AgentRuntimePolicy,
        )

        policy = AgentRuntimePolicy(
            agent_role=AgentType.ANALYST,
            system_prompt="Analyst prompt",
            supports_sub_team=True,
            sub_team_config=None,
        )

        assert policy.supports_sub_team is True
        assert policy.sub_team_config is None


class TestAgentRuntimePolicyImmutability:
    """Test that AgentRuntimePolicy remains immutable with new fields."""

    def test_cannot_modify_supports_sub_team(self):
        """Attempting to modify supports_sub_team should raise error."""
        from mindflow_backend.agents.specialists.runtime_policy import (
            AgentRuntimePolicy,
        )

        policy = AgentRuntimePolicy(
            agent_role=AgentType.ANALYST,
            system_prompt="Test prompt",
        )

        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            policy.supports_sub_team = True  # type: ignore

    def test_cannot_modify_sub_team_config(self):
        """Attempting to modify sub_team_config should raise error."""
        from mindflow_backend.agents.specialists.runtime_policy import (
            AgentRuntimePolicy,
        )

        policy = AgentRuntimePolicy(
            agent_role=AgentType.ANALYST,
            system_prompt="Test prompt",
        )

        with pytest.raises(Exception):
            policy.sub_team_config = SubTeamConfig()  # type: ignore


class TestSubTeamConfigCompatibility:
    """Test compatibility between AgentRuntimePolicy and SubTeamConfig."""

    def test_analyst_with_analyst_config(self):
        """Analyst policy should work with ANALYST_SUB_TEAM_CONFIG."""
        from mindflow_backend.agents.specialists.runtime_policy import (
            AgentRuntimePolicy,
        )

        policy = AgentRuntimePolicy(
            agent_role=AgentType.ANALYST,
            system_prompt="Analyst prompt",
            supports_sub_team=True,
            sub_team_config=ANALYST_SUB_TEAM_CONFIG,
        )

        assert policy.sub_team_config.timeout_seconds == 50.0
        assert policy.sub_team_config.max_agents == 3

    def test_researcher_with_researcher_config(self):
        """Researcher policy should work with RESEARCHER_SUB_TEAM_CONFIG."""
        from mindflow_backend.agents.specialists.runtime_policy import (
            AgentRuntimePolicy,
        )

        policy = AgentRuntimePolicy(
            agent_role=AgentType.RESEARCHER,
            system_prompt="Researcher prompt",
            supports_sub_team=True,
            sub_team_config=RESEARCHER_SUB_TEAM_CONFIG,
        )

        assert policy.sub_team_config.timeout_seconds == 45.0
        assert policy.sub_team_config.max_agents == 3

    def test_coder_with_coder_config(self):
        """Coder policy should work with CODER_SUB_TEAM_CONFIG."""
        from mindflow_backend.agents.specialists.runtime_policy import (
            AgentRuntimePolicy,
        )

        policy = AgentRuntimePolicy(
            agent_role=AgentType.CODER,
            system_prompt="Coder prompt",
            supports_sub_team=True,
            sub_team_config=CODER_SUB_TEAM_CONFIG,
        )

        assert policy.sub_team_config.timeout_seconds == 60.0
        assert policy.sub_team_config.min_agents == 3  # Architect + Writer + Reviewer


class TestAgentRuntimePolicyFields:
    """Test that all expected fields exist on AgentRuntimePolicy."""

    def test_has_supports_sub_team_field(self):
        """AgentRuntimePolicy should have supports_sub_team field."""
        from mindflow_backend.agents.specialists.runtime_policy import (
            AgentRuntimePolicy,
        )

        policy = AgentRuntimePolicy(
            agent_role=AgentType.ANALYST,
            system_prompt="Test",
        )

        assert hasattr(policy, "supports_sub_team")
        assert isinstance(policy.supports_sub_team, bool)

    def test_has_sub_team_config_field(self):
        """AgentRuntimePolicy should have sub_team_config field."""
        from mindflow_backend.agents.specialists.runtime_policy import (
            AgentRuntimePolicy,
        )

        policy = AgentRuntimePolicy(
            agent_role=AgentType.ANALYST,
            system_prompt="Test",
        )

        assert hasattr(policy, "sub_team_config")
