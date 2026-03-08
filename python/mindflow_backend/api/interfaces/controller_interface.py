"""Interface definitions for API controllers.

DEPRECATED: This module has been moved to mindflow_backend.interfaces.api.controllers
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.interfaces.api import AgentControllerInterface, SessionControllerInterface, OrchestrationControllerInterface, ProviderControllerInterface, MemoryControllerInterface, BaseControllerInterface
"""

# Forward compatibility aliases - import from new location
from mindflow_backend.interfaces.api.controllers import (
    AgentControllerInterface,
    SessionControllerInterface,
    OrchestrationControllerInterface,
    ProviderControllerInterface,
    MemoryControllerInterface,
    BaseControllerInterface,
)

# Maintain backward compatibility
__all__ = [
    "AgentControllerInterface",
    "SessionControllerInterface",
    "OrchestrationControllerInterface",
    "ProviderControllerInterface",
    "MemoryControllerInterface",
    "BaseControllerInterface",
]
