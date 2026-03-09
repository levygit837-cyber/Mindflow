"""Monitoring exceptions.

Exceptions for metrics collection, health checks,
and monitoring system failures.
"""

from __future__ import annotations

from mindflow_backend.exceptions.base.core_new import InfrastructureError


class MonitoringError(InfrastructureError):
    """Monitoring system failure."""
    
    def __init__(
        self,
        message: str,
        *,
        monitoring_system: str | None = None,
        metric_name: str | None = None,
        operation: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            service="monitoring",
            operation=operation,
            component="infrastructure",
            **kwargs
        )
        self.monitoring_system = monitoring_system
        self.metric_name = metric_name
