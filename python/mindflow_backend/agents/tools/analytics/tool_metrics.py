"""Analytics and metrics tracking for MindFlow tools.

Provides execution time tracking, error monitoring, and usage analytics
for tool operations.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


# ============================================================================
# Metrics Data Structures
# ============================================================================

@dataclass
class ToolExecutionMetric:
    """Metrics for a single tool execution."""

    tool_name: str
    operation: str
    start_time: float
    end_time: float | None = None
    success: bool = True
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float | None:
        """Get execution duration in seconds."""
        if self.end_time is None:
            return None
        return self.end_time - self.start_time

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tool_name": self.tool_name,
            "operation": self.operation,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "success": self.success,
            "error": self.error,
            "metadata": self.metadata
        }


# ============================================================================
# Metrics Collector
# ============================================================================

class ToolMetricsCollector:
    """Collect and aggregate tool execution metrics."""

    def __init__(self):
        """Initialize metrics collector."""
        self._metrics: list[ToolExecutionMetric] = []
        self._active_operations: dict[str, ToolExecutionMetric] = {}
        self._stats: dict[str, dict[str, Any]] = defaultdict(lambda: {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_duration": 0.0,
            "min_duration": float('inf'),
            "max_duration": 0.0,
            "errors": []
        })

    def start_operation(
        self,
        tool_name: str,
        operation: str,
        metadata: dict[str, Any] | None = None
    ) -> str:
        """Start tracking a tool operation.

        Args:
            tool_name: Name of the tool
            operation: Operation being performed
            metadata: Additional metadata

        Returns:
            Operation ID for tracking
        """
        operation_id = f"{tool_name}_{operation}_{time.time()}"

        metric = ToolExecutionMetric(
            tool_name=tool_name,
            operation=operation,
            start_time=time.time(),
            metadata=metadata or {}
        )

        self._active_operations[operation_id] = metric
        _logger.debug(f"Started tracking operation: {operation_id}")

        return operation_id

    def end_operation(
        self,
        operation_id: str,
        success: bool = True,
        error: str | None = None,
        metadata: dict[str, Any] | None = None
    ) -> ToolExecutionMetric | None:
        """End tracking a tool operation.

        Args:
            operation_id: Operation ID from start_operation
            success: Whether operation succeeded
            error: Error message if failed
            metadata: Additional metadata to merge

        Returns:
            Completed metric or None if operation not found
        """
        if operation_id not in self._active_operations:
            _logger.warning(f"Operation not found: {operation_id}")
            return None

        metric = self._active_operations.pop(operation_id)
        metric.end_time = time.time()
        metric.success = success
        metric.error = error

        if metadata:
            metric.metadata.update(metadata)

        # Store metric
        self._metrics.append(metric)

        # Update stats
        self._update_stats(metric)

        _logger.debug(
            f"Completed operation: {operation_id} "
            f"(duration: {metric.duration:.3f}s, success: {success})"
        )

        return metric

    def _update_stats(self, metric: ToolExecutionMetric) -> None:
        """Update aggregated statistics.

        Args:
            metric: Completed metric
        """
        stats = self._stats[metric.tool_name]

        stats["total_executions"] += 1

        if metric.success:
            stats["successful_executions"] += 1
        else:
            stats["failed_executions"] += 1
            if metric.error:
                stats["errors"].append({
                    "timestamp": metric.start_time,
                    "operation": metric.operation,
                    "error": metric.error
                })

        if metric.duration is not None:
            stats["total_duration"] += metric.duration
            stats["min_duration"] = min(stats["min_duration"], metric.duration)
            stats["max_duration"] = max(stats["max_duration"], metric.duration)

    def get_metrics(
        self,
        tool_name: str | None = None,
        limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Get collected metrics.

        Args:
            tool_name: Optional filter by tool name
            limit: Optional limit on number of results

        Returns:
            List of metric dicts
        """
        metrics = self._metrics

        if tool_name:
            metrics = [m for m in metrics if m.tool_name == tool_name]

        if limit:
            metrics = metrics[-limit:]

        return [m.to_dict() for m in metrics]

    def get_stats(self, tool_name: str | None = None) -> dict[str, Any]:
        """Get aggregated statistics.

        Args:
            tool_name: Optional filter by tool name

        Returns:
            Statistics dict
        """
        if tool_name:
            stats = self._stats.get(tool_name, {})
            return self._format_stats(tool_name, stats)

        # Return stats for all tools
        all_stats = {}
        for name, stats in self._stats.items():
            all_stats[name] = self._format_stats(name, stats)

        return all_stats

    def _format_stats(self, tool_name: str, stats: dict[str, Any]) -> dict[str, Any]:
        """Format statistics for output.

        Args:
            tool_name: Tool name
            stats: Raw statistics

        Returns:
            Formatted statistics
        """
        total = stats.get("total_executions", 0)
        total_duration = stats.get("total_duration", 0.0)

        formatted = {
            "tool_name": tool_name,
            "total_executions": total,
            "successful_executions": stats.get("successful_executions", 0),
            "failed_executions": stats.get("failed_executions", 0),
            "success_rate": (
                stats.get("successful_executions", 0) / total * 100
                if total > 0 else 0.0
            ),
            "total_duration": total_duration,
            "average_duration": total_duration / total if total > 0 else 0.0,
            "min_duration": (
                stats.get("min_duration")
                if stats.get("min_duration") != float('inf') else 0.0
            ),
            "max_duration": stats.get("max_duration", 0.0),
            "recent_errors": stats.get("errors", [])[-5:]  # Last 5 errors
        }

        return formatted

    def clear_metrics(self) -> None:
        """Clear all collected metrics and statistics."""
        self._metrics.clear()
        self._active_operations.clear()
        self._stats.clear()
        _logger.info("Cleared all metrics")

    def get_summary(self) -> dict[str, Any]:
        """Get overall summary of all metrics.

        Returns:
            Summary dict with aggregate statistics
        """
        total_executions = sum(
            s.get("total_executions", 0) for s in self._stats.values()
        )
        total_successful = sum(
            s.get("successful_executions", 0) for s in self._stats.values()
        )
        total_failed = sum(
            s.get("failed_executions", 0) for s in self._stats.values()
        )
        total_duration = sum(
            s.get("total_duration", 0.0) for s in self._stats.values()
        )

        return {
            "total_tools": len(self._stats),
            "total_executions": total_executions,
            "successful_executions": total_successful,
            "failed_executions": total_failed,
            "success_rate": (
                total_successful / total_executions * 100
                if total_executions > 0 else 0.0
            ),
            "total_duration": total_duration,
            "average_duration": (
                total_duration / total_executions
                if total_executions > 0 else 0.0
            ),
            "active_operations": len(self._active_operations)
        }


# ============================================================================
# Global Metrics Collector
# ============================================================================

_global_metrics_collector: ToolMetricsCollector | None = None


def get_metrics_collector() -> ToolMetricsCollector:
    """Get global metrics collector instance.

    Returns:
        ToolMetricsCollector instance
    """
    global _global_metrics_collector
    if _global_metrics_collector is None:
        _global_metrics_collector = ToolMetricsCollector()
    return _global_metrics_collector


# ============================================================================
# Convenience Functions
# ============================================================================

def log_file_operation(
    tool_name: str,
    operation: str,
    file_path: str,
    success: bool = True,
    error: str | None = None,
    duration: float | None = None,
    metadata: dict[str, Any] | None = None
) -> None:
    """Log a file operation for analytics.

    Args:
        tool_name: Name of the tool
        operation: Operation performed
        file_path: Path to the file
        success: Whether operation succeeded
        error: Error message if failed
        duration: Operation duration in seconds
        metadata: Additional metadata
    """
    collector = get_metrics_collector()

    # Create metric manually if duration provided
    if duration is not None:
        start_time = time.time() - duration
        metric = ToolExecutionMetric(
            tool_name=tool_name,
            operation=operation,
            start_time=start_time,
            end_time=time.time(),
            success=success,
            error=error,
            metadata={
                "file_path": file_path,
                **(metadata or {})
            }
        )
        collector._metrics.append(metric)
        collector._update_stats(metric)
    else:
        # Use start/end tracking
        op_id = collector.start_operation(
            tool_name,
            operation,
            {"file_path": file_path, **(metadata or {})}
        )
        collector.end_operation(op_id, success, error)


def get_tool_stats(tool_name: str | None = None) -> dict[str, Any]:
    """Get statistics for a tool or all tools.

    Args:
        tool_name: Optional tool name filter

    Returns:
        Statistics dict
    """
    collector = get_metrics_collector()
    return collector.get_stats(tool_name)


def get_metrics_summary() -> dict[str, Any]:
    """Get overall metrics summary.

    Returns:
        Summary dict
    """
    collector = get_metrics_collector()
    return collector.get_summary()


# ============================================================================
# Context Manager for Tracking
# ============================================================================

class track_operation:
    """Context manager for tracking tool operations.

    Usage:
        with track_operation("file_read", "read", {"file": "test.txt"}):
            # perform operation
            pass
    """

    def __init__(
        self,
        tool_name: str,
        operation: str,
        metadata: dict[str, Any] | None = None
    ):
        """Initialize tracker.

        Args:
            tool_name: Name of the tool
            operation: Operation being performed
            metadata: Additional metadata
        """
        self.tool_name = tool_name
        self.operation = operation
        self.metadata = metadata
        self.operation_id: str | None = None
        self.collector = get_metrics_collector()

    def __enter__(self):
        """Start tracking."""
        self.operation_id = self.collector.start_operation(
            self.tool_name,
            self.operation,
            self.metadata
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End tracking."""
        if self.operation_id:
            success = exc_type is None
            error = str(exc_val) if exc_val else None
            self.collector.end_operation(self.operation_id, success, error)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "ToolExecutionMetric",
    "ToolMetricsCollector",
    "get_metrics_collector",
    "log_file_operation",
    "get_tool_stats",
    "get_metrics_summary",
    "track_operation",
]
