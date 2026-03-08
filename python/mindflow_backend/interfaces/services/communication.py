"""Communication service interfaces for MindFlow backend.

This module defines interfaces for gRPC communication and 
real-time event streaming.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Any
from collections.abc import AsyncGenerator


@runtime_checkable
class CommunicationServiceInterface(Protocol):
    """Interface for service communication operations."""
    
    async def send_message(self, target: str, message: dict[str, Any]) -> dict[str, Any]:
        """Send message to another service."""
        ...
    
    async def receive_message(self, timeout: float | None = None) -> dict[str, Any]:
        """Receive message from another service."""
        ...
    
    async def broadcast_message(self, message: dict[str, Any]) -> dict[str, Any]:
        """Broadcast message to all connected services."""
        ...
    
    async def get_connection_status(self) -> dict[str, Any]:
        """Get connection status."""
        ...
    
    async def establish_connection(self, target: str, config: dict[str, Any]) -> dict[str, Any]:
        """Establish connection to target service."""
        ...
    
    async def close_connection(self, target: str) -> dict[str, Any]:
        """Close connection to target service."""
        ...


@runtime_checkable
class GrpcServiceInterface(Protocol):
    """Interface for gRPC communication operations."""
    
    async def start_server(self, host: str = "localhost", port: int = 50051) -> dict[str, Any]:
        """Start gRPC server."""
        ...
    
    async def stop_server(self) -> dict[str, Any]:
        """Stop gRPC server."""
        ...
    
    async def handle_stream_chat(
        self,
        request: dict[str, Any]
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Handle streaming chat requests."""
        ...
    
    async def get_server_status(self) -> dict[str, Any]:
        """Get gRPC server status."""
        ...
    
    async def register_service(
        self,
        service_name: str,
        service_implementation: Any
    ) -> dict[str, Any]:
        """Register gRPC service."""
        ...
    
    async def get_connection_metrics(self) -> dict[str, Any]:
        """Get connection metrics."""
        ...
    
    async def configure_interceptors(
        self,
        interceptors: list[Any]
    ) -> dict[str, Any]:
        """Configure gRPC interceptors."""
        ...
    
    async def test_connection(self, endpoint: str) -> dict[str, Any]:
        """Test gRPC connection."""
        ...


@runtime_checkable
class StreamingServiceInterface(Protocol):
    """Interface for real-time event streaming operations."""
    
    async def create_stream(
        self,
        stream_id: str,
        stream_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Create new event stream."""
        ...
    
    async def send_event(
        self,
        stream_id: str,
        event: dict[str, Any]
    ) -> dict[str, Any]:
        """Send event to stream."""
        ...
    
    async def subscribe_to_stream(
        self,
        stream_id: str,
        subscriber_id: str
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Subscribe to event stream."""
        ...
    
    async def close_stream(self, stream_id: str) -> dict[str, Any]:
        """Close event stream."""
        ...
    
    async def get_stream_status(self, stream_id: str) -> dict[str, Any]:
        """Get stream status."""
        ...
    
    async def list_active_streams(self) -> list[dict[str, Any]]:
        """List all active streams."""
        ...
    
    async def create_broadcast_channel(
        self,
        channel_name: str,
        channel_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Create broadcast channel for multiple subscribers."""
        ...
    
    async def broadcast_event(
        self,
        channel_name: str,
        event: dict[str, Any]
    ) -> dict[str, Any]:
        """Broadcast event to all channel subscribers."""
        ...
    
    async def get_stream_metrics(self, stream_id: str) -> dict[str, Any]:
        """Get stream performance metrics."""
        ...
    
    async def configure_stream_security(
        self,
        stream_id: str,
        security_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Configure stream security settings."""
        ...
