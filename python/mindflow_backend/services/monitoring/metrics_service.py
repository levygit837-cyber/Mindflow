"""Metrics service for collecting and managing application metrics.

This service provides comprehensive metrics collection including counters,
timings, gauges, and dashboard creation capabilities.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from datetime import UTC, datetime
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.services.interfaces.base_interfaces import BaseAbstractService
from mindflow_backend.services.interfaces.monitoring_interfaces import MetricsServiceInterface


class MetricsService(BaseAbstractService, MetricsServiceInterface):
    """Service for metrics collection and management.
    
    This service provides comprehensive metrics collection including
    counters, timings, gauges, and real-time monitoring.
    """
    
    def __init__(self) -> None:
        """Initialize metrics service with storage and aggregation."""
        super().__init__()
        
        # Metrics storage
        self._counters: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._timings: dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._gauges: dict[str, float] = {}
        
        # Aggregated metrics
        self._aggregated_metrics: dict[str, dict[str, Any]] = {}
        self._alert_rules: list[dict[str, Any]] = []
        
        # Configuration
        self._retention_period_hours = 24  # Keep 24 hours of detailed metrics
        self._aggregation_interval_seconds = 60  # Aggregate every minute
    
    def _get_logger(self) -> Any:
        """Get logger instance for this service."""
        return get_logger(__name__)
    
    async def record_metric(
        self,
        metric_name: str,
        value: float,
        tags: dict[str, str] | None = None,
        timestamp: str | None = None
    ) -> dict[str, Any]:
        """Record a metric value.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            tags: Optional metric tags
            timestamp: Optional timestamp
            
        Returns:
            Dictionary containing recording result
        """
        self.log_operation(
            "record_metric",
            metric_name=metric_name,
            value=value,
            tags=tags
        )
        
        try:
            # Record timestamp
            if timestamp is None:
                timestamp = datetime.now(UTC).isoformat()
            
            # Store gauge value
            self._gauges[metric_name] = value
            
            # Store with tags
            tag_key = self._get_tag_key(tags)
            if tag_key:
                self._gauges[f"{metric_name}.{tag_key}"] = value
            
            # Trigger aggregation if needed
            await self._trigger_aggregation(metric_name)
            
            return {
                "metric_name": metric_name,
                "value": value,
                "tags": tags or {},
                "timestamp": timestamp,
                "status": "recorded"
            }
            
        except Exception as exc:
            self._logger.error(f"Error recording metric {metric_name}: {str(exc)}")
            raise
    
    async def increment_counter(
        self,
        counter_name: str,
        tags: dict[str, str] | None = None,
        value: int = 1
    ) -> dict[str, Any]:
        """Increment a counter metric.
        
        Args:
            counter_name: Name of the counter
            tags: Optional counter tags
            value: Value to increment by
            
        Returns:
            Dictionary containing increment result
        """
        self.log_operation(
            "increment_counter",
            counter_name=counter_name,
            value=value,
            tags=tags
        )
        
        try:
            # Increment counter
            tag_key = self._get_tag_key(tags)
            self._counters[counter_name][tag_key] += value
            
            # Also increment without tags for total
            self._counters[counter_name][""] += value
            
            return {
                "counter_name": counter_name,
                "incremented_by": value,
                "tags": tags or {},
                "new_value": self._counters[counter_name][tag_key],
                "total_value": self._counters[counter_name][""],
                "timestamp": datetime.now(UTC).isoformat()
            }
            
        except Exception as exc:
            self._logger.error(f"Error incrementing counter {counter_name}: {str(exc)}")
            raise
    
    async def record_timing(
        self,
        operation_name: str,
        duration_ms: float,
        tags: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """Record operation timing.
        
        Args:
            operation_name: Name of the operation
            duration_ms: Duration in milliseconds
            tags: Optional operation tags
            
        Returns:
            Dictionary containing timing result
        """
        self.log_operation(
            "record_timing",
            operation_name=operation_name,
            duration_ms=duration_ms,
            tags=tags
        )
        
        try:
            # Record timing
            tag_key = self._get_tag_key(tags)
            timing_record = {
                "duration_ms": duration_ms,
                "tags": tags or {},
                "timestamp": datetime.now(UTC).isoformat()
            }
            
            self._timings[f"{operation_name}.{tag_key}"].append(timing_record)
            self._timings[operation_name].append(timing_record)  # Also store without tags
            
            # Trigger aggregation
            await self._trigger_aggregation(f"{operation_name}_timing")
            
            return {
                "operation_name": operation_name,
                "duration_ms": duration_ms,
                "tags": tags or {},
                "timestamp": timing_record["timestamp"],
                "status": "recorded"
            }
            
        except Exception as exc:
            self._logger.error(f"Error recording timing for {operation_name}: {str(exc)}")
            raise
    
    async def get_metrics(
        self,
        metric_names: list[str] | None = None,
        time_range: Tuple[str, str] | None = None,
        tags: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """Get metrics data with optional filtering.
        
        Args:
            metric_names: Optional list of metric names
            time_range: Optional time range filter
            tags: Optional tag filters
            
        Returns:
            Dictionary containing requested metrics
        """
        self.log_operation("get_metrics")
        
        try:
            result = {
                "counters": self._get_filtered_counters(metric_names, tags),
                "timings": self._get_filtered_timings(metric_names, tags, time_range),
                "gauges": self._get_filtered_gauges(metric_names, tags),
                "aggregated": self._get_filtered_aggregated_metrics(metric_names, time_range),
                "generated_at": datetime.now(UTC).isoformat()
            }
            
            return result
            
        except Exception as exc:
            self._logger.error(f"Error getting metrics: {str(exc)}")
            raise
    
    async def get_aggregated_metrics(
        self,
        metric_name: str,
        aggregation: str = "avg",
        time_range: Tuple[str, str] | None = None
    ) -> dict[str, Any]:
        """Get aggregated metrics for a specific metric.
        
        Args:
            metric_name: Name of the metric
            aggregation: Aggregation type (avg, sum, min, max, p50, p95, p99)
            time_range: Optional time range
            
        Returns:
            Dictionary containing aggregated metrics
        """
        self.log_operation(
            "get_aggregated_metrics",
            metric_name=metric_name,
            aggregation=aggregation
        )
        
        try:
            # Get timing data for aggregation
            timing_data = self._get_timing_data_for_metric(metric_name, time_range)
            
            if not timing_data:
                return {
                    "metric_name": metric_name,
                    "aggregation": aggregation,
                    "value": None,
                    "sample_count": 0,
                    "time_range": time_range
                }
            
            # Extract duration values
            durations = [record["duration_ms"] for record in timing_data]
            
            # Calculate aggregation
            if aggregation == "avg":
                value = sum(durations) / len(durations)
            elif aggregation == "sum":
                value = sum(durations)
            elif aggregation == "min":
                value = min(durations)
            elif aggregation == "max":
                value = max(durations)
            elif aggregation == "p50":
                value = self._calculate_percentile(durations, 50)
            elif aggregation == "p95":
                value = self._calculate_percentile(durations, 95)
            elif aggregation == "p99":
                value = self._calculate_percentile(durations, 99)
            else:
                raise ValueError(f"Unsupported aggregation: {aggregation}")
            
            return {
                "metric_name": metric_name,
                "aggregation": aggregation,
                "value": round(value, 2),
                "sample_count": len(durations),
                "time_range": time_range,
                "calculated_at": datetime.now(UTC).isoformat()
            }
            
        except Exception as exc:
            self._logger.error(f"Error calculating aggregated metrics for {metric_name}: {str(exc)}")
            raise
    
    async def create_dashboard(
        self,
        dashboard_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a metrics dashboard configuration.
        
        Args:
            dashboard_config: Dashboard configuration
            
        Returns:
            Dictionary containing dashboard creation result
        """
        self.log_operation("create_dashboard")
        
        try:
            # Validate dashboard configuration
            required_fields = ["name", "widgets"]
            for field in required_fields:
                if field not in dashboard_config:
                    raise ValueError(f"Missing required field: {field}")
            
            # Generate dashboard ID
            dashboard_id = f"dashboard-{int(time.time())}"
            
            # Process widgets
            processed_widgets = []
            for widget in dashboard_config.get("widgets", []):
                processed_widget = await self._process_dashboard_widget(widget)
                processed_widgets.append(processed_widget)
            
            dashboard = {
                "id": dashboard_id,
                "name": dashboard_config["name"],
                "description": dashboard_config.get("description", ""),
                "widgets": processed_widgets,
                "created_at": datetime.now(UTC).isoformat(),
                "status": "active"
            }
            
            # Store dashboard configuration
            self._aggregated_metrics[f"dashboard_{dashboard_id}"] = dashboard
            
            return {
                "dashboard_id": dashboard_id,
                "name": dashboard_config["name"],
                "widget_count": len(processed_widgets),
                "status": "created",
                "created_at": dashboard.now(UTC).isoformat()
            }
            
        except Exception as exc:
            self._logger.error(f"Error creating dashboard: {str(exc)}")
            raise
    
    async def get_alert_rules(self) -> list[dict[str, Any]]:
        """Get configured alert rules.
        
        Returns:
            List of alert rule configurations
        """
        self.log_operation("get_alert_rules")
        
        try:
            return self._alert_rules.copy()
            
        except Exception as exc:
            self._logger.error(f"Error getting alert rules: {str(exc)}")
            raise
    
    async def create_alert_rule(
        self,
        rule_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Create an alert rule.
        
        Args:
            rule_config: Alert rule configuration
            
        Returns:
            Dictionary containing alert rule creation result
        """
        self.log_operation("create_alert_rule")
        
        try:
            # Validate rule configuration
            required_fields = ["name", "metric_name", "condition", "threshold", "action"]
            for field in required_fields:
                if field not in rule_config:
                    raise ValueError(f"Missing required field: {field}")
            
            # Generate rule ID
            rule_id = f"rule-{int(time.time())}"
            
            alert_rule = {
                "id": rule_id,
                "name": rule_config["name"],
                "metric_name": rule_config["metric_name"],
                "condition": rule_config["condition"],
                "threshold": rule_config["threshold"],
                "action": rule_config["action"],
                "enabled": rule_config.get("enabled", True),
                "created_at": datetime.now(UTC).isoformat(),
                "last_triggered": None
            }
            
            self._alert_rules.append(alert_rule)
            
            return {
                "rule_id": rule_id,
                "name": rule_config["name"],
                "status": "created",
                "created_at": alert_rule["created_at"]
            }
            
        except Exception as exc:
            self._logger.error(f"Error creating alert rule: {str(exc)}")
            raise
    
    # Helper methods
    
    def _get_tag_key(self, tags: dict[str, str] | None) -> str:
        """Generate tag key from tags dictionary."""
        if not tags:
            return ""
        
        # Sort tags for consistent key generation
        sorted_tags = sorted(tags.items())
        tag_key = ".".join([f"{k}:{v}" for k, v in sorted_tags])
        
        return tag_key
    
    async def _trigger_aggregation(self, metric_name: str) -> None:
        """Trigger aggregation for a metric."""
        # In a real implementation, this would run in background
        # For now, we'll do immediate aggregation
        pass
    
    def _get_filtered_counters(self, metric_names: list[str] | None, tags: dict[str, str] | None) -> dict[str, Any]:
        """Get filtered counter metrics."""
        filtered_counters = {}
        
        for counter_name, counter_data in self._counters.items():
            if metric_names and counter_name not in metric_names:
                continue
            
            filtered_data = {}
            for tag_key, value in counter_data.items():
                if tags and tag_key and not self._tags_match(tag_key, tags):
                    continue
                filtered_data[tag_key or "untagged"] = value
            
            if filtered_data:
                filtered_counters[counter_name] = filtered_data
        
        return filtered_counters
    
    def _get_filtered_timings(self, metric_names: list[str] | None, tags: dict[str, str] | None, time_range: Tuple[str, str] | None) -> dict[str, Any]:
        """Get filtered timing metrics."""
        filtered_timings = {}
        
        for timing_name, timing_data in self._timings.items():
            if metric_names and not any(name in timing_name for name in metric_names):
                continue
            
            filtered_records = []
            for record in timing_data:
                # Filter by time range
                if time_range:
                    record_time = datetime.fromisoformat(record["timestamp"])
                    start_time = datetime.fromisoformat(time_range[0])
                    end_time = datetime.fromisoformat(time_range[1])
                    
                    if not (start_time <= record_time <= end_time):
                        continue
                
                # Filter by tags
                if tags and record.get("tags") and not self._tags_match("", record["tags"]):
                    continue
                
                filtered_records.append(record)
            
            if filtered_records:
                filtered_timings[timing_name] = list(filtered_records)
        
        return filtered_timings
    
    def _get_filtered_gauges(self, metric_names: list[str] | None, tags: dict[str, str] | None) -> dict[str, Any]:
        """Get filtered gauge metrics."""
        filtered_gauges = {}
        
        for gauge_name, gauge_value in self._gauges.items():
            if metric_names and gauge_name not in metric_names:
                continue
            
            # Check if gauge name contains tag information
            if "." in gauge_name:
                base_name, tag_part = gauge_name.rsplit(".", 1)
                
                if tags and not self._tags_match(tag_part, tags):
                    continue
                
                if base_name not in filtered_gauges:
                    filtered_gauges[base_name] = {}
                
                filtered_gauges[base_name][tag_part or "untagged"] = gauge_value
            else:
                filtered_gauges[gauge_name] = gauge_value
        
        return filtered_gauges
    
    def _get_filtered_aggregated_metrics(self, metric_names: list[str] | None, time_range: Tuple[str, str] | None) -> dict[str, Any]:
        """Get filtered aggregated metrics."""
        filtered_aggregated = {}
        
        for agg_name, agg_data in self._aggregated_metrics.items():
            if metric_names and not any(name in agg_name for name in metric_names):
                continue
            
            # Filter by time range if specified
            if time_range and "created_at" in agg_data:
                agg_time = datetime.fromisoformat(agg_data["created_at"])
                start_time = datetime.fromisoformat(time_range[0])
                end_time = datetime.fromisoformat(time_range[1])
                
                if not (start_time <= agg_time <= end_time):
                    continue
            
            filtered_aggregated[agg_name] = agg_data
        
        return filtered_aggregated
    
    def _get_timing_data_for_metric(self, metric_name: str, time_range: Tuple[str, str] | None) -> list[dict[str, Any]]:
        """Get timing data for a specific metric."""
        timing_data = self._timings.get(metric_name, deque())
        
        if not time_range:
            return list(timing_data)
        
        # Filter by time range
        start_time = datetime.fromisoformat(time_range[0])
        end_time = datetime.fromisoformat(time_range[1])
        
        filtered_data = [
            record for record in timing_data
            if start_time <= datetime.fromisoformat(record["timestamp"]) <= end_time
        ]
        
        return filtered_data
    
    def _calculate_percentile(self, values: list[float], percentile: int) -> float:
        """Calculate percentile value."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int((percentile / 100) * len(sorted_values))
        
        if index >= len(sorted_values):
            index = len(sorted_values) - 1
        
        return sorted_values[index]
    
    def _tags_match(self, tag_key: str, required_tags: dict[str, str]) -> bool:
        """Check if tag key matches required tags."""
        if not tag_key or not required_tags:
            return True
        
        # Parse tag key into individual tag pairs
        tag_pairs = [pair.split(":") for pair in tag_key.split(".") if pair]
        tag_dict = dict(pair.split(":") for pair in tag_pairs if len(pair.split(":")) == 2)
        
        # Check if all required tags are present
        for req_key, req_value in required_tags.items():
            if tag_dict.get(req_key) != req_value:
                return False
        
        return True
    
    async def _process_dashboard_widget(self, widget: dict[str, Any]) -> dict[str, Any]:
        """Process dashboard widget configuration."""
        widget_type = widget.get("type", "metric")
        
        if widget_type == "metric":
            return {
                "type": "metric",
                "metric_name": widget.get("metric_name"),
                "title": widget.get("title"),
                "aggregation": widget.get("aggregation", "avg"),
                "refresh_interval": widget.get("refresh_interval", 30)
            }
        elif widget_type == "chart":
            return {
                "type": "chart",
                "chart_type": widget.get("chart_type", "line"),
                "metrics": widget.get("metrics", []),
                "title": widget.get("title"),
                "time_range": widget.get("time_range", "1h")
            }
        elif widget_type == "table":
            return {
                "type": "table",
                "metrics": widget.get("metrics", []),
                "title": widget.get("title"),
                "limit": widget.get("limit", 10)
            }
        else:
            return {
                "type": widget_type,
                "title": widget.get("title", "Unknown Widget"),
                "error": f"Unsupported widget type: {widget_type}"
            }
