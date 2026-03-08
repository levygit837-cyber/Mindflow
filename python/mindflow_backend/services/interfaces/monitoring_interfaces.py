"""Monitoring service interfaces for MindFlow backend.

DEPRECATED: This module has been moved to mindflow_backend.interfaces.services.monitoring
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.interfaces.services import MonitoringServiceInterface, HealthServiceInterface, MetricsServiceInterface, ReviewServiceInterface
"""

# Forward compatibility aliases - import from new location
from mindflow_backend.interfaces.services.monitoring import (
    MonitoringServiceInterface,
    HealthServiceInterface,
    MetricsServiceInterface,
    ReviewServiceInterface,
)

# Maintain backward compatibility
__all__ = [
    "MonitoringServiceInterface",
    "HealthServiceInterface",
    "MetricsServiceInterface",
    "ReviewServiceInterface",
]
