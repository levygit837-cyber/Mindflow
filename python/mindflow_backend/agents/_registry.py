"""Agent registry — singleton that holds all registered personalities.

Provides ``register_all_personalities()`` for startup bootstrapping and
``get_agent()`` for runtime lookups. Updated to use new architecture.
"""

from __future__ import annotations

from mindflow_backend.agents._base import BaseAgent
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.orchestration.orchestrator import AgentType
from mindflow_backend.agents.core.initialization import initialize_agent_system, validate_dependencies

_logger = get_logger(__name__)


class AgentRegistry:
    """In-memory registry of agent personalities.

    Agents are registered at startup via ``register_all_personalities()``
    and retrieved at runtime via ``get()`` or the module-level helper
    ``get_agent()``.
    """

    def __init__(self) -> None:
        self._agents: dict[AgentType, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        """Register a personality.  Overwrites any existing entry."""
        self._agents[agent.agent_type] = agent
        _logger.debug("agent_registered", agent_type=str(agent.agent_type))

    def get(self, agent_type: AgentType) -> BaseAgent:
        """Retrieve an agent by type.

        Raises:
            KeyError: If the agent type is not registered.
        """
        try:
            return self._agents[agent_type]
        except KeyError:
            raise KeyError(f"Agent type '{agent_type}' is not registered.") from None

    def list_all(self) -> list[BaseAgent]:
        """Return all registered agents."""
        return list(self._agents.values())

    @property
    def count(self) -> int:
        return len(self._agents)

    def clear(self) -> None:
        """Remove all registrations (useful for testing)."""
        self._agents.clear()


# Module-level singleton
_registry = AgentRegistry()


def get_agent(agent_type: AgentType) -> BaseAgent:
    """Module-level shortcut to retrieve an agent from the global registry."""
    return _registry.get(agent_type)


def get_registry() -> AgentRegistry:
    """Return the global registry instance."""
    return _registry


def register_all_specialists() -> None:
    """Import and register every specialist in global registry.

    Call once during application startup (e.g. in ``main.py``).
    Initializes the new dependency injection system.
    """
    try:
        # Initialize the agent system with DI
        initialize_agent_system()
        
        # Validate dependencies
        if not validate_dependencies():
            raise RuntimeError("Agent system dependency validation failed")
        
        # Import and register specialist factories
        from mindflow_backend.agents.specialists import (
            create_analyst_agent,
            create_coder_agent,
            create_researcher_agent,
            create_security_agent,
            create_review_agent,
            create_architecture_agent,
            create_creative_agent,
            create_deep_analysis_agent,
        )

        for factory in (
            create_analyst_agent,
            create_coder_agent,
            create_researcher_agent,
            create_security_agent,
            create_review_agent,
            create_architecture_agent,
            create_creative_agent,
            create_deep_analysis_agent,
        ):
            _registry.register(factory())

        _logger.info("all_specialists_registered", count=_registry.count)
    
    except Exception as e:
        _logger.error("specialist_registration_failed", error=str(e))
        raise
