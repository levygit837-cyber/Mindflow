"""Interface definitions for API controllers.

This module defines contracts for all API controller operations including
agent interactions, session management, orchestration, providers, and memory.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from mindflow_backend.schemas.api.requests import (
    AgentChatRequest,
    MemorySearchRequest,
    OrchestrationRequest,
    SessionCreateRequest,
    SessionUpdateRequest,
)
from mindflow_backend.schemas.api.responses import (
    AgentResponse,
    MemorySearchResponse,
    OrchestrationResponse,
    SessionResponse,
)


@runtime_checkable
class BaseControllerInterface(Protocol):
    """Base interface for all controllers."""
    
    def handle_error(self, error: Exception, context: str = "") -> Any:
        """Handle errors consistently."""
        ...
    
    def validate_session_id(self, session_id: str | None) -> str:
        """Validate session ID."""
        ...
    
    def log_request(self, request: Any, operation: str, **kwargs) -> None:
        """Log API requests."""
        ...


@runtime_checkable
class AgentControllerInterface(Protocol):
    """Interface for agent controller operations."""
    
    async def chat_stream(self, request: AgentChatRequest) -> Any:
        """Handle streaming agent chat."""
        ...
    
    async def get_capabilities(self, agent_type: str) -> AgentResponse:
        """Get agent capabilities."""
        ...


@runtime_checkable
class SessionControllerInterface(Protocol):
    """Interface for session controller operations."""
    
    async def create_session(self, request: SessionCreateRequest) -> SessionResponse:
        """Create a new session."""
        ...
    
    async def get_session(self, session_id: str) -> SessionResponse:
        """Get session details."""
        ...
    
    async def list_sessions(self, limit: int = 50, offset: int = 0) -> list[SessionResponse]:
        """List sessions."""
        ...
    
    async def update_session(self, session_id: str, request: SessionUpdateRequest) -> SessionResponse:
        """Update session."""
        ...
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session."""
        ...


@runtime_checkable
class OrchestrationControllerInterface(Protocol):
    """Interface for orchestration controller operations."""
    
    async def decompose_task(self, request: OrchestrationRequest) -> OrchestrationResponse:
        """Decompose a task."""
        ...
    
    async def execute_dag(self, dag_id: str, session_id: str | None = None) -> OrchestrationResponse:
        """Execute a DAG."""
        ...
    
    async def get_execution_status(self, execution_id: str) -> OrchestrationResponse:
        """Get execution status."""
        ...


@runtime_checkable
class ProviderControllerInterface(Protocol):
    """Interface for provider controller operations."""
    
    async def list_providers(self) -> list[Any]:
        """List available providers."""
        ...
    
    async def test_provider(self, provider_id: str) -> Any:
        """Test provider connection."""
        ...
    
    async def get_config(self, provider_id: str) -> Any:
        """Get provider configuration."""
        ...


@runtime_checkable
class MemoryControllerInterface(Protocol):
    """Interface for memory controller operations."""
    
    async def search_memory(self, request: MemorySearchRequest) -> MemorySearchResponse:
        """Search memory/context."""
        ...
    
    async def get_agent_memory(self, agent_id: str, session_id: str) -> Any:
        """Get agent memory."""
        ...
    
    async def create_summary(self, agent_id: str, session_id: str, window_range: tuple[int, int]) -> Any:
        """Create memory summary."""
        ...
