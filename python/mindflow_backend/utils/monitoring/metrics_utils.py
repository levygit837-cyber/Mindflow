"""Metrics collection utilities for MindFlow backend.

Lightweight metrics collection and aggregation utilities.
"""

import time
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class Metric:
    """Base class for metrics."""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.created_at = datetime.now(UTC)
        self.last_updated = self.created_at
    
    def update(self, value: Any) -> None:
        """Update metric value."""
        self.last_updated = datetime.now(UTC)
    
    def get_value(self) -> Any:
        """Get current metric value."""
        raise NotImplementedError
    
    def reset(self) -> None:
        """Reset metric to initial state."""
        pass


class Counter(Metric):
    """Counter metric that can be incremented."""
    
    def __init__(self, name: str, description: str = "", initial_value: int = 0):
        super().__init__(name, description)
        self.value = initial_value
    
    def increment(self, amount: int = 1) -> None:
        """Increment counter."""
        self.value += amount
        self.update(None)
    
    def decrement(self, amount: int = 1) -> None:
        """Decrement counter."""
        self.value -= amount
        self.update(None)
    
    def get_value(self) -> int:
        """Get counter value."""
        return self.value
    
    def reset(self) -> None:
        """Reset counter to zero."""
        self.value = 0


class Gauge(Metric):
    """Gauge metric that can go up and down."""
    
    def __init__(self, name: str, description: str = "", initial_value: float = 0.0):
        super().__init__(name, description)
        self.value = float(initial_value)
    
    def set(self, value: Union[int, float]) -> None:
        """Set gauge value."""
        self.value = float(value)
        self.update(None)
    
    def increment(self, amount: Union[int, float] = 1.0) -> None:
        """Increment gauge."""
        self.value += float(amount)
        self.update(None)
    
    def decrement(self, amount: Union[int, float] = 1.0) -> None:
        """Decrement gauge."""
        self.value -= float(amount)
        self.update(None)
    
    def get_value(self) -> float:
        """Get gauge value."""
        return self.value
    
    def reset(self) -> None:
        """Reset gauge to zero."""
        self.value = 0.0


class Histogram(Metric):
    """Histogram metric that tracks distribution of values."""
    
    def __init__(
        self,
        name: str,
        description: str = "",
        buckets: Optional[List[float]] = None,
    ):
        super().__init__(name, description)
        self.buckets = buckets or [0.1, 0.5, 1.0, 2.5, 5.0, 10.0, float('inf')]
        self.bucket_counts = {bucket: 0 for bucket in self.buckets}
        self.count = 0
        self.sum = 0.0
    
    def observe(self, value: Union[int, float]) -> None:
        """Observe a value."""
        value = float(value)
        self.count += 1
        self.sum += value
        
        # Update bucket counts
        for bucket in self.buckets:
            if value <= bucket:
                self.bucket_counts[bucket] += 1
        
        self.update(None)
    
    def get_value(self) -> Dict[str, Any]:
        """Get histogram statistics."""
        return {
            "count": self.count,
            "sum": self.sum,
            "average": self.sum / self.count if self.count > 0 else 0.0,
            "bucket_counts": dict(self.bucket_counts),
            "buckets": self.buckets,
        }
    
    def reset(self) -> None:
        """Reset histogram."""
        self.bucket_counts = {bucket: 0 for bucket in self.buckets}
        self.count = 0
        self.sum = 0.0


class Summary(Metric):
    """Summary metric that tracks statistics over time."""
    
    def __init__(
        self,
        name: str,
        description: str = "",
        max_samples: int = 1000,
        age_buckets: int = 5,
    ):
        super().__init__(name, description)
        self.max_samples = max_samples
        self.age_buckets = age_buckets
        self.samples = deque(maxlen=max_samples)
        self.count = 0
        self.sum = 0.0
    
    def observe(self, value: Union[int, float]) -> None:
        """Observe a value."""
        value = float(value)
        self.samples.append(value)
        self.count += 1
        self.sum += value
        self.update(None)
    
    def get_value(self) -> Dict[str, Any]:
        """Get summary statistics."""
        if not self.samples:
            return {
                "count": 0,
                "sum": 0.0,
                "average": 0.0,
                "min": 0.0,
                "max": 0.0,
                "median": 0.0,
                "p95": 0.0,
                "p99": 0.0,
            }
        
        sorted_samples = sorted(self.samples)
        count = len(sorted_samples)
        
        return {
            "count": self.count,
            "sum": self.sum,
            "average": self.sum / count,
            "min": sorted_samples[0],
            "max": sorted_samples[-1],
            "median": sorted_samples[count // 2],
            "p95": sorted_samples[int(count * 0.95)],
            "p99": sorted_samples[int(count * 0.99)],
        }
    
    def reset(self) -> None:
        """Reset summary."""
        self.samples.clear()
        self.count = 0
        self.sum = 0.0


class Timer:
    """Context manager for timing operations."""
    
    def __init__(self, histogram: Optional[Histogram] = None, summary: Optional[Summary] = None):
        self.histogram = histogram
        self.summary = summary
        self.start_time: Optional[float] = None
        self.duration: Optional[float] = None
    
    def __enter__(self) -> "Timer":
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.start_time is not None:
            self.duration = time.time() - self.start_time
            
            if self.histogram:
                self.histogram.observe(self.duration)
            if self.summary:
                self.summary.observe(self.duration)
    
    def get_duration(self) -> Optional[float]:
        """Get measured duration."""
        return self.duration


class MetricsRegistry:
    """Registry for managing metrics."""
    
    def __init__(self):
        self.metrics: Dict[str, Metric] = {}
        self.tags: Dict[str, Dict[str, str]] = {}
    
    def counter(self, name: str, description: str = "", tags: Optional[Dict[str, str]] = None) -> Counter:
        """Get or create a counter."""
        if name not in self.metrics:
            self.metrics[name] = Counter(name, description)
            if tags:
                self.tags[name] = tags
        elif not isinstance(self.metrics[name], Counter):
            raise ValueError(f"Metric '{name}' already exists but is not a Counter")
        
        return self.metrics[name]
    
    def gauge(self, name: str, description: str = "", tags: Optional[Dict[str, str]] = None) -> Gauge:
        """Get or create a gauge."""
        if name not in self.metrics:
            self.metrics[name] = Gauge(name, description)
            if tags:
                self.tags[name] = tags
        elif not isinstance(self.metrics[name], Gauge):
            raise ValueError(f"Metric '{name}' already exists but is not a Gauge")
        
        return self.metrics[name]
    
    def histogram(
        self,
        name: str,
        description: str = "",
        buckets: Optional[List[float]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> Histogram:
        """Get or create a histogram."""
        if name not in self.metrics:
            self.metrics[name] = Histogram(name, description, buckets)
            if tags:
                self.tags[name] = tags
        elif not isinstance(self.metrics[name], Histogram):
            raise ValueError(f"Metric '{name}' already exists but is not a Histogram")
        
        return self.metrics[name]
    
    def summary(
        self,
        name: str,
        description: str = "",
        max_samples: int = 1000,
        tags: Optional[Dict[str, str]] = None,
    ) -> Summary:
        """Get or create a summary."""
        if name not in self.metrics:
            self.metrics[name] = Summary(name, description, max_samples)
            if tags:
                self.tags[name] = tags
        elif not isinstance(self.metrics[name], Summary):
            raise ValueError(f"Metric '{name}' already exists but is not a Summary")
        
        return self.metrics[name]
    
    def timer(
        self,
        name: str,
        description: str = "",
        buckets: Optional[List[float]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> Timer:
        """Create a timer that records to a histogram."""
        histogram = self.histogram(name, description, buckets, tags)
        return Timer(histogram=histogram)
    
    def get_metric(self, name: str) -> Optional[Metric]:
        """Get a metric by name."""
        return self.metrics.get(name)
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all metrics as a dictionary."""
        result = {}
        
        for name, metric in self.metrics.items():
            metric_data = {
                "name": metric.name,
                "description": metric.description,
                "type": metric.__class__.__name__.lower(),
                "created_at": metric.created_at.isoformat(),
                "last_updated": metric.last_updated.isoformat(),
                "value": metric.get_value(),
                "tags": self.tags.get(name, {}),
            }
            result[name] = metric_data
        
        return result
    
    def reset_metric(self, name: str) -> bool:
        """Reset a specific metric."""
        if name in self.metrics:
            self.metrics[name].reset()
            return True
        return False
    
    def reset_all(self) -> None:
        """Reset all metrics."""
        for metric in self.metrics.values():
            metric.reset()
    
    def remove_metric(self, name: str) -> bool:
        """Remove a metric."""
        if name in self.metrics:
            del self.metrics[name]
            self.tags.pop(name, None)
            return True
        return False


class PerformanceTracker:
    """Track performance metrics for operations."""
    
    def __init__(self, registry: Optional[MetricsRegistry] = None):
        self.registry = registry or MetricsRegistry()
        self.operation_timers = defaultdict(list)
    
    def track_operation(self, operation_name: str, duration: float) -> None:
        """Track an operation duration."""
        histogram = self.registry.histogram(
            f"operation_duration_{operation_name}",
            f"Duration of {operation_name} operations",
            buckets=[0.001, 0.01, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0, float('inf')],
        )
        histogram.observe(duration)
        
        self.operation_timers[operation_name].append({
            "duration": duration,
            "timestamp": datetime.now(UTC),
        })
    
    def time_operation(self, operation_name: str):
        """Context manager for timing operations."""
        return Timer(
            histogram=self.registry.histogram(
                f"operation_duration_{operation_name}",
                f"Duration of {operation_name} operations",
            ),
            summary=self.registry.summary(
                f"operation_summary_{operation_name}",
                f"Summary of {operation_name} operations",
            ),
        )
    
    def get_operation_stats(self, operation_name: str, minutes: int = 60) -> Dict[str, Any]:
        """Get statistics for an operation."""
        cutoff_time = datetime.now(UTC) - timedelta(minutes=minutes)
        
        recent_operations = [
            op for op in self.operation_timers[operation_name]
            if op["timestamp"] > cutoff_time
        ]
        
        if not recent_operations:
            return {
                "operation": operation_name,
                "count": 0,
                "average_duration": 0.0,
                "min_duration": 0.0,
                "max_duration": 0.0,
                "total_duration": 0.0,
            }
        
        durations = [op["duration"] for op in recent_operations]
        
        return {
            "operation": operation_name,
            "count": len(durations),
            "average_duration": sum(durations) / len(durations),
            "min_duration": min(durations),
            "max_duration": max(durations),
            "total_duration": sum(durations),
            "period_minutes": minutes,
        }


# Global metrics registry instance
_metrics_registry: Optional[MetricsRegistry] = None


def get_metrics_registry() -> MetricsRegistry:
    """Get or create global metrics registry."""
    global _metrics_registry
    if _metrics_registry is None:
        _metrics_registry = MetricsRegistry()
    return _metrics_registry


# Global performance tracker instance
_performance_tracker: Optional[PerformanceTracker] = None


def get_performance_tracker() -> PerformanceTracker:
    """Get or create global performance tracker."""
    global _performance_tracker
    if _performance_tracker is None:
        _performance_tracker = PerformanceTracker(get_metrics_registry())
    return _performance_tracker


# Decorators for easy metric collection
def counter_metric(name: str, description: str = "", amount: int = 1):
    """Decorator to count function calls."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            registry = get_metrics_registry()
            counter = registry.counter(name, description)
            counter.increment(amount)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def timer_metric(name: str, description: str = ""):
    """Decorator to time function execution."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            tracker = get_performance_tracker()
            with tracker.time_operation(name):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def gauge_metric(name: str, description: str = "", value_func=None):
    """Decorator to track gauge values."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            registry = get_metrics_registry()
            gauge = registry.gauge(name, description)
            
            if value_func:
                gauge.set(value_func(result))
            else:
                gauge.set(result)
            
            return result
        return wrapper
    return decorator
