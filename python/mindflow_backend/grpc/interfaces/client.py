"""gRPC client interface contract.

Defines the contract for gRPC client implementations to ensure
consistent behavior across different client implementations.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Protocol, runtime_checkable

from mindflow_backend.schemas.chat.agent import AgentChatRequest, StreamEvent


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
