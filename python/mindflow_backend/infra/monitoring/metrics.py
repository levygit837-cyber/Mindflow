"""Metrics collection and management system.

Provides comprehensive metrics collection, aggregation,
and monitoring capabilities for the OmniMind backend.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union, Callable
from datetime import datetime, UTC, timedelta
from enum import Enum

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.infra.config import get_settings

_logger = get_logger(__name__)


class MetricType(Enum):
    """Types of metrics that can be collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class MetricValue:
    """Single metric value with timestamp."""
    value: Union[int, float]
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    labels: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "labels": self.labels,
        }


@dataclass
class MetricSummary:
    """Summary statistics for a metric."""
    metric_name: str
    metric_type: MetricType
    count: int = 0
    sum_value: float = 0.0
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    avg_value: float = 0.0
    last_value: Optional[float] = None
    last_updated: Optional[datetime] = None
    
    def update(self, value: Union[int, float]) -> None:
        """Update summary with new value."""
        self.count += 1
        self.sum_value += float(value)
        self.last_value = float(value)
        self.last_updated = datetime.now(UTC)
        
        if self.min_value is None or float(value) < self.min_value:
            self.min_value = float(value)
            
        if self.max_value is None or float(value) > self.max_value:
            self.max_value = float(value)
            
        self.avg_value = self.sum_value / self.count
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "metric_name": self.metric_name,
            "metric_type": self.metric_type.value,
            "count": self.count,
            "sum": self.sum_value,
            "min": self.min_value,
            "max": self.max_value,
            "avg": self.avg_value,
            "last": self.last_value,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }


class Metric:
    """Base class for all metric types."""
    
    def __init__(self, name: str, metric_type: MetricType, description: str = ""):
        """Initialize metric.
        
        Args:
            name: Metric name
            metric_type: Type of metric
            description: Metric description
        """
        self.name = name
        self.metric_type = metric_type
        self.description = description
        self.created_at = datetime.now(UTC)
        self.labels: Dict[str, str] = {}
        
    def add_label(self, key: str, value: str) -> None:
        """Add a label to the metric.
        
        Args:
            key: Label key
            value: Label value
        """
        self.labels[key] = value
        
    def with_labels(self, **labels: str) -> "Metric":
        """Create a new metric instance with additional labels.
        
        Args:
            **labels: Labels to add
            
        Returns:
            New metric instance with labels
        """
        new_metric = self.__class__(self.name, self.metric_type, self.description)
        new_metric.labels = {**self.labels, **labels}
        return new_metric


class Counter(Metric):
    """Counter metric that can only increase."""
    
    def __init__(self, name: str, description: str = ""):
        """Initialize counter.
        
        Args:
            name: Counter name
            description: Counter description
        """
        super().__init__(name, MetricType.COUNTER, description)
        self._value = 0
        
    def inc(self, amount: int = 1) -> None:
        """Increment counter by specified amount.
        
        Args:
            amount: Amount to increment (must be positive)
        """
        if amount < 0:
            raise ValueError("Counter increment must be positive")
        self._value += amount
        
    def get_value(self) -> int:
        """Get current counter value.
        
        Returns:
            Current counter value
        """
        return self._value
        
    def reset(self) -> None:
        """Reset counter to zero."""
        self._value = 0


class Gauge(Metric):
    """Gauge metric that can increase or decrease."""
    
    def __init__(self, name: str, description: str = ""):
        """Initialize gauge.
        
        Args:
            name: Gauge name
            description: Gauge description
        """
        super().__init__(name, MetricType.GAUGE, description)
        self._value = 0
        
    def set(self, value: Union[int, float]) -> None:
        """Set gauge value.
        
        Args:
            value: New gauge value
        """
        self._value = float(value)
        
    def inc(self, amount: Union[int, float] = 1) -> None:
        """Increment gauge by specified amount.
        
        Args:
            amount: Amount to increment
        """
        self._value += float(amount)
        
    def dec(self, amount: Union[int, float] = 1) -> None:
        """Decrement gauge by specified amount.
        
        Args:
            amount: Amount to decrement
        """
        self._value -= float(amount)
        
    def get_value(self) -> float:
        """Get current gauge value.
        
        Returns:
            Current gauge value
        """
        return self._value


class Histogram(Metric):
    """Histogram metric that tracks value distributions."""
    
    def __init__(self, name: str, buckets: List[float] = None, description: str = ""):
        """Initialize histogram.
        
        Args:
            name: Histogram name
            buckets: Bucket boundaries for histogram
            description: Histogram description
        """
        super().__init__(name, MetricType.HISTOGRAM, description)
        self.buckets = buckets or [0.1, 0.5, 1.0, 2.5, 5.0, 10.0, float('inf')]
        self._bucket_counts = {bucket: 0 for bucket in self.buckets}
        self._count = 0
        self._sum = 0.0
        
    def observe(self, value: Union[int, float]) -> None:
        """Observe a value for the histogram.
        
        Args:
            value: Value to observe
        """
        value_float = float(value)
        self._count += 1
        self._sum += value_float
        
        # Update bucket counts
        for bucket in self.buckets:
            if value_float <= bucket:
                self._bucket_counts[bucket] += 1
                
    def get_bucket_counts(self) -> Dict[float, int]:
        """Get bucket counts.
        
        Returns:
            Dictionary of bucket boundaries to counts
        """
        return self._bucket_counts.copy()
        
    def get_count(self) -> int:
        """Get total observation count.
        
        Returns:
            Total count of observations
        """
        return self._count
        
    def get_sum(self) -> float:
        """Get sum of all observed values.
        
        Returns:
            Sum of all values
        """
        return self._sum
        
    def reset(self) -> None:
        """Reset histogram."""
        self._bucket_counts = {bucket: 0 for bucket in self.buckets}
        self._count = 0
        self._sum = 0.0


class Timer(Metric):
    """Timer metric for measuring duration of operations."""
    
    def __init__(self, name: str, description: str = ""):
        """Initialize timer.
        
        Args:
            name: Timer name
            description: Timer description
        """
        super().__init__(name, MetricType.TIMER, description)
        self._values: deque = deque(maxlen=1000)  # Keep last 1000 values
        self._count = 0
        self._sum = 0.0
        
    def time(self) -> "TimerContext":
        """Create a timer context manager.
        
        Returns:
            TimerContext for timing operations
        """
        return TimerContext(self)
        
    def observe(self, duration_ms: Union[int, float]) -> None:
        """Observe a duration value.
        
        Args:
            duration_ms: Duration in milliseconds
        """
        duration_float = float(duration_ms)
        self._values.append(duration_float)
        self._count += 1
        self._sum += duration_float
        
    def get_count(self) -> int:
        """Get total observation count.
        
        Returns:
            Total count of observations
        """
        return self._count
        
    def get_sum(self) -> float:
        """Get sum of all observed durations.
        
        Returns:
            Sum of all durations
        """
        return self._sum
        
    def get_avg(self) -> float:
        """Get average duration.
        
        Returns:
            Average duration in milliseconds
        """
        return self._sum / max(self._count, 1)
        
    def get_min(self) -> Optional[float]:
        """Get minimum observed duration.
        
        Returns:
            Minimum duration or None if no observations
        """
        return min(self._values) if self._values else None
        
    def get_max(self) -> Optional[float]:
        """Get maximum observed duration.
        
        Returns:
            Maximum duration or None if no observations
        """
        return max(self._values) if self._values else None
        
    def reset(self) -> None:
        """Reset timer."""
        self._values.clear()
        self._count = 0
        self._sum = 0.0


class TimerContext:
    """Context manager for timing operations."""
    
    def __init__(self, timer: Timer):
        """Initialize timer context.
        
        Args:
            timer: Timer instance to use
        """
        self.timer = timer
        self.start_time: Optional[float] = None
        
    def __enter__(self) -> "TimerContext":
        """Enter context and start timing."""
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context and record duration."""
        if self.start_time is not None:
            duration_ms = (time.time() - self.start_time) * 1000
            self.timer.observe(duration_ms)


class MetricsCollector:
    """Central metrics collection and management system.
    
    Provides:
    - Metric registration and management
    - Metric collection and aggregation
    - Performance monitoring
    - Export capabilities
    - Real-time metrics access
    """
    
    def __init__(self):
        """Initialize metrics collector."""
        self._metrics: Dict[str, Metric] = {}
        self._summaries: Dict[str, MetricSummary] = {}
        self._collection_task: Optional[asyncio.Task] = None
        self._is_collecting = False
        self._retention_hours = 24
        
        # Register default metrics
        self._register_default_metrics()
        
    def _register_default_metrics(self) -> None:
        """Register default system metrics."""
        # Request metrics
        self.register_counter("http_requests_total", "Total HTTP requests")
        self.register_counter("http_requests_errors_total", "Total HTTP request errors")
        self.register_timer("http_request_duration_ms", "HTTP request duration in milliseconds")
        
        # Database metrics
        self.register_counter("database_connections_total", "Total database connections")
        self.register_gauge("database_connections_active", "Active database connections")
        self.register_timer("database_query_duration_ms", "Database query duration in milliseconds")
        
        # Cache metrics
        self.register_counter("cache_hits_total", "Total cache hits")
        self.register_counter("cache_misses_total", "Total cache misses")
        self.register_timer("cache_operation_duration_ms", "Cache operation duration in milliseconds")
        
        # System metrics
        self.register_gauge("system_cpu_percent", "System CPU usage percentage")
        self.register_gauge("system_memory_percent", "System memory usage percentage")
        self.register_gauge("system_disk_percent", "System disk usage percentage")
        
    def register_counter(self, name: str, description: str = "") -> Counter:
        """Register a counter metric.
        
        Args:
            name: Counter name
            description: Counter description
            
        Returns:
            Counter instance
        """
        if name in self._metrics:
            raise ValueError(f"Metric {name} already registered")
            
        counter = Counter(name, description)
        self._metrics[name] = counter
        self._summaries[name] = MetricSummary(name, MetricType.COUNTER)
        
        _logger.debug("counter_registered", name=name, description=description)
        return counter
        
    def register_gauge(self, name: str, description: str = "") -> Gauge:
        """Register a gauge metric.
        
        Args:
            name: Gauge name
            description: Gauge description
            
        Returns:
            Gauge instance
        """
        if name in self._metrics:
            raise ValueError(f"Metric {name} already registered")
            
        gauge = Gauge(name, description)
        self._metrics[name] = gauge
        self._summaries[name] = MetricSummary(name, MetricType.GAUGE)
        
        _logger.debug("gauge_registered", name=name, description=description)
        return gauge
        
    def register_histogram(self, name: str, buckets: List[float] = None, description: str = "") -> Histogram:
        """Register a histogram metric.
        
        Args:
            name: Histogram name
            buckets: Bucket boundaries
            description: Histogram description
            
        Returns:
            Histogram instance
        """
        if name in self._metrics:
            raise ValueError(f"Metric {name} already registered")
            
        histogram = Histogram(name, buckets, description)
        self._metrics[name] = histogram
        self._summaries[name] = MetricSummary(name, MetricType.HISTOGRAM)
        
        _logger.debug("histogram_registered", name=name, description=description)
        return histogram
        
    def register_timer(self, name: str, description: str = "") -> Timer:
        """Register a timer metric.
        
        Args:
            name: Timer name
            description: Timer description
            
        Returns:
            Timer instance
        """
        if name in self._metrics:
            raise ValueError(f"Metric {name} already registered")
            
        timer = Timer(name, description)
        self._metrics[name] = timer
        self._summaries[name] = MetricSummary(name, MetricType.TIMER)
        
        _logger.debug("timer_registered", name=name, description=description)
        return timer
        
    def get_metric(self, name: str) -> Optional[Metric]:
        """Get a registered metric.
        
        Args:
            name: Metric name
            
        Returns:
            Metric instance or None if not found
        """
        return self._metrics.get(name)
        
    def get_all_metrics(self) -> Dict[str, Metric]:
        """Get all registered metrics.
        
        Returns:
            Dictionary of all metrics
        """
        return self._metrics.copy()
        
    def get_metric_summary(self, name: str) -> Optional[MetricSummary]:
        """Get summary for a specific metric.
        
        Args:
            name: Metric name
            
        Returns:
            Metric summary or None if not found
        """
        return self._summaries.get(name)
        
    def get_all_summaries(self) -> Dict[str, MetricSummary]:
        """Get summaries for all metrics.
        
        Returns:
            Dictionary of all metric summaries
        """
        return self._summaries.copy()
        
    def update_summaries(self) -> None:
        """Update all metric summaries with current values."""
        for name, metric in self._metrics.items():
            summary = self._summaries[name]
            
            if isinstance(metric, Counter):
                summary.update(metric.get_value())
            elif isinstance(metric, Gauge):
                summary.update(metric.get_value())
            elif isinstance(metric, Histogram):
                summary.update(metric.get_sum())
                # Also update count as a separate metric
                count_summary = MetricSummary(f"{name}_count", MetricType.COUNTER)
                count_summary.update(metric.get_count())
                self._summaries[f"{name}_count"] = count_summary
            elif isinstance(metric, Timer):
                summary.update(metric.get_sum())
                # Update additional timer metrics
                avg_summary = MetricSummary(f"{name}_avg", MetricType.GAUGE)
                avg_summary.update(metric.get_avg())
                self._summaries[f"{name}_avg"] = avg_summary
                
                count_summary = MetricSummary(f"{name}_count", MetricType.COUNTER)
                count_summary.update(metric.get_count())
                self._summaries[f"{name}_count"] = count_summary
                
    async def collect_metrics(self) -> Dict[str, Any]:
        """Collect all current metrics.
        
        Returns:
            Dictionary with all current metric values
        """
        self.update_summaries()
        
        collected = {}
        for name, metric in self._metrics.items():
            if isinstance(metric, Counter):
                collected[name] = {
                    "type": "counter",
                    "value": metric.get_value(),
                    "description": metric.description,
                }
            elif isinstance(metric, Gauge):
                collected[name] = {
                    "type": "gauge",
                    "value": metric.get_value(),
                    "description": metric.description,
                }
            elif isinstance(metric, Histogram):
                collected[name] = {
                    "type": "histogram",
                    "count": metric.get_count(),
                    "sum": metric.get_sum(),
                    "buckets": metric.get_bucket_counts(),
                    "description": metric.description,
                }
            elif isinstance(metric, Timer):
                collected[name] = {
                    "type": "timer",
                    "count": metric.get_count(),
                    "sum": metric.get_sum(),
                    "avg": metric.get_avg(),
                    "min": metric.get_min(),
                    "max": metric.get_max(),
                    "description": metric.description,
                }
                
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "metrics": collected,
            "summaries": {name: summary.to_dict() for name, summary in self._summaries.items()},
        }
        
    async def start_collection(self, interval_seconds: int = 60) -> None:
        """Start automatic metrics collection.
        
        Args:
            interval_seconds: Collection interval in seconds
        """
        if self._is_collecting:
            return
            
        self._is_collecting = True
        self._collection_task = asyncio.create_task(self._collection_loop(interval_seconds))
        
        _logger.info(
            "metrics_collection_started",
            interval=interval_seconds,
            metrics_count=len(self._metrics),
        )
        
    async def stop_collection(self) -> None:
        """Stop automatic metrics collection."""
        if not self._is_collecting:
            return
            
        self._is_collecting = False
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
                
        _logger.info("metrics_collection_stopped")
        
    async def _collection_loop(self, interval_seconds: int) -> None:
        """Main collection loop for automatic metrics collection.
        
        Args:
            interval_seconds: Interval between collections
        """
        while self._is_collecting:
            try:
                self.update_summaries()
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                _logger.error("metrics_collection_loop_error", error=str(e))
                await asyncio.sleep(5)  # Brief pause before retry
                
    def reset_all_metrics(self) -> None:
        """Reset all metrics to initial values."""
        for metric in self._metrics.values():
            if hasattr(metric, 'reset'):
                metric.reset()
                
        # Reset summaries
        for summary in self._summaries.values():
            summary.count = 0
            summary.sum_value = 0.0
            summary.min_value = None
            summary.max_value = None
            summary.avg_value = 0.0
            summary.last_value = None
            summary.last_updated = None
            
        _logger.info("all_metrics_reset")
        
    def export_prometheus_format(self) -> str:
        """Export metrics in Prometheus format.
        
        Returns:
            Prometheus-formatted metrics string
        """
        lines = []
        
        for name, metric in self._metrics.items():
            # Add metric metadata
            lines.append(f"# HELP {name} {metric.description}")
            lines.append(f"# TYPE {name} {metric.metric_type.value}")
            
            if isinstance(metric, Counter):
                lines.append(f"{name} {metric.get_value()}")
            elif isinstance(metric, Gauge):
                lines.append(f"{name} {metric.get_value()}")
            elif isinstance(metric, Histogram):
                # Export histogram buckets
                cumulative_count = 0
                for bucket, count in metric.get_bucket_counts().items():
                    cumulative_count += count
                    bucket_label = "+Inf" if bucket == float('inf') else str(bucket)
                    lines.append(f"{name}_bucket{{le=\"{bucket_label}\"}} {cumulative_count}")
                lines.append(f"{name}_count {metric.get_count()}")
                lines.append(f"{name}_sum {metric.get_sum()}")
            elif isinstance(metric, Timer):
                # Export timer as histogram
                lines.append(f"{name}_sum {metric.get_sum()}")
                lines.append(f"{name}_count {metric.get_count()}")
                
        return "\n".join(lines)


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector
