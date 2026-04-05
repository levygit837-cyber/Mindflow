"""Unit tests for orchestration fallback components."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mindflow_backend.infra.resilience.orchestration_fallback_metrics import (
    OrchestrationFallbackMetrics,
    OrchestrationFallbackMetricsCollector,
)
from mindflow_backend.infra.resilience.orchestration_fallback_registry import (
    OrchestrationFallbackRegistry,
)
from mindflow_backend.infra.resilience.orchestration_fallback import (
    ComponentStatus,
    FallbackContext,
    FallbackResult,
    OrchestrationFallbackManager,
    get_orchestration_fallback_manager,
)


class TestOrchestrationFallbackManager:
    """Tests for OrchestrationFallbackManager."""

    def test_singleton_instance(self):
        """Test that get_orchestration_fallback_manager returns singleton."""
        manager1 = get_orchestration_fallback_manager()
        manager2 = get_orchestration_fallback_manager()
        assert manager1 is manager2

    def test_register_fallback_handler(self):
        """Test registering a fallback handler."""
        manager = OrchestrationFallbackManager()

        async def dummy_handler(ctx: FallbackContext):
            return {"fallback": True}

        manager.register_fallback_handler("test_component", dummy_handler)
        assert "test_component" in manager.list_components()

    def test_get_component_status_default(self):
        """Test getting component status (default healthy)."""
        manager = OrchestrationFallbackManager()
        status = manager.get_component_status("nonexistent")
        assert status == ComponentStatus.HEALTHY

    async def test_execute_with_fallback_success(self):
        """Test successful primary execution without fallback."""
        manager = OrchestrationFallbackManager()

        async def primary_func():
            return {"result": "success"}

        result = await manager.execute_with_fallback(
            component="test",
            primary_func=primary_func,
        )

        assert result.success is True
        assert result.fallback_used is False
        assert result.result == {"result": "success"}

    async def test_execute_with_fallback_trigger(self):
        """Test fallback triggered when primary fails."""
        manager = OrchestrationFallbackManager()

        async def primary_func():
            raise ValueError("Primary failed")

        async def fallback_func(ctx: FallbackContext):
            return {"result": "fallback"}

        result = await manager.execute_with_fallback(
            component="test",
            primary_func=primary_func,
            fallback_func=fallback_func,
        )

        assert result.success is True
        assert result.fallback_used is True
        assert result.result == {"result": "fallback"}

    async def test_execute_with_fallback_no_handler(self):
        """Test execution when no fallback handler is available."""
        manager = OrchestrationFallbackManager()

        async def primary_func():
            raise ValueError("Primary failed")

        result = await manager.execute_with_fallback(
            component="test",
            primary_func=primary_func,
        )

        assert result.success is False
        assert result.fallback_used is False
        assert result.error is not None

    async def test_execute_with_fallback_handler_fails(self):
        """Test when both primary and fallback fail."""
        manager = OrchestrationFallbackManager()

        async def primary_func():
            raise ValueError("Primary failed")

        async def fallback_func(ctx: FallbackContext):
            raise RuntimeError("Fallback failed")

        result = await manager.execute_with_fallback(
            component="test",
            primary_func=primary_func,
            fallback_func=fallback_func,
        )

        assert result.success is False
        assert result.fallback_used is True
        assert "Primary" in result.error
        assert "Fallback" in result.error

    def test_reset_component_status(self):
        """Test resetting component status."""
        manager = OrchestrationFallbackManager()
        manager._component_status["test"] = ComponentStatus.FALLBACK_ACTIVE
        manager.reset_component_status("test")
        assert manager.get_component_status("test") == ComponentStatus.HEALTHY


class TestOrchestrationFallbackRegistry:
    """Tests for OrchestrationFallbackRegistry."""

    def test_register_handler(self):
        """Test registering a handler."""
        registry = OrchestrationFallbackRegistry()

        async def dummy_handler():
            return {"result": True}

        registry.register("test_component", dummy_handler, priority=10)
        assert "test_component" in registry.list_components()

    def test_get_handler(self):
        """Test getting a handler."""
        registry = OrchestrationFallbackRegistry()

        async def dummy_handler():
            return {"result": True}

        registry.register("test_component", dummy_handler)
        handler = registry.get_handler("test_component")
        assert handler is not None

    def test_get_handler_priority(self):
        """Test that highest priority handler is returned."""
        registry = OrchestrationFallbackRegistry()

        async def low_priority():
            return {"priority": 1}

        async def high_priority():
            return {"priority": 10}

        registry.register("test", low_priority, priority=1)
        registry.register("test", high_priority, priority=10)

        handler = registry.get_handler("test")
        assert handler == high_priority

    def test_get_all_handlers(self):
        """Test getting all handlers sorted by priority."""
        registry = OrchestrationFallbackRegistry()

        async def handler1():
            return {"handler": 1}

        async def handler2():
            return {"handler": 2}

        registry.register("test", handler1, priority=5)
        registry.register("test", handler2, priority=10)

        handlers = registry.get_all_handlers("test")
        assert len(handlers) == 2
        assert handlers[0][0] == 10  # Highest priority first
        assert handlers[1][0] == 5

    def test_unregister_specific_handler(self):
        """Test unregistering a specific handler."""
        registry = OrchestrationFallbackRegistry()

        async def handler1():
            return {"handler": 1}

        async def handler2():
            return {"handler": 2}

        registry.register("test", handler1)
        registry.register("test", handler2)
        registry.unregister("test", handler1)

        handlers = registry.get_all_handlers("test")
        assert len(handlers) == 1

    def test_unregister_all_handlers(self):
        """Test unregistering all handlers for a component."""
        registry = OrchestrationFallbackRegistry()

        async def handler1():
            return {"handler": 1}

        async def handler2():
            return {"handler": 2}

        registry.register("test", handler1)
        registry.register("test", handler2)
        registry.unregister("test")

        assert "test" not in registry.list_components()

    def test_validate_handler_callable(self):
        """Test validating a callable handler."""
        registry = OrchestrationFallbackRegistry()

        async def valid_handler():
            return True

        assert registry.validate_handler(valid_handler) is True

    def test_validate_handler_non_callable(self):
        """Test validating a non-callable handler."""
        registry = OrchestrationFallbackRegistry()
        assert registry.validate_handler("not a function") is False


class TestOrchestrationFallbackMetricsCollector:
    """Tests for OrchestrationFallbackMetricsCollector."""

    def test_singleton_instance(self):
        """Test that get_orchestration_fallback_metrics_collector returns singleton."""
        collector1 = get_orchestration_fallback_metrics_collector()
        collector2 = get_orchestration_fallback_metrics_collector()
        assert collector1 is collector2

    def test_record_fallback_success(self):
        """Test recording a successful fallback."""
        collector = OrchestrationFallbackMetricsCollector()

        collector.record_fallback(
            component="test",
            success=True,
            fallback_used=True,
            latency=1.5,
        )

        metrics = collector.get_metrics("test")
        assert metrics.fallback_total == 1
        assert metrics.fallback_success == 1
        assert metrics.fallback_failure == 0

    def test_record_fallback_failure(self):
        """Test recording a failed fallback."""
        collector = OrchestrationFallbackMetricsCollector()

        collector.record_fallback(
            component="test",
            success=False,
            fallback_used=True,
            latency=1.5,
        )

        metrics = collector.get_metrics("test")
        assert metrics.fallback_total == 1
        assert metrics.fallback_success == 0
        assert metrics.fallback_failure == 1

    def test_fallback_rate_calculation(self):
        """Test fallback rate calculation."""
        collector = OrchestrationFallbackMetricsCollector()

        # Record 5 events, 3 with fallback
        for i in range(5):
            collector.record_fallback(
                component="test",
                success=True,
                fallback_used=(i < 3),
                latency=1.0,
            )

        rate = collector._calculate_fallback_rate("test")
        assert rate == 0.6  # 3/5

    def test_is_fallback_rate_high(self):
        """Test checking if fallback rate is high."""
        collector = OrchestrationFallbackMetricsCollector(alert_threshold=0.2)

        # Record 10 events, 8 with fallback (80% rate)
        for i in range(10):
            collector.record_fallback(
                component="test",
                success=True,
                fallback_used=(i < 8),
                latency=1.0,
            )

        assert collector.is_fallback_rate_high("test") is True

    def test_get_all_metrics(self):
        """Test getting metrics for all components."""
        collector = OrchestrationFallbackMetricsCollector()

        collector.record_fallback(
            component="component1",
            success=True,
            fallback_used=True,
            latency=1.0,
        )
        collector.record_fallback(
            component="component2",
            success=True,
            fallback_used=True,
            latency=1.0,
        )

        all_metrics = collector.get_all_metrics()
        assert len(all_metrics) == 2
        assert "component1" in all_metrics
        assert "component2" in all_metrics

    def test_get_overall_fallback_rate(self):
        """Test calculating overall fallback rate."""
        collector = OrchestrationFallbackMetricsCollector()

        # Component 1: 5 events, 2 fallbacks
        for i in range(5):
            collector.record_fallback(
                component="comp1",
                success=True,
                fallback_used=(i < 2),
                latency=1.0,
            )

        # Component 2: 10 events, 3 fallbacks
        for i in range(10):
            collector.record_fallback(
                component="comp2",
                success=True,
                fallback_used=(i < 3),
                latency=1.0,
            )

        overall_rate = collector.get_overall_fallback_rate()
        assert overall_rate == 5 / 15  # 5 fallbacks out of 15 total

    def test_get_alerting_components(self):
        """Test getting components with high fallback rate."""
        collector = OrchestrationFallbackMetricsCollector(alert_threshold=0.2)

        # High rate component
        for i in range(10):
            collector.record_fallback(
                component="high",
                success=True,
                fallback_used=True,
                latency=1.0,
            )

        # Low rate component
        for i in range(10):
            collector.record_fallback(
                component="low",
                success=True,
                fallback_used=(i < 1),
                latency=1.0,
            )

        alerting = collector.get_alerting_components()
        assert "high" in alerting
        assert "low" not in alerting

    def test_reset_metrics_component(self):
        """Test resetting metrics for a specific component."""
        collector = OrchestrationFallbackMetricsCollector()

        collector.record_fallback(
            component="test",
            success=True,
            fallback_used=True,
            latency=1.0,
        )

        collector.reset_metrics("test")
        metrics = collector.get_metrics("test")
        assert metrics.fallback_total == 0

    def test_reset_metrics_all(self):
        """Test resetting all metrics."""
        collector = OrchestrationFallbackMetricsCollector()

        collector.record_fallback(
            component="comp1",
            success=True,
            fallback_used=True,
            latency=1.0,
        )
        collector.record_fallback(
            component="comp2",
            success=True,
            fallback_used=True,
            latency=1.0,
        )

        collector.reset_metrics()
        all_metrics = collector.get_all_metrics()
        assert len(all_metrics) == 0

    def test_latency_percentiles(self):
        """Test latency percentile calculations."""
        collector = OrchestrationFallbackMetricsCollector()

        # Record latencies: 1.0, 2.0, 3.0, 4.0, 5.0
        for latency in [1.0, 2.0, 3.0, 4.0, 5.0]:
            collector.record_fallback(
                component="test",
                success=True,
                fallback_used=True,
                latency=latency,
            )

        metrics = collector.get_metrics("test")
        assert metrics.avg_latency == 3.0
        assert metrics.p50_latency == 3.0
        assert metrics.p95_latency == 5.0


class TestOrchestrationFallbackMetrics:
    """Tests for OrchestrationFallbackMetrics dataclass."""

    def test_fallback_success_rate(self):
        """Test fallback success rate calculation."""
        metrics = OrchestrationFallbackMetrics(component="test")
        metrics.fallback_total = 10
        metrics.fallback_success = 8
        metrics.fallback_failure = 2

        assert metrics.fallback_success_rate == 0.8

    def test_fallback_success_rate_no_fallbacks(self):
        """Test fallback success rate when no fallbacks."""
        metrics = OrchestrationFallbackMetrics(component="test")
        assert metrics.fallback_success_rate == 1.0

    def test_avg_latency(self):
        """Test average latency calculation."""
        from collections import deque

        metrics = OrchestrationFallbackMetrics(component="test")
        metrics.latency_samples = deque([1.0, 2.0, 3.0], maxlen=1000)

        assert metrics.avg_latency == 2.0

    def test_avg_latency_no_samples(self):
        """Test average latency when no samples."""
        metrics = OrchestrationFallbackMetrics(component="test")
        assert metrics.avg_latency == 0.0
