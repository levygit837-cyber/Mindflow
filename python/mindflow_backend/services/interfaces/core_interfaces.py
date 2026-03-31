"""Core service interfaces for MindFlow backend.

DEPRECATED: This module has been moved to mindflow_backend.interfaces.services.core
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.interfaces.services import CoreServiceInterface, AgentServiceInterface, SessionServiceInterface, MemoryServiceInterface, ProviderServiceInterface
"""

# Forward compatibility aliases - import from new location
from mindflow_backend.interfaces.services.core import (
    AgentServiceInterface,
    CoreServiceInterface,
    MemoryServiceInterface,
    ProviderServiceInterface,
    SessionServiceInterface,
)

# Maintain backward compatibility
__all__ = [
    "CoreServiceInterface",
    "AgentServiceInterface",
    "SessionServiceInterface",
    "MemoryServiceInterface",
    "ProviderServiceInterface",
]
