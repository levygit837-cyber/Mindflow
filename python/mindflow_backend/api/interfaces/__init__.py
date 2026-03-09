"""API interfaces for controllers and services.

DEPRECATED: This module has been moved to mindflow_backend.interfaces.api.legacy
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.interfaces.api import ControllerInterface, ServiceInterface
"""

# Forward compatibility aliases - import from new location
from mindflow_backend.interfaces.api.legacy import (
    ControllerInterface,
    ServiceInterface,
)

# Maintain backward compatibility
__all__ = [
    "ControllerInterface",
    "ServiceInterface",
]
