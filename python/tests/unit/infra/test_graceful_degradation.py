"""Tests for Graceful Degradation System."""

from __future__ import annotations

import pytest

from mindflow_backend.infra.error_handling.graceful_degradation import (
    DegradationLevel,
    DegradationPolicy,
    GracefulDegradationManager,
)


class TestGracefulDegradationManager:
    """Tests for GracefulDegradationManager."""

    def test_register_policy(self) -> None:
        manager = GracefulDegradationManager()
        policy = DegradationPolicy(
            feature_name="test_feature",
            degradation_level=DegradationLevel.REDUCED,
            fallback_value="fallback",
        )
        manager.register_policy(policy)
        assert manager.get_policy("test_feature") is not None

    def test_is_degraded_initially_false(self) -> None:
        manager = GracefulDegradationManager()
        policy = DegradationPolicy(feature_name="test_feature")
        manager.register_policy(policy)
        assert not manager.is_degraded("test_feature")

    @pytest.mark.asyncio
    async def test_execute_success(self) -> None:
        manager = GracefulDegradationManager()
        policy = DegradationPolicy(
            feature_name="test_feature",
            fallback_value="fallback",
        )
        manager.register_policy(policy)

        async def primary_func() -> str:
            return "success"

        result = await manager.execute_with_degradation(
            "test_feature", primary_func
        )
        assert result == "success"
        assert not manager.is_degraded("test_feature")

    @pytest.mark.asyncio
    async def test_execute_failure_returns_fallback(self) -> None:
        manager = GracefulDegradationManager()
        policy = DegradationPolicy(
            feature_name="test_feature",
            fallback_value="fallback",
        )
        manager.register_policy(policy)

        async def primary_func() -> str:
            raise Exception("error")

        result = await manager.execute_with_degradation(
            "test_feature", primary_func
        )
        assert result == "fallback"
        assert manager.is_degraded("test_feature")

    @pytest.mark.asyncio
    async def test_auto_recovery(self) -> None:
        manager = GracefulDegradationManager()
        policy = DegradationPolicy(
            feature_name="test_feature",
            fallback_value="fallback",
            auto_recover=True,
            recovery_check_interval=0.0,  # Immediate recovery
        )
        manager.register_policy(policy)

        call_count = 0

        async def primary_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("error")
            return "recovered"

        # First call fails
        result = await manager.execute_with_degradation(
            "test_feature", primary_func
        )
        assert result == "fallback"
        assert manager.is_degraded("test_feature")

        # Second call should recover
        result = await manager.execute_with_degradation(
            "test_feature", primary_func
        )
        assert result == "recovered"
        assert not manager.is_degraded("test_feature")

    def test_recover_feature(self) -> None:
        manager = GracefulDegradationManager()
        policy = DegradationPolicy(
            feature_name="test_feature",
            fallback_value="fallback",
        )
        manager.register_policy(policy)

        # Simulate degradation
        manager._mark_degraded("test_feature")
        assert manager.is_degraded("test_feature")

        # Recover
        manager.recover_feature("test_feature")
        assert not manager.is_degraded("test_feature")

    def test_reset_all(self) -> None:
        manager = GracefulDegradationManager()
        policy1 = DegradationPolicy(feature_name="feature1", fallback_value="fb1")
        policy2 = DegradationPolicy(feature_name="feature2", fallback_value="fb2")
        manager.register_policy(policy1)
        manager.register_policy(policy2)

        manager._mark_degraded("feature1")
        manager._mark_degraded("feature2")
        assert manager.is_degraded("feature1")
        assert manager.is_degraded("feature2")

        manager.reset_all()
        assert not manager.is_degraded("feature1")
        assert not manager.is_degraded("feature2")