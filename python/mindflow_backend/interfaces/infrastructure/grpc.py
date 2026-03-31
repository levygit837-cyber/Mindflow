"""gRPC infrastructure interfaces for MindFlow backend.

Defines contracts for gRPC client and server implementations to ensure
consistent behavior across different implementations.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Protocol, runtime_checkable

from mindflow_backend.schemas.chat.agent import StreamEvent


@runtime_checkable
class GrpcClient(Protocol):
    """Contract for gRPC client implementations."""
    
    async def connect(self) -> None:
        """Establish connection to gRPC server."""
        ...
    
    async def close(self) -> None:
        """Close gRPC connection and cleanup resources."""
        ...
    
    async def stream_chat(
        self,
        *,
        session_id: str,
        message: str,
        provider: str | None = None,
        model: str | None = None,
        run_id: str | None = None,
        orchestrate: bool = False,
        agent_type: str | None = None,
        debug_steps: bool = False,
        folder_path: str | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Stream chat response from gRPC server."""
        ...
    
    async def health_check(self) -> dict[str, str]:
        """Check health of gRPC server."""
        ...
    
    def is_connected(self) -> bool:
        """Check if client is connected to server."""
        ...
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


@runtime_checkable
class GrpcServer(Protocol):
    """Contract for gRPC server implementations."""
    
    async def start(self, host: str = "localhost", port: int = 50051) -> None:
        """Start gRPC server."""
        ...
    
    async def stop(self, grace_period: float = 30.0) -> None:
        """Stop gRPC server with grace period."""
        ...
    
    async def register_service(self, service_name: str, service_impl: Any) -> None:
        """Register gRPC service implementation."""
        ...
    
    async def get_server_info(self) -> dict[str, Any]:
        """Get server information and status."""
        ...
    
    def is_running(self) -> bool:
        """Check if server is running."""
        ...
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()


@runtime_checkable
class GrpcConnectionManager(Protocol):
    """Contract for gRPC connection management."""
    
    async def create_connection(self, endpoint: str, config: dict[str, Any]) -> GrpcClient:
        """Create new gRPC connection."""
        ...
    
    async def get_connection(self, connection_id: str) -> GrpcClient:
        """Get existing connection by ID."""
        ...
    
    async def close_connection(self, connection_id: str) -> None:
        """Close specific connection."""
        ...
    
    async def close_all_connections(self) -> None:
        """Close all active connections."""
        ...
    
    async def get_connection_stats(self) -> dict[str, Any]:
        """Get connection statistics."""
        ...
    
    async def health_check_all(self) -> dict[str, bool]:
        """Health check all connections."""
        ...
