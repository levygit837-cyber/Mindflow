"""Intent analysis for orchestrator routing.

Provides the IntentAnalysis model and helper functions
for building agent capability descriptions.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from mindflow_backend.agents.specialists.runtime_policy import list_agent_runtime_policies
from mindflow_backend.schemas.orchestration.orchestrator import (
    AgentType,
    ExecutionStrategy,
)

def _get_agent_capabilities(session_id: str | None = None) -> dict[str, tuple[str, str]]:
    """Build capability descriptions for every visible runtime policy."""
    return {
        policy.agent_id: (policy.summary, policy.use_when)
        for policy in list_agent_runtime_policies(session_id=session_id)
    }


def _build_available_agents_section(session_id: str | None = None) -> str:
    """Build dynamic agent roster section for the routing prompt.

    Reads from the global registry and generates a formatted description
    of all available agents and specialists. Falls back to a static list
    if the registry is not yet populated.
    """
    try:
        from mindflow_backend.agents._registry import get_registry

        registry = get_registry()
        agents = registry.list_all(session_id=session_id)
    except Exception:
        agents = []

    if not agents:
        # Fallback — registry not yet initialized
        return (
            "### Base Agents (always available)\n"
            "- **ANALYST** — Code investigation, explaining, tracing | default for most tasks\n"
            "- **CODER** — Code writing, fixing, refactoring\n"
            "- **RESEARCHER** — Web search, documentation lookup\n"
            "- **ORCHESTRATOR** — Direct response for greetings only\n"
            "\n### Registered Specialists\n"
            "- `arch_tech` (CODER) — Architecture design\n"
            "- `security_guard` (ANALYST) — Security audits\n"
            "- `critic` (ANALYST) — Code review\n"
            "- `brainstorm` (ANALYST) — Idea generation and alternatives exploration\n"
            "- `deep_iteration` (ANALYST) — Deep exhaustive analysis\n"
        )

    base_agents = [a for a in agents if a.specialist is None]
    specialist_agents = [a for a in agents if a.specialist is not None]
    capabilities = _get_agent_capabilities(session_id=session_id)

    lines = ["### Base Agents (always available)"]
    for agent in base_agents:
        caps = capabilities.get(
            agent.agent_id, ("General purpose agent", "General tasks")
        )
        lines.append(
            f"- **{agent.agent_role.value.upper()}** — {caps[0]}\n"
            f"  ↳ Use when: {caps[1]}"
        )

    if specialist_agents:
        lines.append(
            "\n### Registered Specialists (set recommended_specialist + base agent)"
        )
        for agent in specialist_agents:
            caps = capabilities.get(
                agent.agent_id, ("Domain specialist", "Domain-specific tasks")
            )
            base = agent.agent_role.value.upper()
            spec = agent.specialist.value
            lines.append(
                f"- `{spec}` (base: {base}) — {caps[0]}\n"
                f"  ↳ Use when: {caps[1]}"
            )

    return "\n".join(lines)


def _get_valid_agent_and_specialist_values(session_id: str | None = None) -> tuple[str, str]:
    """Return pipe-separated valid values for recommended_agent and recommended_specialist.

    Used to make the JSON format hint in the routing prompt dynamic.
    Falls back to static defaults if registry is unavailable.
    """
    try:
        from mindflow_backend.agents._registry import get_registry

        registry = get_registry()
        agents = registry.list_all(session_id=session_id)
    except Exception:
        agents = []

    if not agents:
        return (
            "CODER|ANALYST|RESEARCHER|ORCHESTRATOR",
            "security_guard|critic|arch_tech|brainstorm|deep_iteration|null",
        )

    base_roles = sorted(
        {a.agent_role.value.upper() for a in agents if a.specialist is None}
    )
    specialists = sorted(
        a.specialist.value for a in agents if a.specialist is not None
    )

    return "|".join(base_roles), "|".join(specialists) + "|null"


def _get_valid_agent_id_values(session_id: str | None = None) -> str:
    """Return pipe-separated valid agent identities for exact routing."""
    agent_ids = sorted(
        {
            policy.agent_id
            for policy in list_agent_runtime_policies(session_id=session_id)
        }
    )
    if not agent_ids:
        return "analyst|coder|researcher|orchestrator|null"
    return "|".join(agent_ids) + "|null"


class IntentAnalysis(BaseModel):
    """Result of LLM intent analysis."""

    user_intent: str = Field(
        description="Clear interpretation of what user wants to accomplish"
    )
    needs_code_context: bool = Field(
        default=False, description="Unused — kept for schema compatibility"
    )
    context_needed: str = Field(
        default="", description="Unused — kept for schema compatibility"
    )
    suggested_scope: list[str] = Field(
        default_factory=list, description="Suggested files/modules to analyze"
    )
    recommended_agent: AgentType = Field(
        description="Which agent should handle this"
    )
    recommended_agent_id: str | None = Field(
        default=None,
        description="Exact agent identity when routing to a plugin or custom marketplace agent",
    )
    recommended_specialist: str | None = Field(
        default=None, description="Optional specialist/profile identifier"
    )
    formulated_objective: str = Field(
        description="Precise objective for the target agent"
    )
    confidence: float = Field(
        description="Confidence in this analysis (0-1)"
    )
    is_multi_agent: bool = Field(
        default=False, description="Requires multiple agents"
    )
    agent_sequence: list[AgentType] = Field(
        default_factory=list, description="Sequence of agents needed"
    )
    agent_sequence_ids: list[str] = Field(
        default_factory=list,
        description="Optional exact sequence of agent identities for marketplace or plugin agents",
    )
    execution_strategy: ExecutionStrategy = Field(
        default=ExecutionStrategy.DELEGATE,
        description="How to execute: direct_response, delegate, chain, or graph",
    )

    @field_validator("recommended_agent", mode="before")
    @classmethod
    def normalize_agent(cls, v: str) -> str:
        """Normalize agent name to lowercase."""
        return v.lower() if isinstance(v, str) else v

    @field_validator("agent_sequence", mode="before")
    @classmethod
    def normalize_agent_sequence(cls, v: list) -> list:
        """Normalize agent sequence names to lowercase."""
        return [x.lower() if isinstance(x, str) else x for x in (v or [])]

    @field_validator("recommended_agent_id", mode="before")
    @classmethod
    def nullify_agent_id(cls, v):
        """Convert null-ish strings to Python None."""
        if isinstance(v, str) and v.lower() in ("null", "none", ""):
            return None
        return v.lower() if isinstance(v, str) else v

    @field_validator("agent_sequence_ids", mode="before")
    @classmethod
    def normalize_agent_sequence_ids(cls, v: list) -> list:
        """Normalize explicit agent ids."""
        return [x.lower() if isinstance(x, str) else x for x in (v or [])]

    @field_validator("recommended_specialist", mode="before")
    @classmethod
    def nullify_null_string(cls, v):
        """Convert the literal string 'null' returned by LLMs to Python None."""
        if isinstance(v, str) and v.lower() in ("null", "none", ""):
            return None
        return v
