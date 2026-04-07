"""Browser metrics collector for Prometheus monitoring.

Collects and exports browser-related metrics in Prometheus format
for monitoring and alerting.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


@dataclass
class RequestMetrics:
    """Metrics for individual requests."""
    
    timestamp: float
    duration: float
    success: bool
    error_type: str | None = None


class BrowserMetricsCollector:
    """Collects and exports browser metrics for Prometheus monitoring.
    
    This service provides:
    - Request tracking (count, duration, success rate)
    - Resource usage monitoring (CPU, memory)
    - Browser instance metrics
    - Snapshot metrics
    - Prometheus-formatted metric export
    - Automatic cleanup to prevent memory leaks
    
    Metrics exposed:
    - lightpanda_browser_instances_total
    - lightpanda_browser_active_instances
    - lightpanda_browser_cpu_usage_percent
    - lightpanda_browser_memory_usage_mb
    - lightpanda_browser_requests_total
    - lightpanda_browser_request_duration_seconds
    - lightpanda_browser_error_rate
    - lightpanda_browser_snapshot_count
    - lightpanda_browser_uptime_seconds
    """
    
    def __init__(
        self,
        max_metrics_per_instance: int = 1000,
        metrics_retention_seconds: int = 3600,
        instance_data_retention_seconds: int = 7200,
    ):
        """Initialize the metrics collector.
        
        Args:
            max_metrics_per_instance: Max request metrics to keep per instance
            metrics_retention_seconds: How long to keep request metrics (default 1 hour)
            instance_data_retention_seconds: How long to keep instance data (default 2 hours)
        """
        # Request metrics per instance (using deque for automatic size limit)
        self._request_metrics: dict[str, deque[RequestMetrics]] = defaultdict(
            lambda: deque(maxlen=max_metrics_per_instance)
        )
        
        # Current resource metrics per instance
        self._resource_metrics: dict[str, dict[str, float]] = defaultdict(dict)
        self._resource_metrics_timestamps: dict[str, float] = {}
        
        # Snapshot metrics
        self._snapshot_count = 0
        
        # Start time for uptime calculation
        self._start_time = time.time()
        
        # Retention settings
        self._metrics_retention_seconds = metrics_retention_seconds
        self._instance_data_retention_seconds = instance_data_retention_seconds
        
        # Lock for concurrent access
        self._lock = None  # Will be asyncio.Lock in async context
        
        # Last cleanup timestamp
        self._last_cleanup = time.time()
    
    async def record_request(
        self,
        instance_id: str,
        duration: float,
        success: bool,
        error_type: str | None = None,
    ) -> None:
        """Record a browser request metric.
        
        Args:
            instance_id: Browser instance ID
            duration: Request duration in seconds
            success: Whether the request succeeded
            error_type: Type of error if failed
        """
        metric = RequestMetrics(
            timestamp=time.time(),
            duration=duration,
            success=success,
            error_type=error_type,
        )
        
        # Add to deque (automatically limits size)
        self._request_metrics[instance_id].append(metric)
        
        # Trigger periodic cleanup
        await self._maybe_cleanup()
        
        _logger.debug(
            "request_metric_recorded",
            instance_id=instance_id,
            duration=duration,
            success=success,
        )
    
    async def _maybe_cleanup(self) -> None:
        """Perform cleanup if enough time has passed since last cleanup."""
        now = time.time()
        if now - self._last_cleanup > 300:  # Cleanup every 5 minutes
            await self.cleanup_old_data()
            self._last_cleanup = now
    
    async def cleanup_old_data(self) -> int:
        """Clean up old metrics and instance data to prevent memory leaks.
        
        Returns:
            int: Number of items cleaned up
        """
        now = time.time()
        cleanup_count = 0
        
        # Clean up old request metrics
        metrics_cutoff = now - self._metrics_retention_seconds
        for instance_id, metrics_deque in list(self._request_metrics.items()):
            # Filter out old metrics
            original_count = len(metrics_deque)
            self._request_metrics[instance_id] = deque(
                (m for m in metrics_deque if m.timestamp > metrics_cutoff),
                maxlen=metrics_deque.maxlen,
            )
            cleanup_count += original_count - len(self._request_metrics[instance_id])
            
            # Remove instance if no metrics left
            if len(self._request_metrics[instance_id]) == 0:
                del self._request_metrics[instance_id]
        
        # Clean up old resource metrics
        resource_cutoff = now - self._instance_data_retention_seconds
        for instance_id, timestamp in list(self._resource_metrics_timestamps.items()):
            if timestamp < resource_cutoff:
                del self._resource_metrics[instance_id]
                del self._resource_metrics_timestamps[instance_id]
                cleanup_count += 1
        
        if cleanup_count > 0:
            _logger.info(
                "metrics_cleanup_completed",
                items_cleaned=cleanup_count,
            )
        
        return cleanup_count
    
    async def update_resource_metrics(
        self,
        instance_id: str,
        cpu_usage_percent: float,
        memory_usage_mb: float,
    ) -> None:
        """Update resource metrics for a browser instance.
        
        Args:
            instance_id: Browser instance ID
            cpu_usage_percent: CPU usage percentage
            memory_usage_mb: Memory usage in MB
        """
        self._resource_metrics[instance_id] = {
            "cpu_usage_percent": cpu_usage_percent,
            "memory_usage_mb": memory_usage_mb,
            "timestamp": time.time(),
        }
        self._resource_metrics_timestamps[instance_id] = time.time()
    
    async def increment_snapshot_count(self, delta: int = 1) -> None:
        """Increment the snapshot count.
        
        Args:
            delta: Amount to increment (default 1)
        """
        self._snapshot_count += delta
    
    async def collect_metrics(self) -> dict[str, Any]:
        """Collect all current metrics.
        
        Returns:
            dict[str, Any]: Collected metrics
        """
        uptime = time.time() - self._start_time
        
        # Aggregate request metrics
        total_requests = 0
        successful_requests = 0
        failed_requests = 0
        total_duration = 0.0
        
        durations = []
        
        for instance_id, metrics in self._request_metrics.items():
            for metric in metrics:
                total_requests += 1
                total_duration += metric.duration
                durations.append(metric.duration)
                
                if metric.success:
                    successful_requests += 1
                else:
                    failed_requests += 1
        
        # Calculate aggregates
        avg_duration = total_duration / total_requests if total_requests > 0 else 0.0
        error_rate = failed_requests / total_requests if total_requests > 0 else 0.0
        
        # Calculate percentiles
        sorted_durations = sorted(durations)
        n = len(sorted_durations)
        p50 = sorted_durations[n // 2] if n > 0 else 0.0
        p95 = sorted_durations[int(n * 0.95)] if n > 0 else 0.0
        p99 = sorted_durations[int(n * 0.99)] if n > 0 else 0.0
        
        # Aggregate resource metrics
        total_cpu = 0.0
        total_memory = 0.0
        active_instances = len(self._resource_metrics)
        
        for metrics in self._resource_metrics.values():
            total_cpu += metrics.get("cpu_usage_percent", 0.0)
            total_memory += metrics.get("memory_usage_mb", 0.0)
        
        avg_cpu = total_cpu / active_instances if active_instances > 0 else 0.0
        avg_memory = total_memory / active_instances if active_instances > 0 else 0.0
        
        return {
            "uptime_seconds": uptime,
            "total_instances": len(self._request_metrics),
            "active_instances": active_instances,
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "error_rate": error_rate,
            "average_duration_seconds": avg_duration,
            "p50_duration_seconds": p50,
            "p95_duration_seconds": p95,
            "p99_duration_seconds": p99,
            "average_cpu_usage_percent": avg_cpu,
            "average_memory_usage_mb": avg_memory,
            "total_memory_usage_mb": total_memory,
            "snapshot_count": self._snapshot_count,
        }
    
    async def get_prometheus_metrics(self) -> str:
        """Get metrics in Prometheus text format.
        
        Returns:
            str: Prometheus-formatted metrics
        """
        metrics = await self.collect_metrics()
        lines = []
        
        # Browser instance metrics
        lines.append(f'lightpanda_browser_instances_total {metrics["total_instances"]}')
        lines.append(f'lightpanda_browser_active_instances {metrics["active_instances"]}')
        
        # Resource metrics
        lines.append(f'lightpanda_browser_cpu_usage_percent {metrics["average_cpu_usage_percent"]:.2f}')
        lines.append(f'lightpanda_browser_memory_usage_mb {metrics["average_memory_usage_mb"]:.2f}')
        lines.append(f'lightpanda_browser_total_memory_usage_mb {metrics["total_memory_usage_mb"]:.2f}')
        
        # Request metrics
        lines.append(f'lightpanda_browser_requests_total {metrics["total_requests"]}')
        lines.append(f'lightpanda_browser_successful_requests_total {metrics["successful_requests"]}')
        lines.append(f'lightpanda_browser_failed_requests_total {metrics["failed_requests"]}')
        lines.append(f'lightpanda_browser_error_rate {metrics["error_rate"]:.4f}')
        
        # Duration metrics
        lines.append(f'lightpanda_browser_request_duration_seconds {metrics["average_duration_seconds"]:.4f}')
        lines.append(f'lightpanda_browser_request_duration_seconds_p50 {metrics["p50_duration_seconds"]:.4f}')
        lines.append(f'lightpanda_browser_request_duration_seconds_p95 {metrics["p95_duration_seconds"]:.4f}')
        lines.append(f'lightpanda_browser_request_duration_seconds_p99 {metrics["p99_duration_seconds"]:.4f}')
        
        # Histogram buckets for duration
        duration_buckets = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
        all_durations = []
        for metrics in self._request_metrics.values():
            all_durations.extend([m.duration for m in metrics])
        
        for bucket in duration_buckets:
            count = sum(1 for d in all_durations if d <= bucket)
            lines.append(f'lightpanda_browser_request_duration_seconds_bucket{{le="{bucket}"}} {count}')
        
        lines.append(f'lightpanda_browser_request_duration_seconds_bucket{{le="+Inf"}} {len(all_durations)}')
        lines.append(f'lightpanda_browser_request_duration_seconds_count {len(all_durations)}')
        lines.append(f'lightpanda_browser_request_duration_seconds_sum {sum(all_durations):.4f}')
        
        # Snapshot metrics
        lines.append(f'lightpanda_browser_snapshot_count {metrics["snapshot_count"]}')
        
        # Uptime metric
        lines.append(f'lightpanda_browser_uptime_seconds {metrics["uptime_seconds"]:.2f}')
        
        return '\n'.join(lines) + '\n'
    
    async def get_instance_metrics(self, instance_id: str) -> dict[str, Any]:
        """Get metrics for a specific browser instance.
        
        Args:
            instance_id: Browser instance ID
            
        Returns:
            dict[str, Any]: Instance metrics
        """
        request_metrics = self._request_metrics.get(instance_id, [])
        resource_metrics = self._resource_metrics.get(instance_id, {})
        
        total_requests = len(request_metrics)
        successful_requests = sum(1 for m in request_metrics if m.success)
        failed_requests = total_requests - successful_requests
        
        total_duration = sum(m.duration for m in request_metrics)
        avg_duration = total_duration / total_requests if total_requests > 0 else 0.0
        
        return {
            "instance_id": instance_id,
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "error_rate": failed_requests / total_requests if total_requests > 0 else 0.0,
            "average_duration_seconds": avg_duration,
            "cpu_usage_percent": resource_metrics.get("cpu_usage_percent", 0.0),
            "memory_usage_mb": resource_metrics.get("memory_usage_mb", 0.0),
        }
    
    async def reset_metrics(self) -> None:
        """Reset all metrics (useful for testing)."""
        self._request_metrics.clear()
        self._resource_metrics.clear()
        self._snapshot_count = 0
        self._start_time = time.time()
        
        _logger.info("metrics_reset")
