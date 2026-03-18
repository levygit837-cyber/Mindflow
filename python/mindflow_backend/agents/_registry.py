"""Agent registry — singleton that holds all registered personalities.

Provides ``register_all_personalities()`` for startup bootstrapping and
``get_agent()`` for runtime lookups. The canonical runtime resolves agents by
base role, with optional specialization when the planner/delegation layer opts in.
"""

from __future__ import annotations

from mindflow_backend.agents._base import BaseAgent
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.orchestration.orchestrator import AgentType
from mindflow_backend.schemas.orchestration.specialists import SpecialistType
from mindflow_backend.agents.core.initialization import initialize_agent_system, validate_dependencies

_logger = get_logger(__name__)

# Mapping from specialist name → canonical agent_id ("role:specialist").
# Used so callers can look up specialists by their short name without needing
# to know the base AgentType — e.g. get_agent("arch_tech") resolves to the
# (CODER, ARCH_TECH) entry just like get_agent(agent_id="coder:arch_tech").
_SPECIALIST_AGENT_ID: dict[str, str] = {
    "arch_tech": "coder:arch_tech",
    "security_guard": "analyst:security_guard",
    "critic": "analyst:critic",
    "brainstorm": "analyst:brainstorm",
    "deep_iteration": "analyst:deep_iteration",
}


def _normalize_role(agent_type: AgentType | str) -> AgentType:
    """Normalize legacy string lookups to canonical agent roles."""
    if isinstance(agent_type, AgentType):
        return agent_type

    normalized = str(agent_type).strip().lower()
    if normalized == "general":
        return AgentType.ANALYST
    return AgentType(normalized)


def _normalize_specialist(specialist: SpecialistType | str | None) -> SpecialistType | None:
    if specialist is None or isinstance(specialist, SpecialistType):
        return specialist
    return SpecialistType(str(specialist).strip().lower())


class AgentRegistry:
    """In-memory registry of agent personalities.

    Agents are registered at startup via ``register_all_personalities()``
    and retrieved at runtime via ``get()`` or the module-level helper
    ``get_agent()``.
    """

    def __init__(self) -> None:
        self._agents: dict[tuple[AgentType, SpecialistType | None], BaseAgent] = {}
        self._default_agents: dict[AgentType, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        """Register a personality.

        Default role lookup always resolves to the base role variant
        (``specialist is None``). Specialized variants receive their own slot.
        """
        key = (agent.agent_role, agent.specialist)
        self._agents[key] = agent
        if agent.specialist is None:
            self._default_agents[agent.agent_role] = agent
        _logger.debug(
            "agent_registered",
            agent_role=str(agent.agent_role),
            specialist=getattr(agent.specialist, "value", None),
            agent_id=agent.agent_id,
        )

    def get(
        self,
        agent_type: AgentType | str,
        specialist: SpecialistType | str | None = None,
    ) -> BaseAgent:
        """Retrieve an agent by type.

        Raises:
            KeyError: If the agent type is not registered.
        """
        role = _normalize_role(agent_type)
        specialization = _normalize_specialist(specialist)

        try:
            if specialization is not None:
                return self._agents[(role, specialization)]
            return self._default_agents[role]
        except KeyError:
            if specialization is not None:
                raise KeyError(
                    f"Agent '{role.value}' with specialist '{specialization.value}' is not registered."
                ) from None
            raise KeyError(f"Agent type '{role.value}' is not registered.") from None

    def get_by_id(self, agent_id: str) -> BaseAgent:
        """Retrieve an agent by its stable composite identity."""
        normalized = agent_id.strip().lower()
        if ":" in normalized:
            role_value, specialist_value = normalized.split(":", 1)
            return self.get(AgentType(role_value), SpecialistType(specialist_value))
        return self.get(AgentType(normalized))

    def list_all(self) -> list[BaseAgent]:
        """Return all registered agents."""
        return list(self._agents.values())

    @property
    def count(self) -> int:
        return len(self._agents)

    def clear(self) -> None:
        """Remove all registrations (useful for testing)."""
        self._agents.clear()
        self._default_agents.clear()


# Module-level singleton
_registry = AgentRegistry()


def get_agent(
    agent_type: AgentType | str | None = None,
    specialist: SpecialistType | str | None = None,
    agent_id: str | None = None,
) -> BaseAgent:
    """Module-level shortcut to retrieve an agent from the global registry.

    Accepts both canonical agent roles (``AgentType`` values: coder, analyst,
    researcher, orchestrator) and specialist short names (e.g. ``arch_tech``,
    ``security_guard``).  Specialist names are resolved via
    ``_SPECIALIST_AGENT_ID`` so callers don't have to know the base role.
    """
    if agent_id:
        return _registry.get_by_id(agent_id)
    if agent_type is None:
        raise TypeError("get_agent() requires 'agent_type' when 'agent_id' is not provided")
    # Resolve specialist short-names transparently so that
    # get_agent("arch_tech") works exactly like get_agent(agent_id="coder:arch_tech").
    normalized = str(agent_type).strip().lower()
    if normalized in _SPECIALIST_AGENT_ID:
        return _registry.get_by_id(_SPECIALIST_AGENT_ID[normalized])
    return _registry.get(agent_type, specialist=specialist)


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
            create_orchestrator_agent,
            create_security_agent,
            create_review_agent,
            create_architecture_agent,
            create_brainstorm_agent,
            create_deep_analysis_agent,
        )

        for factory in (
            create_analyst_agent,
            create_coder_agent,
            create_researcher_agent,
            create_orchestrator_agent,
            create_security_agent,
            create_review_agent,
            create_architecture_agent,
            create_brainstorm_agent,
            create_deep_analysis_agent,
        ):
            _registry.register(factory())

        _logger.info("all_specialists_registered", count=_registry.count)
    
    except Exception as e:
        _logger.error("specialist_registration_failed", error=str(e))
        raise
