"""Tests for Model Fallback System."""

from __future__ import annotations

import pytest

from mindflow_backend.infra.error_handling.model_fallback import (
    FallbackChain,
    ModelFallbackExhaustedError,
    ModelFallbackManager,
    ModelHealth,
    ModelStatus,
    calculate_backoff_delay,
)


class TestModelHealth:
    """Tests for ModelHealth."""

    def test_initial_state(self) -> None:
        health = ModelHealth(model_name="gpt-4")
        assert health.status == ModelStatus.HEALTHY
        assert health.failure_count == 0
        assert health.consecutive_failures == 0

    def test_record_failure_increments_counters(self) -> None:
        health = ModelHealth(model_name="gpt-4")
        health.record_failure()
        assert health.failure_count == 1
        assert health.consecutive_failures == 1
        assert health.status == ModelStatus.DEGRADED

    def test_multiple_failures_become_unavailable(self) -> None:
        health = ModelHealth(model_name="gpt-4", failure_threshold=3)
        health.record_failure()
        health.record_failure()
        assert health.status == ModelStatus.DEGRADED
        health.record_failure()
        assert health.status == ModelStatus.UNAVAILABLE

    def test_success_resets_consecutive_failures(self) -> None:
        health = ModelHealth(model_name="gpt-4")
        health.record_failure()
        health.record_failure()
        health.record_success()
        assert health.consecutive_failures == 0
        assert health.status == ModelStatus.HEALTHY


class TestFallbackChain:
    """Tests for FallbackChain."""

    def test_available_models(self) -> None:
        chain = FallbackChain(
            primary="gpt-4",
            fallbacks=["gpt-3.5-turbo", "claude-3-haiku"],
        )
        available = chain.get_available_models()
        assert available == ["gpt-4", "gpt-3.5-turbo", "claude-3-haiku"]

    def test_unavailable_model_excluded(self) -> None:
        chain = FallbackChain(
            primary="gpt-4",
            fallbacks=["gpt-3.5-turbo"],
        )
        chain.health["gpt-4"].status = ModelStatus.UNAVAILABLE
        available = chain.get_available_models()
        assert "gpt-4" not in available
        assert "gpt-3.5-turbo" in available


class TestCalculateBackoffDelay:
    """Tests for backoff delay calculation."""

    def test_exponential_increase(self) -> None:
        delay_0 = calculate_backoff_delay(0, base_delay=1.0, jitter=False)
        delay_1 = calculate_backoff_delay(1, base_delay=1.0, jitter=False)
        delay_2 = calculate_backoff_delay(2, base_delay=1.0, jitter=False)
        assert delay_0 == 1.0
        assert delay_1 == 2.0
        assert delay_2 == 4.0

    def test_max_delay_cap(self) -> None:
        delay = calculate_backoff_delay(10, base_delay=1.0, max_delay=30.0, jitter=False)
        assert delay == 30.0

    def test_jitter_adds_variation(self) -> None:
        delays = [
            calculate_backoff_delay(1, base_delay=10.0, jitter=True)
            for _ in range(100)
        ]
        # With jitter, delays should vary
        assert len(set(delays)) > 1


class TestModelFallbackManager:
    """Tests for ModelFallbackManager."""

    @pytest.mark.asyncio
    async def test_execute_with_primary_success(self) -> None:
        manager = ModelFallbackManager()
        chain = FallbackChain(
            primary="gpt-4",
            fallbacks=["gpt-3.5-turbo"],
        )
        manager.register_chain("default", chain)

        async def executor(model_name: str) -> str:
            return f"result from {model_name}"

        result = await manager.execute_with_fallback(
            "default", executor
        )
        assert result == "result from gpt-4"

    @pytest.mark.asyncio
    async def test_fallback_on_failure(self) -> None:
        manager = ModelFallbackManager()
        chain = FallbackChain(
            primary="gpt-4",
            fallbacks=["gpt-3.5-turbo"],
        )
        manager.register_chain("default", chain)

        call_count = 0

        async def executor(model_name: str) -> str:
            nonlocal call_count
            call_count += 1
            if model_name == "gpt-4":
                raise Exception("Server overloaded")
            return f"result from {model_name}"

        result = await manager.execute_with_fallback("default", executor)
        assert result == "result from gpt-3.5-turbo"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_exhausted_raises_error(self) -> None:
        manager = ModelFallbackManager()
        chain = FallbackChain(
            primary="gpt-4",
            fallbacks=["gpt-3.5-turbo"],
        )
        manager.register_chain("default", chain)

        async def executor(model_name: str) -> str:
            raise TimeoutError("Request timed out")

        with pytest.raises(ModelFallbackExhaustedError):
            await manager.execute_with_fallback("default", executor)

    def test_reset_health(self) -> None:
        manager = ModelFallbackManager()
        chain = FallbackChain(primary="gpt-4", fallbacks=[])
        manager.register_chain("default", chain)

        chain.health["gpt-4"].record_failure()
        manager.reset_health("gpt-4")

        health = manager.get_model_health("gpt-4")
        assert health is not None
        assert health.status == ModelStatus.HEALTHY