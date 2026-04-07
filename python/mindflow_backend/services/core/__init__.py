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
    "get_shell_tab_service",
    "get_session_runtime_state_service",
    "get_worktree_service",
]
