"""Monitoring service interfaces for MindFlow backend.

This module defines interfaces for health checks, metrics collection,
and session review/optimization.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Any


@runtime_checkable
class HealthServiceInterface(Protocol):
    """Interface for health check operations."""
    
    async def check_service_health(self, service_name: str) -> dict[str, Any]:
        """Check health of specific service."""
        ...
    
    async def check_system_health(self) -> dict[str, Any]:
        """Check overall system health."""
        ...
    
    async def check_database_health(self) -> dict[str, Any]:
        """Check database connectivity and health."""
        ...
    
    async def check_external_service_health(self, service_url: str) -> dict[str, Any]:
        """Check external service health."""
        ...
    
    async def get_health_metrics(self) -> dict[str, Any]:
        """Get comprehensive health metrics."""
        ...
    
    async def register_health_check(
        self,
        check_name: str,
        check_function: callable,
        interval: int = 60
    ) -> dict[str, Any]:
        """Register custom health check."""
        ...
    
    async def get_health_history(
        self,
        service_name: str | None = None,
        time_range: tuple[str, str] | None = None
    ) -> list[dict[str, Any]]:
        """Get health check history."""
        ...


@runtime_checkable
class MetricsServiceInterface(Protocol):
    """Interface for metrics collection operations."""
    
    async def record_metric(
        self,
        metric_name: str,
        value: float,
        tags: dict[str, str] | None = None,
        timestamp: str | None = None
    ) -> dict[str, Any]:
        """Record a metric value."""
        ...
    
    async def increment_counter(
        self,
        counter_name: str,
        tags: dict[str, str] | None = None,
        value: int = 1
    ) -> dict[str, Any]:
        """Increment a counter metric."""
        ...
    
    async def record_timing(
        self,
        operation_name: str,
        duration_ms: float,
        tags: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """Record operation timing."""
        ...
    
    async def get_metrics(
        self,
        metric_names: list[str] | None = None,
        time_range: tuple[str, str] | None = None,
        tags: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """Get metrics data."""
        ...
    
    async def get_aggregated_metrics(
        self,
        metric_name: str,
        aggregation: str = "avg",
        time_range: tuple[str, str] | None = None
    ) -> dict[str, Any]:
        """Get aggregated metrics."""
        ...
    
    async def create_dashboard(
        self,
        dashboard_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Create metrics dashboard."""
        ...
    
    async def get_alert_rules(self) -> list[dict[str, Any]]:
        """Get alert rules."""
        ...
    
    async def create_alert_rule(
        self,
        rule_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Create alert rule."""
        ...


@runtime_checkable
class ReviewServiceInterface(Protocol):
    """Interface for session review and optimization operations."""
    
    async def initialize_session_review(
        self,
        session_id: str,
        window_size: str = "medium",
        custom_tokens: int | None = None,
        trigger_threshold: int | None = None
    ) -> dict[str, Any]:
        """Initialize session review configuration."""
        ...
    
    async def update_token_count(
        self,
        session_id: str,
        additional_tokens: int
    ) -> dict[str, Any]:
        """Update token count and check if review should be triggered."""
        ...
    
    async def trigger_review(
        self,
        session_id: str,
        review_type: str = "automatic"
    ) -> dict[str, Any]:
        """Trigger session review."""
        ...
    
    async def get_review_status(self, session_id: str) -> dict[str, Any]:
        """Get review status for session."""
        ...
    
    async def get_review_results(
        self,
        session_id: str,
        limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get review results for session."""
        ...
    
    async def optimize_session_context(
        self,
        session_id: str,
        optimization_strategy: str = "summary"
    ) -> dict[str, Any]:
        """Optimize session context based on review results."""
        ...
    
    async def get_review_statistics(
        self,
        time_range: tuple[str, str] | None = None
    ) -> dict[str, Any]:
        """Get review statistics."""
        ...
    
    async def create_review_schedule(
        self,
        schedule_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Create automated review schedule."""
        ...
