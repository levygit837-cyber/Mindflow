"""gRPC interfaces for OmniMind backend.

Defines contracts for gRPC client and server implementations
to ensure loose coupling and testability.
"""

from .client import GrpcClient
from .server import GrpcServer

__all__ = [
    "GrpcClient",
    "GrpcServer",
]
