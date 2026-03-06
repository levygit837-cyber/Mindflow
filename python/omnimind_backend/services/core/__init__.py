"""Core services for OmniMind backend.

This module provides fundamental business services for agents, sessions,
memory management, and provider configuration.
"""

from __future__ import annotations

# Factory functions for core services
def get_agent_service():
    """Factory function for AgentService."""
    from omnimind_backend.services.core.agent_service import AgentService
    return AgentService()

def get_session_service():
    """Factory function for SessionService."""
    from omnimind_backend.services.core.session_service import SessionService
    return SessionService()

def get_memory_service():
    """Factory function for MemoryService."""
    from omnimind_backend.services.core.memory_service import MemoryService
    return MemoryService()

def get_provider_service():
    """Factory function for ProviderService."""
    from omnimind_backend.services.core.provider_service import ProviderService
    return ProviderService()

# Public exports
__all__ = [
    "get_agent_service",
    "get_session_service", 
    "get_memory_service",
    "get_provider_service",
]
