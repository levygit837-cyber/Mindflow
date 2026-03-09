"""Interface definitions for API services.

DEPRECATED: This module has been moved to mindflow_backend.interfaces.api.services
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.interfaces.api import AgentServiceInterface, SessionServiceInterface, OrchestrationServiceInterface, ProviderServiceInterface, MemoryServiceInterface, BaseServiceInterface
"""

# Forward compatibility aliases - import from new location
from mindflow_backend.interfaces.api.services import (
    AgentServiceInterface,
    SessionServiceInterface,
    OrchestrationServiceInterface,
    ProviderServiceInterface,
    MemoryServiceInterface,
    BaseServiceInterface,
)

# Maintain backward compatibility
__all__ = [
    "AgentServiceInterface",
    "SessionServiceInterface",
    "OrchestrationServiceInterface",
    "ProviderServiceInterface",
    "MemoryServiceInterface",
    "BaseServiceInterface",
]
