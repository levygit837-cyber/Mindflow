"""Agent API interfaces.

Defines contracts for agent management, configuration,
and lifecycle operations.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class AgentInterface(Protocol):
    """Contract for agent API implementations."""
    
    async def list_agents(self) -> list[dict]:
        """List available agents."""
        ...

    async def get_agent_config(self, agent_id: str) -> dict:
        """Get agent configuration."""
        ...

    async def update_agent_config(self, agent_id: str, config: dict) -> dict:
        """Update agent configuration."""
        ...

    async def get_agent_status(self, agent_id: str) -> dict:
        """Get agent status and health."""
        ...
