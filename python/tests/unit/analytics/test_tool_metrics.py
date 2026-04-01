"""Unit tests for analytics module.

Tests metrics collection, statistics, and tracking functionality.
"""

from __future__ import annotations

import time

import pytest

from mindflow_backend.agents.tools.analytics.tool_metrics import (
    ToolExecutionMetric,
    ToolMetricsCollector,
    get_metrics_collector,
    get_metrics_summary,
    get_tool_stats,
    log_file_operation,
    track_operation,
)


class TestToolExecutionMetric:
    """Test ToolExecutionMetric dataclass."""

    def test_metric_creation(self):
        """Test creating a metric."""
        metric = ToolExecutionMetric(
            tool_name="test_tool",
            operation="test_op",
            start_time=time.time(),
            success=True
        )

        assert metric.tool_name == "test_tool"
        assert metric.operation == "test_op"
        assert metric.success is True
        assert metric.duration is None  # Not ended yet

    def test_metric_duration_calculation(self):
        """Test duration calculation."""
        start = time.time()
        metric = ToolExecutionMetric(
            tool_name="test_tool",
            operation="test_op",
            start_time=start,
            end_time=start + 1.5
        )

        assert metric.duration is not None
        assert 1.4 < metric.duration < 1.6

    def test_metric_to_dict(self):
        """Test converting metric to dict."""
        metric = ToolExecutionMetric(
            tool_name="test_tool",
            operation="test_op",
            start_time=time.time(),
            success=True,
            metadata={"key": "value"}
        )

        result = metric.to_dict()

        assert result["tool_name"] == "test_tool"
        assert result["operation"] == "test_op"
        assert result["success"] is True
        assert result["metadata"]["key"] == "value"


class TestToolMetricsCollector:
    """Test ToolMetricsCollector class."""

    @pytest.fixture
    def collector(self):
        """Create fresh collector."""
        collector = ToolMetricsCollector()
        collector.clear_metrics()
        return collector

    def test_start_operation(self, collector):
        """Test starting an operation."""
        op_id = collector.start_operation("test_tool", "test_op")

        assert op_id is not None
        assert "test_tool" in op_id
        assert "test_op" in op_id

    def test_end_operation_success(self, collector):
        """Test ending operation successfully."""
        op_id = collector.start_operation("test_tool", "test_op")
        metric = collector.end_operation(op_id, success=True)

        assert metric is not None
        assert metric.success is True
        assert metric.duration is not None
        assert metric.duration >= 0

    def test_end_operation_failure(self, collector):
        """Test ending operation with failure."""
        op_id = collector.start_operation("test_tool", "test_op")
        metric = collector.end_operation(
            op_id,
            success=False,
            error="Test error"
        )

        assert metric is not None
        assert metric.success is False
        assert metric.error == "Test error"

    def test_end_operation_not_found(self, collector):
        """Test ending nonexistent operation."""
        metric = collector.end_operation("nonexistent_id")
        assert metric is None

    def test_get_metrics_all(self, collector):
        """Test getting all metrics."""
        # Create some operations
        for i in range(3):
            op_id = collector.start_operation("test_tool", f"op{i}")
            collector.end_operation(op_id, success=True)

        metrics = collector.get_metrics()

        assert len(metrics) == 3

    def test_get_metrics_filtered_by_tool(self, collector):
        """Test getting metrics filtered by tool name."""
        # Create operations for different tools
        op1 = collector.start_operation("tool1", "op")
        collector.end_operation(op1, success=True)

        op2 = collector.start_operation("tool2", "op")
        collector.end_operation(op2, success=True)

        metrics = collector.get_metrics(tool_name="tool1")

        assert len(metrics) == 1
        assert metrics[0]["tool_name"] == "tool1"

    def test_get_metrics_with_limit(self, collector):
        """Test getting metrics with limit."""
        # Create many operations
        for i in range(10):
            op_id = collector.start_operation("test_tool", f"op{i}")
            collector.end_operation(op_id, success=True)

        metrics = collector.get_metrics(limit=5)

        assert len(metrics) == 5

    def test_get_stats_single_tool(self, collector):
        """Test getting stats for single tool."""
        # Create successful operations
        for i in range(3):
            op_id = collector.start_operation("test_tool", f"op{i}")
            collector.end_operation(op_id, success=True)

        # Create failed operation
        op_id = collector.start_operation("test_tool", "fail_op")
        collector.end_operation(op_id, success=False, error="Test error")

        stats = collector.get_stats("test_tool")

        assert stats["total_executions"] == 4
        assert stats["successful_executions"] == 3
        assert stats["failed_executions"] == 1
        assert stats["success_rate"] == 75.0
        assert stats["average_duration"] > 0

    def test_get_stats_all_tools(self, collector):
        """Test getting stats for all tools."""
        # Create operations for multiple tools
        op1 = collector.start_operation("tool1", "op")
        collector.end_operation(op1, success=True)

        op2 = collector.start_operation("tool2", "op")
        collector.end_operation(op2, success=True)

        stats = collector.get_stats()

        assert "tool1" in stats
        assert "tool2" in stats
        assert stats["tool1"]["total_executions"] == 1
        assert stats["tool2"]["total_executions"] == 1

    def test_get_summary(self, collector):
        """Test getting overall summary."""
        # Create operations for multiple tools
        for i in range(3):
            op_id = collector.start_operation("tool1", f"op{i}")
            collector.end_operation(op_id, success=True)

        for i in range(2):
            op_id = collector.start_operation("tool2", f"op{i}")
            collector.end_operation(op_id, success=i == 0)  # 1 success, 1 fail

        summary = collector.get_summary()

        assert summary["total_tools"] == 2
        assert summary["total_executions"] == 5
        assert summary["successful_executions"] == 4
        assert summary["failed_executions"] == 1
        assert summary["success_rate"] == 80.0

    def test_clear_metrics(self, collector):
        """Test clearing all metrics."""
        # Create some operations
        op_id = collector.start_operation("test_tool", "op")
        collector.end_operation(op_id, success=True)

        assert len(collector.get_metrics()) > 0

        collector.clear_metrics()

        assert len(collector.get_metrics()) == 0
        summary = collector.get_summary()
        assert summary["total_executions"] == 0


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_log_file_operation_with_duration(self):
        """Test logging file operation with duration."""
        collector = get_metrics_collector()
        collector.clear_metrics()

        log_file_operation(
            tool_name="file_read",
            operation="read",
            file_path="/test/file.txt",
            success=True,
            duration=0.5
        )

        stats = get_tool_stats("file_read")
        assert stats["total_executions"] >= 1

    def test_log_file_operation_without_duration(self):
        """Test logging file operation without duration."""
        collector = get_metrics_collector()
        collector.clear_metrics()

        log_file_operation(
            tool_name="file_write",
            operation="write",
            file_path="/test/file.txt",
            success=True
        )

        stats = get_tool_stats("file_write")
        assert stats["total_executions"] >= 1

    def test_get_tool_stats_convenience(self):
        """Test get_tool_stats convenience function."""
        collector = get_metrics_collector()
        collector.clear_metrics()

        op_id = collector.start_operation("test_tool", "op")
        collector.end_operation(op_id, success=True)

        stats = get_tool_stats("test_tool")

        assert stats["total_executions"] == 1
        assert stats["success_rate"] == 100.0

    def test_get_metrics_summary_convenience(self):
        """Test get_metrics_summary convenience function."""
        collector = get_metrics_collector()
        collector.clear_metrics()

        op_id = collector.start_operation("test_tool", "op")
        collector.end_operation(op_id, success=True)

        summary = get_metrics_summary()

        assert summary["total_executions"] >= 1


class TestTrackOperationContextManager:
    """Test track_operation context manager."""

    def test_context_manager_success(self):
        """Test context manager with successful operation."""
        collector = get_metrics_collector()
        collector.clear_metrics()

        with track_operation("test_tool", "test_op", {"key": "value"}):
            time.sleep(0.01)  # Simulate work

        stats = get_tool_stats("test_tool")

        assert stats["total_executions"] == 1
        assert stats["successful_executions"] == 1
        assert stats["success_rate"] == 100.0

    def test_context_manager_with_exception(self):
        """Test context manager with exception."""
        collector = get_metrics_collector()
        collector.clear_metrics()

        try:
            with track_operation("test_tool", "test_op"):
                raise ValueError("Test error")
        except ValueError:
            pass

        stats = get_tool_stats("test_tool")

        assert stats["total_executions"] == 1
        assert stats["failed_executions"] == 1
        assert stats["success_rate"] == 0.0

    def test_context_manager_metadata(self):
        """Test context manager preserves metadata."""
        collector = get_metrics_collector()
        collector.clear_metrics()

        with track_operation("test_tool", "test_op", {"file": "test.txt"}):
            pass

        metrics = collector.get_metrics("test_tool")

        assert len(metrics) == 1
        assert metrics[0]["metadata"]["file"] == "test.txt"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
