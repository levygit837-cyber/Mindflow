"""Orchestration service for managing task decomposition and agent coordination.

DEPRECATED: This module has been moved to mindflow_backend.services.orchestration.orchestration_service
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.services import get_orchestration_service
"""

# Forward compatibility alias - import from centralized location
from mindflow_backend.services.orchestration.orchestration_service import OrchestrationService

# Maintain backward compatibility
__all__ = ["OrchestrationService"]
