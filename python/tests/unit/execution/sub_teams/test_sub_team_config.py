"""
Unit tests for SubTeamConfig.

Tests validation, immutability, and predefined configurations.
"""

import pytest

from mindflow_backend.execution.sub_teams.sub_team_config import (
    ANALYST_SUB_TEAM_CONFIG,
    CODER_SUB_TEAM_CONFIG,
    RESEARCHER_SUB_TEAM_CONFIG,
    SubTeamConfig,
)


class TestSubTeamConfigValidation:
    """Test SubTeamConfig validation rules."""

    def test_valid_config_creation(self):
        """Valid configuration should be created successfully."""
        config = SubTeamConfig(
            model_tier="tier-2",
            max_agents=3,
            timeout_seconds=45.0,
            skip_discussion=True,
            min_agents=2,
        )

        assert config.model_tier == "tier-2"
        assert config.max_agents == 3
        assert config.timeout_seconds == 45.0
        assert config.skip_discussion is True
        assert config.min_agents == 2

    def test_default_values(self):
        """Default values should be applied correctly."""
        config = SubTeamConfig()

        assert config.model_tier == "tier-2"
        assert config.max_agents == 3
        assert config.timeout_seconds == 60.0
        assert config.skip_discussion is True
        assert config.min_agents == 2

    def test_max_agents_too_low(self):
        """max_agents < 2 should raise ValueError."""
        with pytest.raises(ValueError, match="max_agents must be between 2 and 5"):
            SubTeamConfig(max_agents=1)

    def test_max_agents_too_high(self):
        """max_agents > 5 should raise ValueError."""
        with pytest.raises(ValueError, match="max_agents must be between 2 and 5"):
            SubTeamConfig(max_agents=6)

    def test_min_agents_too_low(self):
        """min_agents < 2 should raise ValueError."""
        with pytest.raises(ValueError, match="min_agents must be at least 2"):
            SubTeamConfig(min_agents=1)

    def test_min_agents_exceeds_max_agents(self):
        """min_agents > max_agents should raise ValueError."""
        with pytest.raises(
            ValueError, match="min_agents .* cannot exceed max_agents"
        ):
            SubTeamConfig(min_agents=4, max_agents=3)

    def test_timeout_too_high(self):
        """timeout_seconds > 60.0 should raise ValueError."""
        with pytest.raises(
            ValueError, match="timeout_seconds must be ≤ 60.0 for sub-teams"
        ):
            SubTeamConfig(timeout_seconds=61.0)

    def test_timeout_zero(self):
        """timeout_seconds = 0 should raise ValueError."""
        with pytest.raises(ValueError, match="timeout_seconds must be positive"):
            SubTeamConfig(timeout_seconds=0.0)

    def test_timeout_negative(self):
        """Negative timeout_seconds should raise ValueError."""
        with pytest.raises(ValueError, match="timeout_seconds must be positive"):
            SubTeamConfig(timeout_seconds=-10.0)

    def test_invalid_model_tier(self):
        """Invalid model_tier should raise ValueError."""
        with pytest.raises(
            ValueError, match="model_tier must be 'tier-2', 'fast', or 'cheap'"
        ):
            SubTeamConfig(model_tier="tier-1")

    def test_valid_model_tier_fast(self):
        """model_tier='fast' should be accepted."""
        config = SubTeamConfig(model_tier="fast")
        assert config.model_tier == "fast"

    def test_valid_model_tier_cheap(self):
        """model_tier='cheap' should be accepted."""
        config = SubTeamConfig(model_tier="cheap")
        assert config.model_tier == "cheap"


class TestSubTeamConfigImmutability:
    """Test that SubTeamConfig is immutable (frozen=True)."""

    def test_cannot_modify_model_tier(self):
        """Attempting to modify model_tier should raise FrozenInstanceError."""
        config = SubTeamConfig()

        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            config.model_tier = "fast"  # type: ignore

    def test_cannot_modify_max_agents(self):
        """Attempting to modify max_agents should raise FrozenInstanceError."""
        config = SubTeamConfig()

        with pytest.raises(Exception):
            config.max_agents = 5  # type: ignore

    def test_cannot_modify_timeout(self):
        """Attempting to modify timeout_seconds should raise FrozenInstanceError."""
        config = SubTeamConfig()

        with pytest.raises(Exception):
            config.timeout_seconds = 30.0  # type: ignore


class TestPredefinedConfigurations:
    """Test predefined SubTeamConfig instances."""

    def test_researcher_config(self):
        """RESEARCHER_SUB_TEAM_CONFIG should have correct values."""
        config = RESEARCHER_SUB_TEAM_CONFIG

        assert config.model_tier == "tier-2"
        assert config.max_agents == 3
        assert config.timeout_seconds == 45.0
        assert config.skip_discussion is True
        assert config.min_agents == 2

    def test_analyst_config(self):
        """ANALYST_SUB_TEAM_CONFIG should have correct values."""
        config = ANALYST_SUB_TEAM_CONFIG

        assert config.model_tier == "tier-2"
        assert config.max_agents == 3
        assert config.timeout_seconds == 50.0
        assert config.skip_discussion is True
        assert config.min_agents == 2

    def test_coder_config(self):
        """CODER_SUB_TEAM_CONFIG should have correct values."""
        config = CODER_SUB_TEAM_CONFIG

        assert config.model_tier == "tier-2"
        assert config.max_agents == 3
        assert config.timeout_seconds == 60.0
        assert config.skip_discussion is True
        assert config.min_agents == 3  # Architect + Writer + Reviewer

    def test_predefined_configs_are_immutable(self):
        """Predefined configs should be immutable."""
        with pytest.raises(Exception):
            RESEARCHER_SUB_TEAM_CONFIG.max_agents = 5  # type: ignore


class TestSubTeamConfigEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_max_agents_boundary_min(self):
        """max_agents=2 (minimum) should be valid."""
        config = SubTeamConfig(max_agents=2)
        assert config.max_agents == 2

    def test_max_agents_boundary_max(self):
        """max_agents=5 (maximum) should be valid."""
        config = SubTeamConfig(max_agents=5)
        assert config.max_agents == 5

    def test_timeout_boundary_max(self):
        """timeout_seconds=60.0 (maximum) should be valid."""
        config = SubTeamConfig(timeout_seconds=60.0)
        assert config.timeout_seconds == 60.0

    def test_timeout_very_small(self):
        """Very small positive timeout should be valid."""
        config = SubTeamConfig(timeout_seconds=0.1)
        assert config.timeout_seconds == 0.1

    def test_min_equals_max_agents(self):
        """min_agents == max_agents should be valid."""
        config = SubTeamConfig(min_agents=3, max_agents=3)
        assert config.min_agents == 3
        assert config.max_agents == 3
