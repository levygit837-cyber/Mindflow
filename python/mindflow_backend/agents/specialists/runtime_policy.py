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
from typing import TYPE_CHECKING

from mindflow_backend.agents._base import BaseAgent
from mindflow_backend.agents.prompts.core.analyst import (
    ANALYST_SYSTEM_PROMPT,
    compose_analyst_prompt,
)
from mindflow_backend.agents.prompts.core.coder import CODER_SYSTEM_PROMPT, compose_coder_prompt
from mindflow_backend.agents.prompts.core.orchestrator import ORCHESTRATOR_SYSTEM_PROMPT
from mindflow_backend.agents.prompts.core.researcher import RESEARCHER_SYSTEM_PROMPT
from mindflow_backend.agents.prompts.specialized.deep_analysis import DEEP_ANALYSIS_PROMPT
from mindflow_backend.agents.prompts.specialized.planning import PLANNING_PROMPT
from mindflow_backend.schemas.orchestration.communication import (
    CommRole,
    MissionGraphType,
)
from mindflow_backend.schemas.orchestration.orchestrator import (
    AgentType,
    SandboxMode,
    ThinkingLevel,
    ToolScope,
)
from mindflow_backend.schemas.orchestration.specialists import SpecialistType

if TYPE_CHECKING:
    from mindflow_backend.execution.sub_teams.sub_team_config import SubTeamConfig


# Import predefined sub-team configs for runtime use
def _get_sub_team_configs() -> dict[str, Any]:
    """Lazy import of SubTeamConfig to avoid circular dependencies."""
    from mindflow_backend.execution.sub_teams.sub_team_config import (
        ANALYST_SUB_TEAM_CONFIG,
        CODER_SUB_TEAM_CONFIG,
        RESEARCHER_SUB_TEAM_CONFIG,
    )

    return {
        "analyst": ANALYST_SUB_TEAM_CONFIG,
        "coder": CODER_SUB_TEAM_CONFIG,
        "researcher": RESEARCHER_SUB_TEAM_CONFIG,
    }


@dataclass(frozen=True, slots=True)
class AgentRuntimePolicy:
    """Immutable runtime contract for a role or specialist identity."""

    agent_role: AgentType
    system_prompt: str
    specialist: SpecialistType | None = None
    custom_agent_id: str | None = None
    tools: tuple[ToolScope, ...] = ()
    sandbox: SandboxMode = SandboxMode.NONE
    thinking_level: ThinkingLevel = ThinkingLevel.MEDIUM
    keep_context: bool = True
    max_iterations: int = 1
    summary: str = ""
    use_when: str = ""

    # ── Communication and mission fields (Phase 1C) ──────────────────
    comm_role: CommRole = CommRole.SPECIALIST
    """Papel na sessão colaborativa: leader | specialist | observer"""

    available_mission_graphs: tuple[MissionGraphType, ...] = ()
    """Tipos de execution graphs que este agente pode executar"""

    can_observe: bool = False
    """Se True, o agente pode entrar em modo observer após missão"""

    mission_types: tuple[str, ...] = ()
    """Tipos de missão que este agente pode liderar (strings descritivas)"""

    # ── Sub-Team capability fields (Phase 3.3) ──────────────────────────
    supports_sub_team: bool = False
    """Se True, este agente pode spawnar sub-teams de executores especializados"""

    sub_team_config: SubTeamConfig | None = None
    """Configuração de sub-team (model tier, timeout, max agents)"""

    @property
    def agent_id(self) -> str:
        if self.custom_agent_id:
            return self.custom_agent_id
        if self.specialist is None:
            return self.agent_role.value
        return f"{self.agent_role.value}:{self.specialist.value}"

    def build_agent(self) -> BaseAgent:
        """Create the concrete runtime agent from the policy.

        Injects tool descriptions into the system prompt so the LLM
        knows which tools are available and how to use them.
        """
        enhanced_prompt = self._inject_tool_descriptions(self.system_prompt)
        return BaseAgent(
            agent_role=self.agent_role,
            specialist=self.specialist,
            custom_agent_id=self.custom_agent_id,
            system_prompt=enhanced_prompt,
            tools=list(self.tools),
            thinking_level=self.thinking_level,
            sandbox=self.sandbox,
            keep_context=self.keep_context,
        )

    def _inject_tool_descriptions(self, base_prompt: str) -> str:
        """Inject tool descriptions and usage instructions into the prompt."""
        try:
            from mindflow_backend.agents.tools.tool_injection import (
                inject_tools_into_prompt,
            )
            from mindflow_backend.agents.tools.base.tool_registry import (
                get_tool_registry,
            )

            # Create a temporary BaseAgent to pass to injector
            temp_agent = BaseAgent(
                agent_role=self.agent_role,
                specialist=self.specialist,
                system_prompt=base_prompt,
                tools=list(self.tools),
            )
            registry = get_tool_registry()
            return inject_tools_into_prompt(base_prompt, registry, temp_agent)
        except Exception:
            # Fallback: return original prompt if injection fails
            return base_prompt

    async def build_agent_assembled(self, working_directory: str | None = None) -> BaseAgent:
        """NOVO: Cria agente usando PromptAssembler multi-camada."""
        from mindflow_backend.agents.prompts.base import build_assembled_prompt
        from mindflow_backend.agents.tools.tool_injection import ToolPromptInjector
        from mindflow_backend.agents.tools.base.tool_registry import get_tool_registry

        registry = get_tool_registry()
        injector = ToolPromptInjector(registry)

        assembled_prompt = await build_assembled_prompt(
            personality_prompt=self.system_prompt,
            include_tools=True,
            include_environment=True,
            include_git=True,
            include_memory=True,
            tool_injector=injector,
            working_directory=working_directory,
        )

        return BaseAgent(
            agent_role=self.agent_role,
            specialist=self.specialist,
            custom_agent_id=self.custom_agent_id,
            system_prompt=assembled_prompt,
            tools=list(self.tools),
            sandbox=self.sandbox,
            thinking_level=self.thinking_level,
            keep_context=self.keep_context,
        )


# Lazy-load sub-team configs to avoid circular imports at module level
_SUB_TEAM_CONFIGS: dict[str, Any] | None = None


def _ensure_sub_team_configs() -> dict[str, Any]:
    """Ensure sub-team configs are loaded."""
    global _SUB_TEAM_CONFIGS
    if _SUB_TEAM_CONFIGS is None:
        _SUB_TEAM_CONFIGS = _get_sub_team_configs()
    return _SUB_TEAM_CONFIGS


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
        # ── Communication fields ──────────────────────────────────────
        comm_role=CommRole.LEADER,
        available_mission_graphs=(),  # Não executa missões; lança missões de outros
        can_observe=True,  # Monitora todas as missões em andamento
        mission_types=("coordination", "synthesis", "team_session"),
    ),
    "analyst": AgentRuntimePolicy(
        agent_role=AgentType.ANALYST,
        system_prompt=ANALYST_SYSTEM_PROMPT,
        tools=(ToolScope.CODE_ANALYSIS, ToolScope.CONTEXTPLUS, ToolScope.FILESYSTEM, ToolScope.SHELL, ToolScope.MEMORY),
        sandbox=SandboxMode.READ_ONLY,
        thinking_level=ThinkingLevel.MEDIUM,
        max_iterations=500,  # Unlimited for deep code investigation
        summary="Code investigation, structure analysis, symbol tracing, workspace exploration.",
        use_when="Understanding code, tracing bugs, auditing and explaining implementations.",
        # ── Communication fields ──────────────────────────────────────
        comm_role=CommRole.SPECIALIST,
        available_mission_graphs=(
            MissionGraphType.ANALYSIS,
            MissionGraphType.DEEP_INVESTIGATION,
            MissionGraphType.SECURITY_AUDIT,
            MissionGraphType.CODE_REVIEW,
        ),
        can_observe=True,
        mission_types=("analysis", "code_investigation", "review"),
        # ── Sub-Team capability (Phase 3.3) ───────────────────────────
        supports_sub_team=True,
        sub_team_config=_get_sub_team_configs()["analyst"],
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
        # ── Communication fields ──────────────────────────────────────
        comm_role=CommRole.SPECIALIST,
        available_mission_graphs=(
            MissionGraphType.SECURITY_AUDIT,
            MissionGraphType.VULNERABILITY_SCAN,
        ),
        can_observe=True,
        mission_types=("security_audit", "vulnerability_scan"),
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
        # ── Communication fields ──────────────────────────────────────
        comm_role=CommRole.SPECIALIST,
        available_mission_graphs=(
            MissionGraphType.CODE_REVIEW,
            MissionGraphType.ANALYSIS,
        ),
        can_observe=False,
        mission_types=("code_review", "quality_assessment"),
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
        # ── Communication fields ──────────────────────────────────────
        comm_role=CommRole.SPECIALIST,
        available_mission_graphs=(
            MissionGraphType.IDEATION,
            MissionGraphType.EXPLORATION,
        ),
        can_observe=False,
        mission_types=("ideation", "exploration"),
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
        # ── Communication fields ──────────────────────────────────────
        comm_role=CommRole.SPECIALIST,
        available_mission_graphs=(
            MissionGraphType.DEEP_INVESTIGATION,
            MissionGraphType.MULTI_PASS_ANALYSIS,
        ),
        can_observe=True,
        mission_types=("deep_analysis", "multi_pass_investigation"),
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
        # ── Communication fields ──────────────────────────────────────
        comm_role=CommRole.SPECIALIST,
        available_mission_graphs=(
            MissionGraphType.ANALYSIS,
            MissionGraphType.DEEP_INVESTIGATION,
        ),
        can_observe=False,
        mission_types=("planning", "impact_analysis"),
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
        # ── Communication fields ──────────────────────────────────────
        comm_role=CommRole.SPECIALIST,
        available_mission_graphs=(
            MissionGraphType.CODING_TASK,
            MissionGraphType.REFACTOR,
            MissionGraphType.BUG_FIX,
            MissionGraphType.IMPLEMENTATION,
        ),
        can_observe=False,
        mission_types=("coding", "bug_fix", "refactor", "implementation"),
        # ── Sub-Team capability (Phase 3.3) ───────────────────────────
        supports_sub_team=True,
        sub_team_config=_get_sub_team_configs()["coder"],
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
        # ── Communication fields ──────────────────────────────────────
        comm_role=CommRole.SPECIALIST,
        available_mission_graphs=(
            MissionGraphType.ARCHITECTURE_DESIGN,
            MissionGraphType.STRUCTURAL_REFACTOR,
            MissionGraphType.CODING_TASK,
        ),
        can_observe=False,
        mission_types=("architecture_design", "structural_refactor"),
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
        # ── Communication fields ──────────────────────────────────────
        comm_role=CommRole.SPECIALIST,
        available_mission_graphs=(
            MissionGraphType.WEB_RESEARCH,
            MissionGraphType.DOCUMENTATION_LOOKUP,
            MissionGraphType.COMPARISON_ANALYSIS,
        ),
        can_observe=False,
        mission_types=("web_research", "documentation", "comparison"),
        # ── Sub-Team capability (Phase 3.3) ───────────────────────────
        supports_sub_team=True,
        sub_team_config=_get_sub_team_configs()["researcher"],
    ),
}

_SESSION_RUNTIME_POLICIES: dict[str, dict[str, AgentRuntimePolicy]] = {}


def register_session_runtime_policy(
    session_id: str,
    policy: AgentRuntimePolicy,
) -> None:
    """Register a dynamic runtime policy for a session."""
    session_key = str(session_id)
    _SESSION_RUNTIME_POLICIES.setdefault(session_key, {})[policy.agent_id] = policy


def unregister_session_runtime_policies(session_id: str) -> None:
    """Remove all dynamic runtime policies for a session."""
    _SESSION_RUNTIME_POLICIES.pop(str(session_id), None)


def get_agent_runtime_policy(
    agent_role: AgentType | str | None = None,
    *,
    specialist: SpecialistType | str | None = None,
    agent_id: str | None = None,
    session_id: str | None = None,
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

    if session_id:
        session_policies = _SESSION_RUNTIME_POLICIES.get(str(session_id), {})
        if key in session_policies:
            return session_policies[key]

    try:
        return AGENT_RUNTIME_POLICY[key]
    except KeyError as exc:
        raise KeyError(f"Unknown runtime policy for {key!r}") from exc


def list_agent_runtime_policies(session_id: str | None = None) -> list[AgentRuntimePolicy]:
    """Return all registered runtime policies."""
    policies = list(AGENT_RUNTIME_POLICY.values())
    if session_id:
        policies.extend(_SESSION_RUNTIME_POLICIES.get(str(session_id), {}).values())
    return policies
