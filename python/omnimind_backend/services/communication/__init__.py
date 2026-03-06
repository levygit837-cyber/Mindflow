"""Communication services for OmniMind backend.

This module provides services for gRPC communication and 
real-time event streaming.
"""

from __future__ import annotations

# Factory functions for communication services
def get_grpc_service():
    """Factory function for GrpcService."""
    from omnimind_backend.services.communication.grpc_service import GrpcService
    return GrpcService()

def get_streaming_service():
    """Factory function for StreamingService."""
    from omnimind_backend.services.communication.streaming_service import StreamingService
    return StreamingService()

# Public exports
__all__ = [
    "get_grpc_service",
    "get_streaming_service",
]
