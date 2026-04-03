"""Core services for MindFlow backend.

This module provides fundamental business services for agents, sessions,
memory management, and provider configuration.
"""

from __future__ import annotations

_pinchtab_service = None

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

    global _pinchtab_service
    if _pinchtab_service is None:
        _pinchtab_service = PinchTabService(get_pinchtab_fleet_service())
    return _pinchtab_service


_pinchtab_container_service = None
_pinchtab_browser_service = None
_pinchtab_fleet_service = None


def get_pinchtab_container_service():
    """Factory for the PinchTab docker container orchestrator."""
    global _pinchtab_container_service
    if _pinchtab_container_service is None:
        from mindflow_backend.services.core.pinchtab_container_service import (
            PinchTabContainerService,
        )

        _pinchtab_container_service = PinchTabContainerService()
    return _pinchtab_container_service


def get_pinchtab_browser_service():
    """Factory for the PinchTab HTTP client service."""
    global _pinchtab_browser_service
    if _pinchtab_browser_service is None:
        from mindflow_backend.services.core.pinchtab_browser_service import PinchTabBrowserService

        _pinchtab_browser_service = PinchTabBrowserService()
    return _pinchtab_browser_service


def get_pinchtab_fleet_service():
    """Factory for the session-scoped PinchTab fleet service."""
    global _pinchtab_fleet_service
    if _pinchtab_fleet_service is None:
        from mindflow_backend.services.core.pinchtab_fleet_service import PinchTabFleetService

        _pinchtab_fleet_service = PinchTabFleetService(
            container_orchestrator=get_pinchtab_container_service(),
            browser_service=get_pinchtab_browser_service(),
        )
    return _pinchtab_fleet_service


_shell_tab_service = None
_session_runtime_state_service = None
_worktree_service = None


def get_shell_tab_service():
    """Factory function for the session-scoped in-memory ShellTabService."""
    global _shell_tab_service
    if _shell_tab_service is None:
        from mindflow_backend.services.core.shell_tab_service import ShellTabService
        _shell_tab_service = ShellTabService()
    return _shell_tab_service


def get_session_runtime_state_service():
    """Factory function for the session runtime state persistence service."""
    global _session_runtime_state_service
    if _session_runtime_state_service is None:
        from mindflow_backend.services.core.session_runtime_state_service import (
            SessionRuntimeStateService,
        )

        _session_runtime_state_service = SessionRuntimeStateService()
    return _session_runtime_state_service


def get_worktree_service():
    """Factory function for the workspace isolation service."""
    global _worktree_service
    if _worktree_service is None:
        from mindflow_backend.services.core.worktree_service import WorktreeService

        _worktree_service = WorktreeService(
            session_runtime_state_service=get_session_runtime_state_service(),
        )
    return _worktree_service

# Public exports
__all__ = [
    "get_agent_service",
    "get_session_service", 
    "get_memory_service",
    "get_provider_service",
    "get_pinchtab_service",
    "get_pinchtab_container_service",
    "get_pinchtab_browser_service",
    "get_pinchtab_fleet_service",
    "get_shell_tab_service",
    "get_session_runtime_state_service",
    "get_worktree_service",
]
