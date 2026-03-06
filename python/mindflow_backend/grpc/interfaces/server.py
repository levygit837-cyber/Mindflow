"""gRPC server interface contract.

Defines the contract for gRPC server implementations to ensure
consistent behavior across different server implementations.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class GrpcServer(Protocol):
    """Contract for gRPC server implementations."""
    
    async def start(self) -> None:
        """Start the gRPC server."""
        ...
    
    async def stop(self, grace_period_seconds: float = 30.0) -> None:
        """Stop the gRPC server with graceful shutdown."""
        ...
    
    def is_running(self) -> bool:
        """Check if server is currently running."""
        ...
    
    def get_port(self) -> int:
        """Get the port the server is listening on."""
        ...
    
    def get_host(self) -> str:
        """Get the host the server is bound to."""
        ...
    
    async def wait_for_termination(self) -> None:
        """Wait for server termination."""
        ...
    
    def add_interceptor(self, interceptor) -> None:
        """Add a server interceptor."""
        ...
    
    def add_service(self, service) -> None:
        """Add a service to the server."""
        ...
