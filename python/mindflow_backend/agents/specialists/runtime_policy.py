"""Canonical runtime policy for agents and registered specialists.

This module is the single source of truth for runtime identity:
- system prompt
- tool scopes
- sandbox mode
- thinking level
- max tool iterations
- high-level routing hints
"""

from __future__ import annotations

from dataclasses import dataclass

from mindflow_backend.agents._base import BaseAgent
from mindflow_backend.agents.prompts.core.analyst import ANALYST_SYSTEM_PROMPT, compose_analyst_prompt
from mindflow_backend.agents.prompts.core.coder import CODER_SYSTEM_PROMPT, compose_coder_prompt
from mindflow_backend.agents.prompts.core.orchestrator import ORCHESTRATOR_SYSTEM_PROMPT
from mindflow_backend.agents.prompts.core.researcher import RESEARCHER_SYSTEM_PROMPT
from mindflow_backend.agents.prompts.specialized.deep_analysis import DEEP_ANALYSIS_PROMPT
from mindflow_backend.agents.prompts.specialized.planning import PLANNING_PROMPT
from mindflow_backend.schemas.orchestration.orchestrator import (
    AgentType,
    SandboxMode,
    ThinkingLevel,
    ToolScope,
)
from mindflow_backend.schemas.orchestration.specialists import SpecialistType


@dataclass(frozen=True, slots=True)
class AgentRuntimePolicy:
    """Immutable runtime contract for a role or specialist identity."""

    agent_role: AgentType
    system_prompt: str
    specialist: SpecialistType | None = None
    tools: tuple[ToolScope, ...] = ()
    sandbox: SandboxMode = SandboxMode.NONE
    thinking_level: ThinkingLevel = ThinkingLevel.MEDIUM
    keep_context: bool = True
    max_iterations: int = 1
    summary: str = ""
    use_when: str = ""

    @property
    def agent_id(self) -> str:
        if self.specialist is None:
            return self.agent_role.value
        return f"{self.agent_role.value}:{self.specialist.value}"

    def build_agent(self) -> BaseAgent:
        """Create the concrete runtime agent from the policy."""
        return BaseAgent(
            agent_role=self.agent_role,
            specialist=self.specialist,
            system_prompt=self.system_prompt,
            tools=list(self.tools),
            thinking_level=self.thinking_level,
            sandbox=self.sandbox,
            keep_context=self.keep_context,
        )


AGENT_RUNTIME_POLICY: dict[str, AgentRuntimePolicy] = {
    "orchestrator": AgentRuntimePolicy(
        agent_role=AgentType.ORCHESTRATOR,
        system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
        tools=(ToolScope.MEMORY, ToolScope.PLANNING, ToolScope.DELEGATION),
        sandbox=SandboxMode.NONE,
        thinking_level=ThinkingLevel.HIGH,
        max_iterations=1000,  # Practically unlimited for deep orchestration
        summary="Central conversational agent that delegates to specialists via delegate_to_agent tool.",
        use_when="All user messages — the Orchestrator is the sole entry point.",
    ),
    "analyst": AgentRuntimePolicy(
        agent_role=AgentType.ANALYST,
        system_prompt=ANALYST_SYSTEM_PROMPT,
        tools=(ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM, ToolScope.SHELL, ToolScope.MEMORY),
        sandbox=SandboxMode.READ_ONLY,
        thinking_level=ThinkingLevel.MEDIUM,
        max_iterations=500,  # Unlimited for deep code investigation
        summary="Code investigation, structure analysis, symbol tracing, workspace exploration.",
        use_when="Understanding code, tracing bugs, auditing and explaining implementations.",
    ),
    "analyst:security_guard": AgentRuntimePolicy(
        agent_role=AgentType.ANALYST,
        specialist=SpecialistType.SECURITY_GUARD,
        system_prompt=compose_analyst_prompt("core", "security_guard"),
        tools=(ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM, ToolScope.SHELL),
        sandbox=SandboxMode.READ_ONLY,
        thinking_level=ThinkingLevel.HIGH,
        max_iterations=500,  # Unlimited for thorough security audits
        summary="Security audits, auth flow review, vulnerability-oriented investigation.",
        use_when="Security reviews, auth analysis and vulnerability checks.",
    ),
    "analyst:critic": AgentRuntimePolicy(
        agent_role=AgentType.ANALYST,
        specialist=SpecialistType.CRITIC,
        system_prompt=compose_analyst_prompt("core", "critic"),
        tools=(ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM, ToolScope.SHELL),
        sandbox=SandboxMode.READ_ONLY,
        thinking_level=ThinkingLevel.MEDIUM,
        max_iterations=500,  # Unlimited for comprehensive code review
        summary="Code review, critique, regression and best-practice assessment.",
        use_when="Focused review of implementation quality and risks.",
    ),
    "analyst:brainstorm": AgentRuntimePolicy(
        agent_role=AgentType.ANALYST,
        specialist=SpecialistType.BRAINSTORM,
        system_prompt=compose_analyst_prompt("core", "brainstorm"),
        tools=(ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM),
        sandbox=SandboxMode.READ_ONLY,
        thinking_level=ThinkingLevel.MEDIUM,
        max_iterations=500,  # Unlimited for extensive ideation
        summary="Structured idea generation, alternatives exploration and option scoring.",
        use_when="Ideation, alternatives exploration and brainstorming requests.",
    ),
    "analyst:deep_iteration": AgentRuntimePolicy(
        agent_role=AgentType.ANALYST,
        specialist=SpecialistType.DEEP_ITERATION,
        system_prompt=DEEP_ANALYSIS_PROMPT,
        tools=(ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM, ToolScope.SHELL),
        sandbox=SandboxMode.READ_ONLY,
        thinking_level=ThinkingLevel.HIGH,
        max_iterations=1000,  # Unlimited for exhaustive multi-pass analysis
        summary="Deep multi-file investigation with iterative exhaustive analysis.",
        use_when="Cross-cutting, high-complexity analysis requiring multiple passes.",
    ),
    "analyst:planner": AgentRuntimePolicy(
        agent_role=AgentType.ANALYST,
        specialist=SpecialistType.DEEP_ITERATION,  # Uses deep_iteration as base
        system_prompt=PLANNING_PROMPT,
        tools=(ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM, ToolScope.PLANNING),
        sandbox=SandboxMode.READ_ONLY,
        thinking_level=ThinkingLevel.HIGH,
        max_iterations=500,  # Unlimited for complex planning
        summary="Structured implementation planning with file impact analysis and task decomposition.",
        use_when="Complex tasks requiring explicit planning before implementation.",
    ),
    "coder": AgentRuntimePolicy(
        agent_role=AgentType.CODER,
        system_prompt=CODER_SYSTEM_PROMPT,
        tools=(ToolScope.FILESYSTEM, ToolScope.SHELL, ToolScope.MEMORY),
        sandbox=SandboxMode.FULL,
        thinking_level=ThinkingLevel.HIGH,
        max_iterations=1000,  # Unlimited for complex implementations
        summary="Code writing, implementation, refactoring and bug fixing.",
        use_when="Implementing features, fixing bugs and editing the codebase.",
    ),
    "coder:arch_tech": AgentRuntimePolicy(
        agent_role=AgentType.CODER,
        specialist=SpecialistType.ARCH_TECH,
        system_prompt=compose_coder_prompt("core", "arch_tech"),
        tools=(ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM, ToolScope.SHELL),
        sandbox=SandboxMode.FULL,
        thinking_level=ThinkingLevel.HIGH,
        max_iterations=1000,  # Unlimited for architectural work
        summary="Architecture design, structural decisions and implementation planning.",
        use_when="Architecture-heavy coding or structural refactoring requests.",
    ),
    "researcher": AgentRuntimePolicy(
        agent_role=AgentType.RESEARCHER,
        system_prompt=RESEARCHER_SYSTEM_PROMPT,
        tools=(ToolScope.WEB_SEARCH, ToolScope.PINCHTAB_FLEET, ToolScope.PINCHTAB_BROWSER, ToolScope.MEMORY),
        sandbox=SandboxMode.READ_ONLY,
        thinking_level=ThinkingLevel.HIGH,
        max_iterations=500,  # Unlimited for thorough research
        summary="Web search, documentation lookup and external research.",
        use_when="External research, documentation lookup and technology comparisons.",
    ),
}


def get_agent_runtime_policy(
    agent_role: AgentType | str | None = None,
    *,
    specialist: SpecialistType | str | None = None,
    agent_id: str | None = None,
) -> AgentRuntimePolicy:
    """Return the canonical runtime policy for the given identity."""
    if agent_id:
        key = str(agent_id).strip().lower()
    else:
        role_value = agent_role.value if isinstance(agent_role, AgentType) else str(agent_role or "").strip().lower()
        if specialist is None:
            key = role_value
        else:
            spec_value = specialist.value if isinstance(specialist, SpecialistType) else str(specialist).strip().lower()
            key = f"{role_value}:{spec_value}"

    try:
        return AGENT_RUNTIME_POLICY[key]
    except KeyError as exc:
        raise KeyError(f"Unknown runtime policy for {key!r}") from exc


def list_agent_runtime_policies() -> list[AgentRuntimePolicy]:
    """Return all registered runtime policies."""
    return list(AGENT_RUNTIME_POLICY.values())
