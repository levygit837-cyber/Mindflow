"""Tests for Feature Flags V2 System."""

from __future__ import annotations

import pytest

from mindflow_backend.runtime.feature_flags_v2 import (
    ABExperiment,
    ABVariant,
    FeatureFlagStatus,
    FeatureFlagV2,
    FeatureFlagsV2,
)


class TestFeatureFlagV2:
    """Tests for FeatureFlagV2."""

    def test_status_disabled(self) -> None:
        flag = FeatureFlagV2(name="TEST", enabled=False)
        assert flag.get_status() == FeatureFlagStatus.DISABLED

    def test_status_enabled(self) -> None:
        flag = FeatureFlagV2(name="TEST", enabled=True, rollout_percentage=100)
        assert flag.get_status() == FeatureFlagStatus.ENABLED

    def test_status_partial(self) -> None:
        flag = FeatureFlagV2(name="TEST", enabled=True, rollout_percentage=50)
        assert flag.get_status() == FeatureFlagStatus.PARTIAL


class TestFeatureFlagsV2:
    """Tests for FeatureFlagsV2."""

    def test_register_and_get(self) -> None:
        ff = FeatureFlagsV2()
        flag = FeatureFlagV2(name="TEST", enabled=True)
        ff.register(flag)
        assert ff.get_flag("TEST") is not None

    def test_is_enabled_disabled(self) -> None:
        ff = FeatureFlagsV2()
        flag = FeatureFlagV2(name="TEST", enabled=False)
        ff.register(flag)
        assert not ff.is_enabled("TEST")

    def test_is_enabled_100_percent(self) -> None:
        ff = FeatureFlagsV2()
        flag = FeatureFlagV2(name="TEST", enabled=True, rollout_percentage=100)
        ff.register(flag)
        assert ff.is_enabled("TEST", session_id="user-123")

    def test_is_enabled_0_percent(self) -> None:
        ff = FeatureFlagsV2()
        flag = FeatureFlagV2(name="TEST", enabled=True, rollout_percentage=0)
        ff.register(flag)
        assert not ff.is_enabled("TEST", session_id="user-123")

    def test_override(self) -> None:
        ff = FeatureFlagsV2()
        flag = FeatureFlagV2(name="TEST", enabled=False)
        ff.register(flag)
        assert not ff.is_enabled("TEST")
        ff.override("TEST", True)
        assert ff.is_enabled("TEST")

    def test_clear_override(self) -> None:
        ff = FeatureFlagsV2()
        flag = FeatureFlagV2(name="TEST", enabled=False)
        ff.register(flag)
        ff.override("TEST", True)
        assert ff.is_enabled("TEST")
        ff.clear_override("TEST")
        assert not ff.is_enabled("TEST")

    def test_target_users(self) -> None:
        ff = FeatureFlagsV2()
        flag = FeatureFlagV2(
            name="TEST",
            enabled=True,
            rollout_percentage=0,
            target_users=["user-123"],
        )
        ff.register(flag)
        assert ff.is_enabled("TEST", user_id="user-123")
        assert not ff.is_enabled("TEST", user_id="user-456")

    def test_dependencies(self) -> None:
        ff = FeatureFlagsV2()
        base = FeatureFlagV2(name="BASE", enabled=False)
        dependent = FeatureFlagV2(
            name="DEPENDENT",
            enabled=True,
            dependencies=["BASE"],
        )
        ff.register(base)
        ff.register(dependent)
        assert not ff.is_enabled("DEPENDENT")

        # Enable base
        ff.override("BASE", True)
        assert ff.is_enabled("DEPENDENT")

    def test_ab_testing(self) -> None:
        ff = FeatureFlagsV2()
        experiment = ABExperiment(
            name="test_exp",
            variants=[
                ABVariant("control", weight=50, config={"algo": "old"}),
                ABVariant("treatment", weight=50, config={"algo": "new"}),
            ],
        )
        flag = FeatureFlagV2(
            name="SEARCH_ALGO",
            enabled=True,
            rollout_percentage=100,
            experiment=experiment,
        )
        ff.register(flag)

        variant = ff.get_variant("SEARCH_ALGO", session_id="user-123")
        assert variant is not None
        assert variant.name in ("control", "treatment")

    def test_ab_variant_consistency(self) -> None:
        ff = FeatureFlagsV2()
        experiment = ABExperiment(
            name="test_exp",
            variants=[
                ABVariant("control", weight=50),
                ABVariant("treatment", weight=50),
            ],
        )
        flag = FeatureFlagV2(
            name="SEARCH_ALGO",
            enabled=True,
            rollout_percentage=100,
            experiment=experiment,
        )
        ff.register(flag)

        # Same session should always get same variant
        variant1 = ff.get_variant("SEARCH_ALGO", session_id="user-123")
        variant2 = ff.get_variant("SEARCH_ALGO", session_id="user-123")
        assert variant1 is not None
        assert variant2 is not None
        assert variant1.name == variant2.name

    def test_get_all_flags(self) -> None:
        ff = FeatureFlagsV2()
        flag1 = FeatureFlagV2(name="FLAG1", enabled=True)
        flag2 = FeatureFlagV2(name="FLAG2", enabled=False)
        ff.register(flag1)
        ff.register(flag2)

        all_flags = ff.get_all_flags()
        assert "FLAG1" in all_flags
        assert "FLAG2" in all_flags

    def test_reset_all(self) -> None:
        ff = FeatureFlagsV2()
        flag = FeatureFlagV2(name="TEST", enabled=True)
        ff.register(flag)
        ff.override("TEST", False)
        ff.reset_all()
        assert ff.get_flag("TEST") is None