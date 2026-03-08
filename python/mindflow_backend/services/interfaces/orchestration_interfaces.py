"""Orchestration service interfaces for MindFlow backend.

DEPRECATED: This module has been moved to mindflow_backend.interfaces.services.orchestration
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.interfaces.services import OrchestrationServiceInterface, TaskServiceInterface, RoutingServiceInterface
"""

# Forward compatibility aliases - import from new location
from mindflow_backend.interfaces.services.orchestration import (
    OrchestrationServiceInterface,
    TaskServiceInterface,
    RoutingServiceInterface,
)

# Maintain backward compatibility
__all__ = [
    "OrchestrationServiceInterface",
    "TaskServiceInterface",
    "RoutingServiceInterface",
]
