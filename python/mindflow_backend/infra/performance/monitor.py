"""Advanced performance monitoring system.

Provides comprehensive performance monitoring with
real-time metrics, anomaly detection, and alerting.
"""

from __future__ import annotations

import asyncio
import statistics
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

import psutil

from mindflow_backend.infra.cache.redis_client import get_redis_client
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class MetricType(Enum):
    """Metric types."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"
    METER = "meter"


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MetricPoint:
    """Single metric data point."""
    name: str
    value: float
    timestamp: datetime
    tags: dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
            "metric_type": self.metric_type.value,
        }


@dataclass
class MetricAggregation:
    """Aggregated metric statistics."""
    name: str
    count: int
    sum_value: float
    min_value: float
    max_value: float
    avg_value: float
    p50: float
    p90: float
    p95: float
    p99: float
    timestamp: datetime
    tags: dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "count": self.count,
            "sum_value": self.sum_value,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "avg_value": self.avg_value,
            "p50": self.p50,
            "p90": self.p90,
            "p95": self.p95,
            "p99": self.p99,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
        }


@dataclass
class Alert:
    """Performance alert."""
    id: str
    name: str
    severity: AlertSeverity
    message: str
    metric_name: str
    threshold: float
    current_value: float
    timestamp: datetime
    resolved: bool = False
    resolved_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "severity": self.severity.value,
            "message": self.message,
            "metric_name": self.name,
            "threshold": self.threshold,
            "current_value": self.current_value,
            "timestamp": self.timestamp.isoformat(),
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "metadata": self.metadata,
        }


class AnomalyDetector:
    """Anomaly detection for performance metrics."""
    
    def __init__(self, window_size: int = 100, threshold: float = 2.0):
        """Initialize anomaly detector.
        
        Args:
            window_size: Size of the sliding window
            threshold: Standard deviation threshold
        """
        self.window_size = window_size
        self.threshold = threshold
        self._data_windows: dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        
    def add_point(self, metric_name: str, value: float) -> bool:
        """Add data point and check for anomaly.
        
        Args:
            metric_name: Metric name
            value: Metric value
            
        Returns:
            True if anomaly detected
        """
        window = self._data_windows[metric_name]
        window.append(value)
        
        if len(window) < 10:  # Need minimum data points
            return False
            
        # Calculate statistics
        mean = statistics.mean(window)
        std_dev = statistics.stdev(window) if len(window) > 1 else 0
        
        if std_dev == 0:
            return False
            
        # Check if current point is anomaly
        z_score = abs((value - mean) / std_dev)
        
        return z_score > self.threshold
        
    def get_statistics(self, metric_name: str) -> dict[str, float]:
        """Get statistics for metric.
        
        Args:
            metric_name: Metric name
            
        Returns:
            Statistics dictionary
        """
        window = self._data_windows[metric_name]
        
        if not window:
            return {}
            
        return {
            "count": len(window),
            "mean": statistics.mean(window),
            "std_dev": statistics.stdev(window) if len(window) > 1 else 0,
            "min": min(window),
            "max": max(window),
            "median": statistics.median(window),
        }


class PerformanceMonitor:
    """Advanced performance monitoring system.
    
    Features:
    - Real-time metric collection
    - Performance aggregation
    - Anomaly detection
    - Alerting system
    - Historical data analysis
    - Performance dashboards
    """
    
    def __init__(self):
        """Initialize performance monitor."""
        self._redis_client = None
        self._is_initialized = False
        
        # Metric storage
        self._metrics: dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._aggregations: dict[str, MetricAggregation] = {}
        self._alerts: dict[str, Alert] = {}
        
        # Monitoring configuration
        self._collection_interval = 30  # seconds
        self._aggregation_window = 300  # 5 minutes
        self._alert_thresholds: dict[str, dict[str, Any]] = {}
        
        # Anomaly detection
        self._anomaly_detector = AnomalyDetector()
        
        # System monitoring
        self._system_metrics_enabled = True
        self._custom_metrics: dict[str, Callable] = {}
        
        # Background tasks
        self._collection_task: asyncio.Task | None = None
        self._aggregation_task: asyncio.Task | None = None
        self._is_collecting = False
        
        # Statistics
        self._stats = {
            "metrics_collected": 0,
            "alerts_triggered": 0,
            "alerts_resolved": 0,
            "anomalies_detected": 0,
            "collection_errors": 0,
            "avg_collection_time_ms": 0.0,
        }
        
    async def initialize(self) -> None:
        """Initialize performance monitor."""
        self._redis_client = get_redis_client()
        await self._redis_client.initialize()
        
        # Set default alert thresholds
        self._setup_default_thresholds()
        
        self._is_initialized = True
        
        _logger.info(
            "performance_monitor_initialized",
            collection_interval=self._collection_interval,
            aggregation_window=self._aggregation_window,
            system_metrics_enabled=self._system_metrics_enabled,
        )
        
    def _setup_default_thresholds(self) -> None:
        """Setup default alert thresholds."""
        self._alert_thresholds = {
            "cpu_percent": {
                "warning": 70.0,
                "critical": 90.0,
                "severity": AlertSeverity.HIGH,
            },
            "memory_percent": {
                "warning": 75.0,
                "critical": 95.0,
                "severity": AlertSeverity.HIGH,
            },
            "disk_percent": {
                "warning": 80.0,
                "critical": 95.0,
                "severity": AlertSeverity.MEDIUM,
            },
            "response_time_ms": {
                "warning": 500.0,
                "critical": 2000.0,
                "severity": AlertSeverity.HIGH,
            },
            "error_rate": {
                "warning": 0.05,
                "critical": 0.15,
                "severity": AlertSeverity.CRITICAL,
            },
        }
        
    async def start_monitoring(self) -> None:
        """Start performance monitoring."""
        if self._is_collecting:
            return
            
        self._is_collecting = True
        
        # Start collection task
        self._collection_task = asyncio.create_task(self._collection_loop())
        
        # Start aggregation task
        self._aggregation_task = asyncio.create_task(self._aggregation_loop())
        
        _logger.info("performance_monitoring_started")
        
    async def stop_monitoring(self) -> None:
        """Stop performance monitoring."""
        if not self._is_collecting:
            return
            
        self._is_collecting = False
        
        # Cancel tasks
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
                
        if self._aggregation_task:
            self._aggregation_task.cancel()
            try:
                await self._aggregation_task
            except asyncio.CancelledError:
                pass
                
        _logger.info("performance_monitoring_stopped")
        
    async def _collection_loop(self) -> None:
        """Main collection loop."""
        while self._is_collecting:
            try:
                start_time = time.time()
                
                # Collect system metrics
                if self._system_metrics_enabled:
                    await self._collect_system_metrics()
                    
                # Collect custom metrics
                await self._collect_custom_metrics()
                
                # Update statistics
                duration_ms = (time.time() - start_time) * 1000
                self._update_collection_stats(duration_ms)
                
                await asyncio.sleep(self._collection_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                _logger.error("metric_collection_error", error=str(e))
                self._stats["collection_errors"] += 1
                await asyncio.sleep(5)  # Brief pause before retry
                
    async def _aggregation_loop(self) -> None:
        """Main aggregation loop."""
        while self._is_collecting:
            try:
                # Aggregate metrics
                await self._aggregate_metrics()
                
                # Check alerts
                await self._check_alerts()
                
                # Clean up old data
                await self._cleanup_old_data()
                
                await asyncio.sleep(self._aggregation_window)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                _logger.error("metric_aggregation_error", error=str(e))
                await asyncio.sleep(30)  # Brief pause before retry
                
    async def _collect_system_metrics(self) -> None:
        """Collect system performance metrics."""
        timestamp = datetime.now(UTC)
        
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            await self._record_metric("cpu_percent", cpu_percent, timestamp)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            await self._record_metric("memory_percent", memory.percent, timestamp)
            await self._record_metric("memory_used_mb", memory.used / (1024 * 1024), timestamp)
            await self._record_metric("memory_available_mb", memory.available / (1024 * 1024), timestamp)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            await self._record_metric("disk_percent", (disk.used / disk.total) * 100, timestamp)
            await self._record_metric("disk_used_gb", disk.used / (1024 * 1024 * 1024), timestamp)
            await self._record_metric("disk_free_gb", disk.free / (1024 * 1024 * 1024), timestamp)
            
            # Network metrics
            network = psutil.net_io_counters()
            await self._record_metric("network_bytes_sent", network.bytes_sent, timestamp)
            await self._record_metric("network_bytes_recv", network.bytes_recv, timestamp)
            
            # Process metrics
            process = psutil.Process()
            await self._record_metric("process_cpu_percent", process.cpu_percent(), timestamp)
            await self._record_metric("process_memory_mb", process.memory_info().rss / (1024 * 1024), timestamp)
            await self._record_metric("process_threads", process.num_threads(), timestamp)
            
        except Exception as e:
            _logger.error("system_metrics_collection_failed", error=str(e))
            
    async def _collect_custom_metrics(self) -> None:
        """Collect custom metrics."""
        timestamp = datetime.now(UTC)
        
        for name, metric_func in self._custom_metrics.items():
            try:
                value = metric_func()
                await self._record_metric(name, value, timestamp)
            except Exception as e:
                _logger.error("custom_metric_collection_failed", name=name, error=str(e))
                
    async def _record_metric(self, name: str, value: float, timestamp: datetime, tags: dict[str, str] | None = None) -> None:
        """Record a metric point.
        
        Args:
            name: Metric name
            value: Metric value
            timestamp: Timestamp
            tags: Metric tags
        """
        metric_point = MetricPoint(
            name=name,
            value=value,
            timestamp=timestamp,
            tags=tags or {}
        )
        
        # Store in memory
        self._metrics[name].append(metric_point)
        
        # Store in Redis
        if self._redis_client:
            try:
                redis_key = f"metric:{name}:{timestamp.strftime('%Y%m%d%H%M')}"
                await self._redis_client.lpush(redis_key, metric_point.to_dict())
                await self._redis_client.expire(redis_key, 86400)  # 24 hours
            except Exception as e:
                _logger.error("metric_storage_failed", name=name, error=str(e))
                
        # Check for anomalies
        if self._anomaly_detector.add_point(name, value):
            await self._handle_anomaly(name, value, timestamp)
            
        # Update statistics
        self._stats["metrics_collected"] += 1
        
    async def _aggregate_metrics(self) -> None:
        """Aggregate metrics over time window."""
        current_time = datetime.now(UTC)
        window_start = current_time - timedelta(seconds=self._aggregation_window)
        
        for name, metric_points in self._metrics.items():
            # Filter points in window
            window_points = [
                point for point in metric_points
                if point.timestamp >= window_start
            ]
            
            if not window_points:
                continue
                
            # Calculate statistics
            values = [point.value for point in window_points]
            
            aggregation = MetricAggregation(
                name=name,
                count=len(values),
                sum_value=sum(values),
                min_value=min(values),
                max_value=max(values),
                avg_value=statistics.mean(values),
                p50=self._percentile(values, 50),
                p90=self._percentile(values, 90),
                p95=self._percentile(values, 95),
                p99=self._percentile(values, 99),
                timestamp=current_time,
            )
            
            self._aggregations[name] = aggregation
            
            # Store in Redis
            if self._redis_client:
                try:
                    redis_key = f"aggregation:{name}:{current_time.strftime('%Y%m%d%H%M')}"
                    await self._redis_client.set(redis_key, aggregation.to_dict(), ttl=86400 * 7)  # 7 days
                except Exception as e:
                    _logger.error("aggregation_storage_failed", name=name, error=str(e))
                    
    def _percentile(self, values: list[float], percentile: int) -> float:
        """Calculate percentile of values.
        
        Args:
            values: List of values
            percentile: Percentile to calculate
            
        Returns:
            Percentile value
        """
        if not values:
            return 0.0
            
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
        
    async def _check_alerts(self) -> None:
        """Check for alert conditions."""
        current_time = datetime.now(UTC)
        
        for metric_name, threshold_config in self._alert_thresholds.items():
            aggregation = self._aggregations.get(metric_name)
            if not aggregation:
                continue
                
            # Check warning threshold
            if aggregation.avg_value >= threshold_config["warning"]:
                alert_id = f"{metric_name}_warning"
                
                if alert_id not in self._alerts or not self._alerts[alert_id].resolved:
                    await self._trigger_alert(
                        alert_id,
                        metric_name,
                        aggregation.avg_value,
                        threshold_config["warning"],
                        AlertSeverity.WARNING if aggregation.avg_value < threshold_config["critical"] else AlertSeverity.CRITICAL,
                        current_time,
                    )
                    
            # Check for resolution
            elif aggregation.avg_value < threshold_config["warning"] * 0.9:  # 10% below threshold
                alert_id = f"{metric_name}_warning"
                if alert_id in self._alerts and not self._alerts[alert_id].resolved:
                    await self._resolve_alert(alert_id, current_time)
                    
    async def _trigger_alert(
        self,
        alert_id: str,
        metric_name: str,
        current_value: float,
        threshold: float,
        severity: AlertSeverity,
        timestamp: datetime
    ) -> None:
        """Trigger an alert.
        
        Args:
            alert_id: Alert ID
            metric_name: Metric name
            current_value: Current metric value
            threshold: Alert threshold
            severity: Alert severity
            timestamp: Alert timestamp
        """
        alert = Alert(
            id=alert_id,
            name=f"{metric_name} alert",
            severity=severity,
            message=f"{metric_name} exceeded threshold: {current_value:.2f} > {threshold:.2f}",
            metric_name=metric_name,
            threshold=threshold,
            current_value=current_value,
            timestamp=timestamp,
        )
        
        self._alerts[alert_id] = alert
        self._stats["alerts_triggered"] += 1
        
        _logger.warning(
            "alert_triggered",
            alert_id=alert_id,
            metric_name=metric_name,
            current_value=current_value,
            threshold=threshold,
            severity=severity.value,
        )
        
    async def _resolve_alert(self, alert_id: str, timestamp: datetime) -> None:
        """Resolve an alert.
        
        Args:
            alert_id: Alert ID
            timestamp: Resolution timestamp
        """
        if alert_id in self._alerts:
            self._alerts[alert_id].resolved = True
            self._alerts[alert_id].resolved_at = timestamp
            self._stats["alerts_resolved"] += 1
            
            _logger.info("alert_resolved", alert_id=alert_id)
            
    async def _handle_anomaly(self, metric_name: str, value: float, timestamp: datetime) -> None:
        """Handle detected anomaly.
        
        Args:
            metric_name: Metric name
            value: Anomalous value
            timestamp: Detection timestamp
        """
        self._stats["anomalies_detected"] += 1
        
        _logger.warning(
            "anomaly_detected",
            metric_name=metric_name,
            value=value,
            timestamp=timestamp.isoformat(),
        )
        
        # Create alert for anomaly
        alert_id = f"{metric_name}_anomaly"
        await self._trigger_alert(
            alert_id,
            metric_name,
            value,
            0.0,  # Anomaly doesn't have a specific threshold
            AlertSeverity.MEDIUM,
            timestamp,
        )
        
    async def _cleanup_old_data(self) -> None:
        """Clean up old metric data."""
        cutoff_time = datetime.now(UTC) - timedelta(hours=24)
        
        # Clean up old metrics
        for name, metric_points in self._metrics.items():
            # Filter out old points
            self._metrics[name] = deque(
                (point for point in metric_points if point.timestamp >= cutoff_time),
                maxlen=1000
            )
            
        # Clean up old aggregations
        old_aggregations = [
            name for name, agg in self._aggregations.items()
            if agg.timestamp < cutoff_time
        ]
        
        for name in old_aggregations:
            del self._aggregations[name]
            
        # Clean up old alerts
        old_alerts = [
            alert_id for alert_id, alert in self._alerts.items()
            if alert.timestamp < cutoff_time and alert.resolved
        ]
        
        for alert_id in old_alerts:
            del self._alerts[alert_id]
            
    def _update_collection_stats(self, duration_ms: float) -> None:
        """Update collection statistics.
        
        Args:
            duration_ms: Collection duration in milliseconds
        """
        current_avg = self._stats["avg_collection_time_ms"]
        count = self._stats["metrics_collected"]
        
        if count == 0:
            self._stats["avg_collection_time_ms"] = duration_ms
        else:
            self._stats["avg_collection_time_ms"] = (current_avg * (count - 1) + duration_ms) / count
            
    def add_custom_metric(self, name: str, metric_func: Callable[[], float]) -> None:
        """Add custom metric collection function.
        
        Args:
            name: Metric name
            metric_func: Function that returns metric value
        """
        self._custom_metrics[name] = metric_func
        _logger.debug("custom_metric_added", name=name)
        
    def remove_custom_metric(self, name: str) -> bool:
        """Remove custom metric.
        
        Args:
            name: Metric name
            
        Returns:
            True if metric was removed
        """
        if name in self._custom_metrics:
            del self._custom_metrics[name]
            _logger.debug("custom_metric_removed", name=name)
            return True
        return False
        
    def get_metric_history(self, name: str, hours: int = 1) -> list[MetricPoint]:
        """Get metric history.
        
        Args:
            name: Metric name
            hours: Hours of history to retrieve
            
        Returns:
            List of metric points
        """
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
        
        return [
            point for point in self._metrics.get(name, [])
            if point.timestamp >= cutoff_time
        ]
        
    def get_metric_aggregation(self, name: str) -> MetricAggregation | None:
        """Get latest metric aggregation.
        
        Args:
            name: Metric name
            
        Returns:
            Metric aggregation or None
        """
        return self._aggregations.get(name)
        
    def get_active_alerts(self) -> list[Alert]:
        """Get active (unresolved) alerts.
        
        Returns:
            List of active alerts
        """
        return [alert for alert in self._alerts.values() if not alert.resolved]
        
    def get_all_alerts(self) -> list[Alert]:
        """Get all alerts.
        
        Returns:
            List of all alerts
        """
        return list(self._alerts.values())
        
    def get_stats(self) -> dict[str, Any]:
        """Get monitor statistics.
        
        Returns:
            Statistics dictionary
        """
        stats = self._stats.copy()
        
        # Add current status
        stats["is_collecting"] = self._is_collecting
        stats["metrics_count"] = len(self._metrics)
        stats["aggregations_count"] = len(self._aggregations)
        stats["active_alerts_count"] = len(self.get_active_alerts())
        stats["total_alerts_count"] = len(self._alerts)
        stats["custom_metrics_count"] = len(self._custom_metrics)
        
        # Add system info
        if self._system_metrics_enabled:
            stats["system_info"] = {
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": psutil.virtual_memory().total / (1024 ** 3),
                "disk_total_gb": psutil.disk_usage('/').total / (1024 ** 3),
            }
            
        return stats
        
    async def health_check(self) -> dict[str, Any]:
        """Perform monitor health check.
        
        Returns:
            Health check results
        """
        try:
            start_time = time.time()
            
            # Test metric collection
            test_metric = "health_check"
            await self._record_metric(test_metric, 1.0, datetime.now(UTC))
            
            # Test Redis connection
            redis_healthy = True
            if self._redis_client:
                redis_health = await self._redis_client.health_check()
                redis_healthy = redis_health.get("status") == "healthy"
                
            duration_ms = (time.time() - start_time) * 1000
            
            health_data = {
                "status": "healthy",
                "is_collecting": self._is_collecting,
                "redis_healthy": redis_healthy,
                "metrics_count": len(self._metrics),
                "active_alerts": len(self.get_active_alerts()),
                "test_metric_recorded": True,
                "duration_ms": duration_ms,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            
            _logger.info("performance_monitor_health_check_success", **health_data)
            return health_data
            
        except Exception as e:
            error_data = {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }
            
            _logger.error("performance_monitor_health_check_failed", **error_data)
            return error_data


# Global performance monitor instance
_performance_monitor: PerformanceMonitor | None = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance.
    
    Returns:
        PerformanceMonitor instance
    """
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor
