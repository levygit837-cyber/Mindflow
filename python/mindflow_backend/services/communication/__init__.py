"""Communication services for MindFlow backend.

This module provides services for gRPC communication and 
real-time event streaming.
"""

from __future__ import annotations


# Factory functions for communication services
def get_grpc_service():
    """Factory function for GrpcService."""
    from mindflow_backend.services.communication.grpc_service import GrpcService
    return GrpcService()

def get_streaming_service():
    """Factory function for StreamingService."""
    from mindflow_backend.services.communication.streaming_service import StreamingService
    return StreamingService()

def get_agent_runtime_service():
    """Factory function for AgentRuntimeService."""
    from mindflow_backend.services.communication.agent_runtime_service import AgentRuntimeService
    return AgentRuntimeService()

# Public exports
__all__ = [
    "get_grpc_service",
    "get_streaming_service",
    "get_agent_runtime_service",
]
