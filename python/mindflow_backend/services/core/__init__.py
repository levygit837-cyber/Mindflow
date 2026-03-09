"""Core services for MindFlow backend.

This module provides fundamental business services for agents, sessions,
memory management, and provider configuration.
"""

from __future__ import annotations

# Factory functions for core services
def get_agent_service():
    """Factory function for AgentService."""
    from mindflow_backend.services.core.agent_service import AgentService
    return AgentService()

def get_session_service():
    """Factory function for SessionService."""
    from mindflow_backend.services.core.session_service import SessionService
    return SessionService()

def get_memory_service():
    """Factory function for MemoryService - now imported from memory module."""
    from mindflow_backend.memory import get_memory_service
    return get_memory_service()

def get_provider_service():
    """Factory function for ProviderService."""
    from mindflow_backend.services.core.provider_service import ProviderService
    return ProviderService()

def get_pinchtab_service():
    """Factory function for PinchTabService."""
    from mindflow_backend.services.core.pinchtab_service import PinchTabService
    return PinchTabService()

# Public exports
__all__ = [
    "get_agent_service",
    "get_session_service", 
    "get_memory_service",
    "get_provider_service",
    "get_pinchtab_service",
]
