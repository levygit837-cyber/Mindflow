"""Unit tests for BrowserMetricsCollector."""

from __future__ import annotations

import asyncio

import pytest

from mindflow_backend.services.browser import BrowserMetricsCollector


class TestBrowserMetricsCollector:
    """Test suite for BrowserMetricsCollector."""
    
    @pytest.fixture
    def metrics_collector(self):
        """Create a metrics collector instance for testing."""
        return BrowserMetricsCollector()
    
    @pytest.mark.asyncio
    async def test_record_request_success(self, metrics_collector):
        """Test recording a successful request."""
        await metrics_collector.record_request(
            instance_id="browser-1",
            duration=0.5,
            success=True,
        )
        
        assert "browser-1" in metrics_collector._request_metrics
        assert len(metrics_collector._request_metrics["browser-1"]) == 1
        assert metrics_collector._request_metrics["browser-1"][0].success is True
    
    @pytest.mark.asyncio
    async def test_record_request_failure(self, metrics_collector):
        """Test recording a failed request."""
        await metrics_collector.record_request(
            instance_id="browser-1",
            duration=0.3,
            success=False,
            error_type="TimeoutError",
        )
        
        assert metrics_collector._request_metrics["browser-1"][0].success is False
        assert metrics_collector._request_metrics["browser-1"][0].error_type == "TimeoutError"
    
    @pytest.mark.asyncio
    async def test_update_resource_metrics(self, metrics_collector):
        """Test updating resource metrics."""
        await metrics_collector.update_resource_metrics(
            instance_id="browser-1",
            cpu_usage_percent=50.5,
            memory_usage_mb=256.0,
        )
        
        assert "browser-1" in metrics_collector._resource_metrics
        assert metrics_collector._resource_metrics["browser-1"]["cpu_usage_percent"] == 50.5
        assert metrics_collector._resource_metrics["browser-1"]["memory_usage_mb"] == 256.0
    
    @pytest.mark.asyncio
    async def test_increment_snapshot_count(self, metrics_collector):
        """Test incrementing snapshot count."""
        initial_count = metrics_collector._snapshot_count
        
        await metrics_collector.increment_snapshot_count()
        
        assert metrics_collector._snapshot_count == initial_count + 1
    
    @pytest.mark.asyncio
    async def test_collect_metrics(self, metrics_collector):
        """Test collecting all metrics."""
        await metrics_collector.record_request("browser-1", 0.5, True)
        await metrics_collector.record_request("browser-1", 0.3, True)
        await metrics_collector.record_request("browser-1", 0.7, False)
        await metrics_collector.update_resource_metrics("browser-1", 50.0, 256.0)
        
        metrics = await metrics_collector.collect_metrics()
        
        assert metrics is not None
        assert "total_requests" in metrics
        assert metrics["total_requests"] == 3
        assert metrics["successful_requests"] == 2
        assert metrics["failed_requests"] == 1
        assert metrics["error_rate"] == pytest.approx(1/3)
    
    @pytest.mark.asyncio
    async def test_get_prometheus_metrics(self, metrics_collector):
        """Test getting Prometheus-formatted metrics."""
        await metrics_collector.record_request("browser-1", 0.5, True)
        await metrics_collector.update_resource_metrics("browser-1", 50.0, 256.0)
        
        prometheus_text = await metrics_collector.get_prometheus_metrics()
        
        assert prometheus_text is not None
        assert "lightpanda_browser_instances_total" in prometheus_text
        assert "lightpanda_browser_requests_total" in prometheus_text
        assert "lightpanda_browser_cpu_usage_percent" in prometheus_text
        assert "lightpanda_browser_memory_usage_mb" in prometheus_text
    
    @pytest.mark.asyncio
    async def test_get_instance_metrics(self, metrics_collector):
        """Test getting metrics for a specific instance."""
        await metrics_collector.record_request("browser-1", 0.5, True)
        await metrics_collector.update_resource_metrics("browser-1", 50.0, 256.0)
        
        metrics = await metrics_collector.get_instance_metrics("browser-1")
        
        assert metrics is not None
        assert metrics["instance_id"] == "browser-1"
        assert metrics["total_requests"] == 1
        assert metrics["successful_requests"] == 1
        assert metrics["cpu_usage_percent"] == 50.0
        assert metrics["memory_usage_mb"] == 256.0
    
    @pytest.mark.asyncio
    async def test_get_instance_metrics_nonexistent(self, metrics_collector):
        """Test getting metrics for non-existent instance."""
        metrics = await metrics_collector.get_instance_metrics("non-existent")
        
        assert metrics == {}
    
    @pytest.mark.asyncio
    async def test_reset_metrics(self, metrics_collector):
        """Test resetting all metrics."""
        await metrics_collector.record_request("browser-1", 0.5, True)
        await metrics_collector.update_resource_metrics("browser-1", 50.0, 256.0)
        
        await metrics_collector.reset_metrics()
        
        assert len(metrics_collector._request_metrics) == 0
        assert len(metrics_collector._resource_metrics) == 0
        assert metrics_collector._snapshot_count == 0
    
    @pytest.mark.asyncio
    async def test_request_metrics_limit(self, metrics_collector):
        """Test that request metrics are limited to last 1000."""
        # Record more than 1000 requests
        for i in range(1005):
            await metrics_collector.record_request("browser-1", 0.1, True)
        
        assert len(metrics_collector._request_metrics["browser-1"]) == 1000
    
    @pytest.mark.asyncio
    async def test_duration_percentiles(self, metrics_collector):
        """Test calculation of duration percentiles."""
        # Record requests with varying durations
        durations = [0.1, 0.2, 0.3, 0.4, 0.5, 1.0, 2.0, 5.0]
        for duration in durations:
            await metrics_collector.record_request("browser-1", duration, True)
        
        metrics = await metrics_collector.collect_metrics()
        
        assert "p50_duration_seconds" in metrics
        assert "p95_duration_seconds" in metrics
        assert "p99_duration_seconds" in metrics
        assert metrics["p50_duration_seconds"] > 0
        assert metrics["p95_duration_seconds"] >= metrics["p50_duration_seconds"]
