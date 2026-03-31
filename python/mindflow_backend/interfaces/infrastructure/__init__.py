"""Infrastructure interfaces for MindFlow backend.

Provides contracts and protocols for infrastructure components including
gRPC, databases, caching, message queues, and storage systems.
"""

from .grpc import GrpcClient, GrpcConnectionManager, GrpcServer

__all__ = [
    # gRPC interfaces
    "GrpcClient",
    "GrpcServer", 
    "GrpcConnectionManager",
]
