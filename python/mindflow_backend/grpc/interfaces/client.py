"""gRPC client interface contract.

DEPRECATED: This module has been moved to mindflow_backend.interfaces.infrastructure.grpc
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.interfaces.infrastructure import GrpcClient, GrpcServer, GrpcConnectionManager
"""

# Forward compatibility aliases - import from new location
from mindflow_backend.interfaces.infrastructure.grpc import (
    GrpcClient,
    GrpcConnectionManager,
    GrpcServer,
)

# Maintain backward compatibility
__all__ = [
    "GrpcClient",
    "GrpcServer", 
    "GrpcConnectionManager",
]
