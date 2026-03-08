"""Communication service interfaces for MindFlow backend.

DEPRECATED: This module has been moved to mindflow_backend.interfaces.services.communication
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.interfaces.services import CommunicationServiceInterface, GrpcServiceInterface, StreamingServiceInterface
"""

# Forward compatibility aliases - import from new location
from mindflow_backend.interfaces.services.communication import (
    CommunicationServiceInterface,
    GrpcServiceInterface,
    StreamingServiceInterface,
)

# Maintain backward compatibility
__all__ = [
    "CommunicationServiceInterface",
    "GrpcServiceInterface",
    "StreamingServiceInterface",
]
