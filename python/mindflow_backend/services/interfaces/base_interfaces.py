"""Base service interfaces for MindFlow backend.

DEPRECATED: This module has been moved to mindflow_backend.interfaces.services.base
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.interfaces.services import BaseServiceInterface, ServiceLifecycleInterface, CacheableServiceInterface, ConfigurableServiceInterface, BaseAbstractService
"""

# Forward compatibility aliases - import from new location
from mindflow_backend.interfaces.services.base import (
    BaseAbstractService,
    BaseServiceInterface,
    CacheableServiceInterface,
    ConfigurableServiceInterface,
    ServiceLifecycleInterface,
)

# Maintain backward compatibility
__all__ = [
    "BaseServiceInterface",
    "ServiceLifecycleInterface",
    "CacheableServiceInterface",
    "ConfigurableServiceInterface",
    "BaseAbstractService",
]
