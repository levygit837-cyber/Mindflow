"""Core service interfaces for MindFlow backend.

This module defines interfaces for fundamental business services including
agents, sessions, memory management, and provider configuration.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from mindflow_backend.schemas.core.common import LLMProvider


@runtime_checkable
class CoreServiceInterface(Protocol):
    """Interface for core business operations."""
    
    async def process_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Process core business request."""
        ...
    
    async def validate_request(self, request: dict[str, Any]) -> bool:
        """Validate core request."""
        ...
    
    async def get_service_status(self) -> dict[str, Any]:
        """Get core service status."""
        ...
    
    async def handle_error(self, error: Exception, context: str) -> dict[str, Any]:
        """Handle core service errors."""
        ...


@runtime_checkable
class AgentServiceInterface(Protocol):
    """Interface for agent service operations."""
    
    async def process_agent_request(
        self,
        message: str,
        agent_type: str | None = None,
        provider: LLMProvider | None = None,
        model: str | None = None,
        session_id: str | None = None,
        orchestrate: bool = False
    ) -> dict[str, Any]:
        """Process an agent request."""
        ...
    
    async def get_agent_capabilities(self, agent_type: str) -> dict[str, Any]:
        """Get agent capabilities."""
        ...
    
    async def validate_agent_request(self, request_data: dict[str, Any]) -> bool:
        """Validate agent request."""
        ...
    
    async def list_available_agents(self) -> list[dict[str, Any]]:
        """List all available agents."""
        ...
    
    async def get_agent_status(self, agent_type: str) -> dict[str, Any]:
        """Get agent status and health."""
        ...


@runtime_checkable
class SessionServiceInterface(Protocol):
    """Interface for session service operations."""
    
    async def create_session(
        self,
        title: str | None = None,
        user_id: str | None = None
    ) -> dict[str, Any]:
        """Create a new session."""
        ...
    
    async def get_session(self, session_id: str) -> dict[str, Any]:
        """Get session details."""
        ...
    
    async def list_sessions(
        self,
        limit: int = 50,
        offset: int = 0,
        user_id: str | None = None
    ) -> list[dict[str, Any]]:
        """List sessions."""
        ...
    
    async def update_session(
        self,
        session_id: str,
        title: str | None = None
    ) -> dict[str, Any]:
        """Update session."""
        ...
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session."""
        ...
    
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        provider: str | None = None,
        model: str | None = None
    ) -> dict[str, Any]:
        """Add message to session."""
        ...
    
    async def get_session_messages(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> list[dict[str, Any]]:
        """Get session messages."""
        ...
    
    async def get_session_context(self, session_id: str) -> dict[str, Any]:
        """Get session context and metadata."""
        ...


@runtime_checkable
class MemoryServiceInterface(Protocol):
    """Interface for memory service operations."""
    
    async def get_agent_memory(
        self,
        agent_id: str,
        session_id: str,
        token_limit: int | None = None
    ) -> dict[str, Any]:
        """Get agent memory."""
        ...
    
    async def add_memory_event(
        self,
        agent_id: str,
        session_id: str,
        role: str,
        content: str,
        token_count: int,
        source_message_id: int | None = None
    ) -> dict[str, Any]:
        """Add memory event."""
        ...
    
    async def get_context_window(
        self,
        session_id: str,
        window_start: int,
        window_end: int
    ) -> dict[str, Any]:
        """Get context window."""
        ...
    
    async def search_semantic_context(
        self,
        query: str,
        session_id: str,
        top_k: int = 5,
        min_score: float = 0.3
    ) -> list[dict[str, Any]]:
        """Search semantic context."""
        ...
    
    async def create_memory_summary(
        self,
        agent_id: str,
        session_id: str,
        window_range: tuple[int, int]
    ) -> dict[str, Any]:
        """Create memory summary."""
        ...
    
    async def get_memory_windows(
        self,
        agent_id: str,
        session_id: str
    ) -> list[dict[str, Any]]:
        """Get memory windows."""
        ...
    
    async def update_memory_cursor(
        self,
        agent_id: str,
        session_id: str,
        token_total: int,
        tokens_since_summary: int
    ) -> dict[str, Any]:
        """Update memory cursor."""
        ...
    
    async def retrieve_context_for_query(
        self,
        query: str,
        session_id: str,
        agent_id: str
    ) -> dict[str, Any]:
        """Retrieve relevant context for a query."""
        ...


@runtime_checkable
class ProviderServiceInterface(Protocol):
    """Interface for provider service operations."""
    
    async def list_providers(self) -> list[dict[str, Any]]:
        """List providers."""
        ...
    
    async def get_provider_models(self, provider_id: str) -> list[dict[str, Any]]:
        """Get provider models."""
        ...
    
    async def test_provider_connection(self, provider_id: str) -> dict[str, Any]:
        """Test provider connection."""
        ...
    
    async def get_provider_config(self, provider_id: str) -> dict[str, Any]:
        """Get provider config."""
        ...
    
    async def update_provider_config(
        self,
        provider_id: str,
        config: dict[str, Any]
    ) -> dict[str, Any]:
        """Update provider config."""
        ...
    
    async def get_fallback_chain(self) -> list[str]:
        """Get fallback chain."""
        ...
    
    async def handle_provider_failure(
        self,
        provider_id: str,
        error: str
    ) -> dict[str, Any]:
        """Handle provider failure."""
        ...
    
    async def get_optimal_provider(
        self,
        task_type: str,
        model_requirements: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Get optimal provider for task."""
        ...
    
    async def validate_provider_config(self, config: dict[str, Any]) -> bool:
        """Validate provider configuration."""
        ...
