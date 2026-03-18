"""Canonical orchestrator routing implementation.

This module is the authoritative router for the production orchestration
runtime. It decides execution strategy and target agent identity, then hands
that route to the planner layer for final chain/graph resolution.
"""

from __future__ import annotations

import json
from contextlib import suppress
from typing import Any

from pydantic import BaseModel, Field, field_validator

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.orchestrator.delegation_engine import DelegationEngine
from mindflow_backend.runtime import get_model_for_provider, normalize_response_for_json
from mindflow_backend.schemas.orchestration.delegation import OrchestratorSession
from mindflow_backend.schemas.orchestration.orchestrator import (
    AgentType,
    ExecutionStrategy,
    OrchestratorDecision,
    Priority,
    ThinkingLevel,
    ToolScope,
)
from mindflow_backend.schemas.orchestration.workflow import WorkflowRouteDecision
from mindflow_backend.schemas.orchestration.specialists import SpecialistType
from mindflow_backend.agents.specialists.runtime_policy import (
    get_agent_runtime_policy,
    list_agent_runtime_policies,
)

_logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Static capability descriptions for each agent_id (role or role:specialist).
# These are used to build the dynamic routing prompt at request time.
# ---------------------------------------------------------------------------

_AGENT_CAPABILITIES: dict[str, tuple[str, str]] = {
    policy.agent_id: (policy.summary, policy.use_when)
    for policy in list_agent_runtime_policies()
}


def _build_available_agents_section() -> str:
    """Build dynamic agent roster section for the routing prompt.

    Reads from the global registry and generates a formatted description
    of all available agents and specialists. Falls back to a static list
    if the registry is not yet populated.
    """
    try:
        from mindflow_backend.agents._registry import get_registry
        registry = get_registry()
        agents = registry.list_all()
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

    lines = ["### Base Agents (always available)"]
    for agent in base_agents:
        caps = _AGENT_CAPABILITIES.get(agent.agent_id, ("General purpose agent", "General tasks"))
        lines.append(
            f"- **{agent.agent_role.value.upper()}** — {caps[0]}\n"
            f"  ↳ Use when: {caps[1]}"
        )

    if specialist_agents:
        lines.append("\n### Registered Specialists (set recommended_specialist + base agent)")
        for agent in specialist_agents:
            caps = _AGENT_CAPABILITIES.get(agent.agent_id, ("Domain specialist", "Domain-specific tasks"))
            base = agent.agent_role.value.upper()
            spec = agent.specialist.value
            lines.append(
                f"- `{spec}` (base: {base}) — {caps[0]}\n"
                f"  ↳ Use when: {caps[1]}"
            )

    return "\n".join(lines)


def _get_valid_agent_and_specialist_values() -> tuple[str, str]:
    """Return pipe-separated valid values for recommended_agent and recommended_specialist.

    Used to make the JSON format hint in the routing prompt dynamic.
    Falls back to static defaults if registry is unavailable.
    """
    try:
        from mindflow_backend.agents._registry import get_registry
        registry = get_registry()
        agents = registry.list_all()
    except Exception:
        agents = []

    if not agents:
        return (
            "CODER|ANALYST|RESEARCHER|ORCHESTRATOR",
            "security_guard|critic|arch_tech|brainstorm|deep_iteration|null",
        )

    base_roles = sorted({a.agent_role.value.upper() for a in agents if a.specialist is None})
    specialists = sorted(a.specialist.value for a in agents if a.specialist is not None)

    return "|".join(base_roles), "|".join(specialists) + "|null"


class IntentAnalysis(BaseModel):
    """Result of LLM intent analysis."""

    user_intent: str = Field(description="Clear interpretation of what user wants to accomplish")
    needs_code_context: bool = Field(default=False, description="Unused — kept for schema compatibility")
    context_needed: str = Field(default="", description="Unused — kept for schema compatibility")
    suggested_scope: list[str] = Field(default_factory=list, description="Suggested files/modules to analyze")
    recommended_agent: AgentType = Field(description="Which agent should handle this")
    recommended_specialist: str | None = Field(default=None, description="Optional specialist/profile identifier")
    formulated_objective: str = Field(description="Precise objective for the target agent")
    confidence: float = Field(description="Confidence in this analysis (0-1)")
    is_multi_agent: bool = Field(default=False, description="Requires multiple agents")
    agent_sequence: list[AgentType] = Field(default_factory=list, description="Sequence of agents needed")
    execution_strategy: ExecutionStrategy = Field(
        default=ExecutionStrategy.SINGLE_AGENT,
        description="How to execute: direct_response, single_agent, chain, or graph",
    )

    @field_validator("recommended_agent", mode="before")
    @classmethod
    def normalize_agent(cls, v: str) -> str:
        return v.lower() if isinstance(v, str) else v

    @field_validator("agent_sequence", mode="before")
    @classmethod
    def normalize_agent_sequence(cls, v: list) -> list:
        return [x.lower() if isinstance(x, str) else x for x in (v or [])]

    @field_validator("recommended_specialist", mode="before")
    @classmethod
    def nullify_null_string(cls, v):
        """Convert the literal string 'null' returned by LLMs to Python None."""
        if isinstance(v, str) and v.lower() in ("null", "none", ""):
            return None
        return v


class IntelligentRouter:
    """LLM-powered intelligent routing. The Orchestrator is an entity — it can
    respond directly OR delegate to specialists. No keyword routing."""

    def __init__(self, delegation_engine: DelegationEngine):
        self.delegation_engine = delegation_engine
        self.settings = get_settings()

    async def analyze_intent_with_llm(
        self,
        message: str,
        session_context: str = "",
        folder_path: str | None = None,
        has_folder_path: bool = False,
    ) -> IntentAnalysis:
        """Use LLM to analyze user intent and decide execution strategy."""

        available_agents_section = _build_available_agents_section()
        valid_agents_str, valid_specialists_str = _get_valid_agent_and_specialist_values()

        analysis_prompt = f"""You are the MindFlow Orchestrator routing engine. Classify the user request into EXACTLY ONE execution strategy.

User Request: {message}

Session Context: {session_context if session_context else "No previous context"}
Workspace Root: {folder_path if folder_path else "No folder_path provided"}
Has Workspace Root: {str(has_folder_path).lower()}

## Step 1 — Analyze Available Agents

IMPORTANT: Before choosing an agent, read the full roster below carefully and reason about which agent best matches the task. Do NOT assume a fixed set of agents — always route based on what is registered here.

{available_agents_section}

## Step 2 — Choose Execution Strategy (strictly in priority order)

### 1. direct_response — EXTREMELY RARE. Only these exact cases qualify:
- Pure greetings: "hi", "hello", "oi", "olá", "tudo bem?"
- Pure thanks: "thanks", "obrigado", "valeu"
- Ask who you are: "who are you?", "quem é você?"
- NO other case qualifies. If the user asks anything that requires thinking, answering, explaining, coding, or researching → DO NOT use direct_response.

### 2. single_agent — DEFAULT for almost everything. Use when ONE agent from the roster above can handle it alone. Match the task to the agent whose capabilities and "Use when" description best fit.

### 3. chain — Only when the task EXPLICITLY requires multiple distinct phases:
| chain_id | Use when |
|---|---|
| coding_task | Must read context AND write code (e.g., "implement feature X based on existing patterns") |
| analysis_task | Must research AND synthesize (e.g., "compare A and B then recommend") |
| file_analysis | User has set a folder_path and wants files analyzed, mapped, explained, audited, or traced |

## Step 3 — Select Specialist (if applicable)

Set `recommended_specialist` ONLY when the task clearly matches a registered specialist in the roster above. Leave it `null` if no specialist is a clear fit. Only use specialist names that appear in the roster — do NOT invent names.

Specialist routing examples (based on the registered roster):
- "design a arquitetura do sistema de pagamentos" → single_agent, CODER, recommended_specialist: "arch_tech"
- "audita a segurança do sistema de auth" → single_agent, ANALYST, recommended_specialist: "security_guard"
- "revisa este código e aponta problemas" → single_agent, ANALYST, recommended_specialist: "critic"
- "brainstorm ideias para melhorar a performance" → single_agent, ANALYST, recommended_specialist: "brainstorm"
- "pense em alternativas para resolver X" → single_agent, ANALYST, recommended_specialist: "brainstorm"

## Decision Examples
- "hello" → direct_response, ORCHESTRATOR
- "olá como você está?" → direct_response, ORCHESTRATOR
- "como funciona o orchestrator?" → single_agent, ANALYST
- "explica o fluxo de delegação" → single_agent, ANALYST
- "por que o agente está lento?" → single_agent, ANALYST
- "o que é o MindFlow?" → single_agent, ANALYST
- "cria uma função X" → single_agent, CODER
- "corrige o bug Y" → single_agent, CODER
- "pesquisa sobre langchain" → single_agent, RESEARCHER
- "implementa feature X lendo o código atual" → chain, coding_task
- "analise esta codebase" with folder_path → chain, file_analysis

## Strong Rule For Workspace Analysis
- If `has_folder_path` is true AND the request is about understanding, mapping, tracing, auditing, explaining, or exploring a codebase/workspace, choose:
  - execution_strategy = "chain"
  - suggested_chain_id = "file_analysis"
  - suggested_chain_type = "file_analysis"
  - recommended_agent = "ANALYST"
- If `has_folder_path` is false, do NOT force file_analysis.

## Response Format — ONLY valid JSON, no markdown:
{{
    "user_intent": "1-sentence interpretation",
    "needs_code_context": false,
    "context_needed": "",
    "suggested_scope": [],
    "recommended_agent": "{valid_agents_str}",
    "recommended_specialist": "{valid_specialists_str}",
    "formulated_objective": "precise objective for the specialist (empty if direct_response)",
    "confidence": 0.9,
    "is_multi_agent": false,
    "agent_sequence": [],
    "execution_strategy": "direct_response|single_agent|chain|graph"
}}

STRICT RULES:
- "ORCHESTRATOR" as recommended_agent ONLY when execution_strategy is "direct_response"
- When in doubt → single_agent + ANALYST (never direct_response for doubt cases)
- "direct_response" is reserved for the ~5% of messages that are pure social interaction
- Only use agent names and specialist names that appear in the registered roster above"""

        try:
            llm = get_model_for_provider(
                self.settings.default_provider,
                self.settings.default_model,
            )

            messages = [
                {"role": "system", "content": "You are a precise task analyzer. Respond only with valid JSON."},
                {"role": "user", "content": analysis_prompt},
            ]

            response = await llm.ainvoke(messages)
            response_text = normalize_response_for_json(response)

            try:
                data = json.loads(response_text)
                intent_analysis = IntentAnalysis(**data)
            except (json.JSONDecodeError, TypeError) as e:
                # Try extracting JSON from within the response (LLM may add prose)
                import re as _re
                json_match = _re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    try:
                        data = json.loads(json_match.group())
                        intent_analysis = IntentAnalysis(**data)
                        _logger.info("intent_parse_recovered_from_prose")
                    except (json.JSONDecodeError, TypeError) as e2:
                        _logger.warning("intent_parse_failed", raw_response=response_text[:500], error=str(e2))
                        intent_analysis = IntentAnalysis(
                            user_intent=message,
                            recommended_agent=AgentType.ANALYST,
                            formulated_objective=message,
                            confidence=0.5,
                            execution_strategy=ExecutionStrategy.SINGLE_AGENT,
                        )
                else:
                    _logger.warning("intent_parse_failed_no_json", raw_response=response_text[:500], error=str(e))
                    intent_analysis = IntentAnalysis(
                        user_intent=message,
                        recommended_agent=AgentType.ANALYST,
                        formulated_objective=message,
                        confidence=0.5,
                        execution_strategy=ExecutionStrategy.SINGLE_AGENT,
                    )

            _logger.info(
                "intent_analyzed",
                intent=intent_analysis.user_intent,
                agent=intent_analysis.recommended_agent.value,
                strategy=intent_analysis.execution_strategy.value,
                confidence=intent_analysis.confidence,
            )
            return intent_analysis

        except Exception as exc:
            _logger.error("intent_analysis_failed", error=str(exc))
            return IntentAnalysis(
                user_intent=message,
                recommended_agent=AgentType.CODER,
                formulated_objective=message,
                confidence=0.3,
                execution_strategy=ExecutionStrategy.SINGLE_AGENT,
            )

    async def route_message_strategy(
        self,
        message: str,
        session: OrchestratorSession | None = None,
        folder_path: str | None = None,
    ) -> WorkflowRouteDecision:
        """Route message using LLM intent analysis.

        Router responsibility ends at strategy + target identity. Chain or graph
        variant resolution happens in the planner layer.
        """
        if session is None:
            session = OrchestratorSession(user_intent=message)

        session_context = session.session_checkpoints[-1] if session.session_checkpoints else ""
        if folder_path:
            intent = await self.analyze_intent_with_llm(
                message,
                session_context,
                folder_path=folder_path,
                has_folder_path=True,
            )
        else:
            intent = await self.analyze_intent_with_llm(message, session_context)

        specialist = None
        with suppress(ValueError):
            if intent.recommended_specialist:
                specialist = SpecialistType(intent.recommended_specialist)

        # --- DIRECT_RESPONSE: Orchestrator answers itself ---
        if intent.execution_strategy == ExecutionStrategy.DIRECT_RESPONSE:
            _logger.info("orchestrator_direct_response", intent=intent.user_intent)
            return WorkflowRouteDecision(
                rationale="Orchestrator answering directly — no delegation needed.",
                agent_role=AgentType.ORCHESTRATOR,
                specialist=specialist,
                task=message,
                thinking=ThinkingLevel.MEDIUM,
                priority=Priority.NORMAL,
                execution_strategy=ExecutionStrategy.DIRECT_RESPONSE,
                tools=self._get_tools_for_agent(AgentType.ORCHESTRATOR),
                confidence=intent.confidence,
            )

        # --- CHAIN: planner resolves the concrete chain ---
        if intent.execution_strategy == ExecutionStrategy.CHAIN:
            target_role = (
                intent.recommended_agent
                if intent.recommended_agent != AgentType.ORCHESTRATOR
                else AgentType.ANALYST
            )
            _logger.info("orchestrator_chain", target_role=target_role.value)
            return WorkflowRouteDecision(
                rationale="Multi-step execution required; planner will resolve the concrete workflow.",
                agent_role=target_role,
                specialist=specialist,
                task=intent.formulated_objective or intent.user_intent or message,
                thinking=ThinkingLevel.HIGH,
                tools=self._get_tools_for_agent(target_role, specialist),
                priority=Priority.HIGH,
                execution_strategy=ExecutionStrategy.CHAIN,
                confidence=intent.confidence,
            )

        # --- GRAPH: planner/executor resolve the concrete graph ---
        if intent.execution_strategy == ExecutionStrategy.GRAPH:
            target_role = (
                intent.recommended_agent
                if intent.recommended_agent != AgentType.ORCHESTRATOR
                else AgentType.ANALYST
            )
            return WorkflowRouteDecision(
                rationale="Graph execution selected; planner will resolve the concrete graph runtime.",
                agent_role=target_role,
                specialist=specialist,
                task=intent.formulated_objective or intent.user_intent or message,
                thinking=ThinkingLevel.HIGH,
                tools=self._get_tools_for_agent(target_role, specialist),
                priority=Priority.HIGH,
                execution_strategy=ExecutionStrategy.GRAPH,
                confidence=intent.confidence,
            )

        # --- SINGLE_AGENT or multi-agent (both route to single_agent decision) ---
        if intent.is_multi_agent and intent.agent_sequence:
            target_agent = intent.agent_sequence[0]
            rationale = (
                f"Multi-agent task: starting with {target_agent.value}. "
                f"Sequence: {[a.value for a in intent.agent_sequence]}"
            )
        else:
            target_agent = intent.recommended_agent
            rationale = (
                f"Delegating to {target_agent.value} "
                f"(confidence: {intent.confidence:.0%})"
            )

        _logger.info("orchestrator_single_agent", agent=target_agent.value, rationale=rationale)

        return WorkflowRouteDecision(
            rationale=rationale,
            agent_role=target_agent,
            specialist=specialist,
            task=intent.formulated_objective or message,
            thinking=ThinkingLevel.HIGH,
            tools=self._get_tools_for_agent(target_agent, specialist),
            priority=Priority.NORMAL,
            execution_strategy=ExecutionStrategy.SINGLE_AGENT,
            confidence=intent.confidence,
        )

    async def route_message_intelligently(
        self,
        message: str,
        session: OrchestratorSession | None = None,
        folder_path: str | None = None,
    ) -> OrchestratorDecision:
        """Compatibility helper that returns the final executor plan."""
        from mindflow_backend.orchestrator.chain_integration import plan_orchestrator_execution

        route = await self.route_message_strategy(
            message,
            session=session,
            folder_path=folder_path,
        )
        return plan_orchestrator_execution(
            message=message,
            route=route,
            folder_path=folder_path,
        )

    def _get_tools_for_agent(
        self,
        agent_type: AgentType,
        specialist: SpecialistType | None = None,
    ) -> list[ToolScope]:
        """Get tool scopes from the canonical runtime policy."""
        policy = get_agent_runtime_policy(agent_type, specialist=specialist)
        return list(policy.tools)


# Global router instance
_intelligent_router: IntelligentRouter | None = None


def get_intelligent_router() -> IntelligentRouter:
    """Get or create the global intelligent router instance."""
    global _intelligent_router
    if _intelligent_router is None:
        from mindflow_backend.orchestrator.delegation_engine import get_delegation_engine
        _intelligent_router = IntelligentRouter(get_delegation_engine())
    return _intelligent_router


async def route_message_intelligently(
    message: str,
    session: OrchestratorSession | None = None,
    folder_path: str | None = None,
) -> OrchestratorDecision:
    """Route a user message using LLM intent analysis (no keyword routing)."""
    router = get_intelligent_router()
    return await router.route_message_intelligently(message, session, folder_path=folder_path)
