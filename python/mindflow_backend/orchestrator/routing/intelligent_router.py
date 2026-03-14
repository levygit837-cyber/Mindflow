"""Intelligent Orchestrator Router — LLM-powered intent analysis and delegation.

Replaces keyword-based routing with intelligent intent analysis using LLM.
Orchestrator analyzes user message, delegates to Analyst for context when needed,
then makes informed delegation decisions based on structured findings.
"""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from mindflow_backend.agents._registry import get_agent
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.orchestrator.delegation_engine import DelegationEngine
from mindflow_backend.runtime import get_model_for_provider, normalize_response_for_json
from mindflow_backend.schemas.orchestration.delegation import (
    DelegationTask,
    DelegationResult,
    OrchestratorSession,
)
from mindflow_backend.schemas.orchestration.orchestrator import (
    AgentType,
    ChainType,
    ExecutionStrategy,
    OrchestratorDecision,
    Priority,
    ThinkingLevel,
    ToolScope,
)

_logger = get_logger(__name__)


class IntentAnalysis(BaseModel):
    """Result of LLM intent analysis."""

    user_intent: str = Field(description="Clear interpretation of what user wants to accomplish")
    needs_code_context: bool = Field(description="Whether we need codebase context to decide")
    context_needed: str = Field(description="What specific context we need from Analyst")
    suggested_scope: list[str] = Field(default_factory=list, description="Suggested files/modules to analyze")
    recommended_agent: AgentType = Field(description="Which agent should handle this")
    formulated_objective: str = Field(description="Precise objective for the target agent")
    confidence: float = Field(description="Confidence in this analysis (0-1)")
    is_multi_agent: bool = Field(default=False, description="Requires multiple agents")
    agent_sequence: list[AgentType] = Field(default_factory=list, description="Sequence of agents needed")

    @field_validator("recommended_agent", mode="before")
    @classmethod
    def normalize_agent(cls, v: str) -> str:
        return v.lower() if isinstance(v, str) else v

    @field_validator("agent_sequence", mode="before")
    @classmethod
    def normalize_agent_sequence(cls, v: list) -> list:
        return [x.lower() if isinstance(x, str) else x for x in (v or [])]
    execution_strategy: ExecutionStrategy = Field(
        default=ExecutionStrategy.SINGLE_AGENT,
        description="How to execute: single agent, chain, or graph",
    )
    suggested_chain_id: str | None = Field(default=None, description="Chain identifier if using CHAIN")
    suggested_chain_type: ChainType | None = Field(default=None, description="Chain type/category")


class IntelligentRouter:
    """LLM-powered intelligent routing with Analyst delegation."""
    
    def __init__(self, delegation_engine: DelegationEngine):
        self.delegation_engine = delegation_engine
        self.settings = get_settings()
        
    async def analyze_intent_with_llm(
        self, 
        message: str, 
        session_context: str = ""
    ) -> IntentAnalysis:
        """Use LLM to analyze user intent and recommend actions."""
        
        # Create the intent analysis prompt
        analysis_prompt = f"""You are an intelligent orchestrator planner. Analyze this user request and determine:
1. What the user actually wants to accomplish
2. Whether you need codebase context to make good decisions
3. What execution strategy to use (SINGLE_AGENT vs CHAIN vs GRAPH)
4. If CHAIN: which chain (and its type)
5. Which specialized agent would be responsible if SINGLE_AGENT
6. If multi-agent is needed, in what sequence

User Request: {message}

Session Context: {session_context if session_context else "No previous context"}

Available Agents:
- CODER: Implementation, bug fixes, refactoring, code generation, testing, architecture decisions
- ANALYST: Code analysis, structure mapping, flow tracing, security audits, code review, brainstorming
- RESEARCHER: Web search, documentation lookup, technology comparison
- ORCHESTRATOR: Session coordination, multi-agent task delegation

Available Chains:
- coding_task (CODING_TASK): Analyst (read/deep) → Coder (write) → Analyst-as-Critic (code review).
  Use for most coding/implementation/refactor tasks where changes are expected.

Respond with a JSON object following this schema:
{{
    "user_intent": "clear interpretation of what user wants to accomplish",
    "needs_code_context": true/false,
    "context_needed": "what specific context we need from Analyst",
    "suggested_scope": ["file1.py", "module2"],
    "recommended_agent": "CODER|ANALYST|RESEARCHER",
    "formulated_objective": "precise objective for the target agent",
    "confidence": 0.0-1.0,
    "is_multi_agent": true/false,
    "agent_sequence": ["AGENT1", "AGENT2"],
    "execution_strategy": "single_agent|chain|graph",
    "suggested_chain_id": "coding_task|null",
    "suggested_chain_type": "coding_task|research|review_only|null"
}}"""
        
        try:
            llm = get_model_for_provider(
                self.settings.default_provider,
                self.settings.default_model
            )
            
            messages = [
                {"role": "system", "content": "You are an intelligent task analyzer. Be precise and structured."},
                {"role": "user", "content": analysis_prompt}
            ]
            
            response = await llm.ainvoke(messages)
            response_text = normalize_response_for_json(response)
            
            # Parse JSON response manually for now
            import json
            try:
                data = json.loads(response_text)
                intent_analysis = IntentAnalysis(**data)
            except (json.JSONDecodeError, TypeError) as e:
                _logger.warning("intent_parse_failed", error=str(e))
                # Fallback to basic analysis
                intent_analysis = IntentAnalysis(
                    user_intent=message,
                    needs_code_context=True,
                    context_needed="General codebase analysis needed",
                    recommended_agent=AgentType.CODER,
                    formulated_objective=message,
                    confidence=0.3,
                    execution_strategy=ExecutionStrategy.CHAIN,
                    suggested_chain_id="coding_task",
                    suggested_chain_type=ChainType.CODING_TASK,
                )
            
            _logger.info(
                "intent_analyzed",
                intent=intent_analysis.user_intent,
                agent=intent_analysis.recommended_agent.value,
                confidence=intent_analysis.confidence,
            )
            
            return intent_analysis
            
        except Exception as exc:
            _logger.error("intent_analysis_failed", error=str(exc))
            # Fallback to CODER with basic analysis
            return IntentAnalysis(
                user_intent=message,
                needs_code_context=True,
                context_needed="General codebase analysis needed",
                recommended_agent=AgentType.CODER,
                formulated_objective=message,
                confidence=0.3,
            )
    
    # -----------------------------------------------------------------------
    # Heuristic fast-path — avoids LLM call for common, unambiguous intents
    # -----------------------------------------------------------------------

    _RESEARCHER_RE = re.compile(
        r"\b(pesquise|search|procure|busque|notícia|noticias|news|latest|"
        r"docs|documentation|o que é|o que é|what is|explain|explique|"
        r"como funciona|how does|tutorial|guia)\b",
        re.IGNORECASE,
    )
    _ANALYST_RE = re.compile(
        r"\b(analise|analyze|review|revisar|audit|auditoria|"
        r"trace|rastrear|map|mapear|diagrama|diagram|"
        r"code review|revisar código|entenda o código)\b",
        re.IGNORECASE,
    )
    _CODER_RE = re.compile(
        r"\b(implement|implemente|crie|create|escreva|write|"
        r"fix|corrija|refactor|refatore|bug|erro|error|"
        r"função|function|class|classe|test|teste|deploy|"
        r"migrat|script|código|code)\b",
        re.IGNORECASE,
    )

    def _try_fast_route(self, message: str) -> OrchestratorDecision | None:
        """Return a routing decision via keywords without an LLM call.

        Returns None when the message is ambiguous and needs LLM routing.
        """
        text = message.strip()
        words = text.split()

        # Greetings / very short conversational messages → CODER (concise assistant)
        # RESEARCHER generates long reports; CODER responds pragmatically to chat.
        if len(words) <= 4:
            return OrchestratorDecision(
                rationale="Short conversational message — routing directly without LLM",
                agent=AgentType.CODER,
                task=text,
                thinking=ThinkingLevel.LOW,
                tools=[],
                priority=Priority.NORMAL,
            )

        if self._ANALYST_RE.search(text):
            return OrchestratorDecision(
                rationale="Keyword match: analysis/review task",
                agent=AgentType.ANALYST,
                task=text,
                thinking=ThinkingLevel.HIGH,
                tools=[],
                priority=Priority.NORMAL,
            )

        if self._RESEARCHER_RE.search(text):
            return OrchestratorDecision(
                rationale="Keyword match: research/documentation task",
                agent=AgentType.RESEARCHER,
                task=text,
                thinking=ThinkingLevel.MEDIUM,
                tools=[],
                priority=Priority.NORMAL,
            )

        if self._CODER_RE.search(text):
            return OrchestratorDecision(
                rationale="Keyword match: coding/implementation task",
                agent=AgentType.CODER,
                task=text,
                thinking=ThinkingLevel.HIGH,
                tools=[],
                priority=Priority.NORMAL,
            )

        return None  # ambiguous → fall through to LLM

    async def route_message_intelligently(
        self,
        message: str,
        session: OrchestratorSession | None = None,
    ) -> OrchestratorDecision:
        """Route message using intelligent LLM analysis and delegation."""

        # Create or get session
        if session is None:
            session = OrchestratorSession(
                user_intent=message,
            )

        # Fast-path: skip LLM for unambiguous intents
        fast_decision = self._try_fast_route(message)
        if fast_decision is not None:
            _logger.info("fast_route_hit", agent=fast_decision.agent.value, message_len=len(message))
            return fast_decision

        analyst_result = None

        # Step 1: Analyze intent with LLM
        session_context = session.session_checkpoints[-1] if session.session_checkpoints else ""
        intent_analysis = await self.analyze_intent_with_llm(message, session_context)
        
        # If strategy is CHAIN, we do not execute here; execute_node will run the chain.
        if intent_analysis.execution_strategy == ExecutionStrategy.CHAIN:
            chain_id = intent_analysis.suggested_chain_id or "coding_task"
            chain_type = intent_analysis.suggested_chain_type or ChainType.CODING_TASK
            return OrchestratorDecision(
                rationale=(
                    "Using chain execution for coding workflow: "
                    "Analyst(read) → Coder(write) → Critic(review)."
                ),
                agent=AgentType.ORCHESTRATOR,
                task=intent_analysis.user_intent,
                thinking=ThinkingLevel.HIGH,
                tools=[],
                priority=Priority.HIGH,
                execution_strategy=ExecutionStrategy.CHAIN,
                chain_id=chain_id,
                chain_type=chain_type,
            )

        # Step 2: Get code context if needed
        if intent_analysis.needs_code_context:
            analyst_task = DelegationTask(
                agent=AgentType.ANALYST,
                objective=intent_analysis.context_needed,
                scope=intent_analysis.suggested_scope,
                expected_output="Structured findings about relevant code, architecture, and dependencies",
                context_from_session=session_context,
                priority=Priority.HIGH,
            )
            
            _logger.info(
                "delegating_to_analyst",
                objective=analyst_task.objective,
                scope=analyst_task.scope,
            )
            
            analyst_result = await self.delegation_engine.delegate_task(analyst_task, session)
            
            if analyst_result.status == "completed":
                # Integrate analyst findings into session
                session.session_checkpoints.append(
                    f"Analyst findings: {analyst_result.key_findings}"
                )
                _logger.info(
                    "analyst_completed",
                    findings_len=len(analyst_result.key_findings),
                    tokens=analyst_result.tokens_consumed,
                )
            else:
                _logger.warning(
                    "analyst_failed",
                    error=analyst_result.error_message,
                )
                # Continue without analyst context
                analyst_result = None
        
        # Step 3: Decide on delegation strategy
        if intent_analysis.is_multi_agent:
            # Multi-agent coordination needed
            return await self._handle_multi_agent_task(intent_analysis, session, analyst_result)
        else:
            # Single agent task
            return await self._handle_single_agent_task(intent_analysis, session, analyst_result)
    
    async def _handle_single_agent_task(
        self,
        intent_analysis: IntentAnalysis,
        session: OrchestratorSession,
        analyst_result: DelegationResult | None = None,
    ) -> OrchestratorDecision:
        """Handle delegation to a single agent."""
        
        # Prepare context from analyst if available
        context_from_analyst = (
            analyst_result.key_findings if analyst_result else ""
        )
        
        # Create the main delegation task
        main_task = DelegationTask(
            agent=intent_analysis.recommended_agent,
            objective=intent_analysis.formulated_objective,
            expected_output=f"Complete solution for: {intent_analysis.user_intent}",
            context_from_session=context_from_analyst,
            priority=Priority.NORMAL,
        )
        
        _logger.info(
            "delegating_to_agent",
            agent=intent_analysis.recommended_agent.value,
            objective=main_task.objective,
        )
        
        # Execute delegation
        result = await self.delegation_engine.delegate_task(main_task, session)
        
        # Create decision based on result
        decision = OrchestratorDecision(
            rationale=f"Intelligent routing selected {intent_analysis.recommended_agent.value} "
                     f"(confidence: {intent_analysis.confidence:.2f})",
            agent=intent_analysis.recommended_agent,
            task=intent_analysis.formulated_objective,
            thinking=ThinkingLevel.HIGH,
            tools=self._get_tools_for_agent(intent_analysis.recommended_agent),
            priority=Priority.NORMAL,
        )
        
        # Store delegation in session
        session.delegation_log.append({
            "agent": intent_analysis.recommended_agent.value,
            "objective": main_task.objective,
            "status": result.status,
            "tokens": result.tokens_consumed,
        })
        
        return decision
    
    async def _handle_multi_agent_task(
        self,
        intent_analysis: IntentAnalysis,
        session: OrchestratorSession,
        analyst_result: DelegationResult | None = None,
    ) -> OrchestratorDecision:
        """Handle multi-agent coordination tasks."""
        
        # For now, start with the first agent in sequence
        # TODO: Implement full multi-agent coordination in Phase 2
        first_agent = intent_analysis.agent_sequence[0]
        
        context_from_analyst = (
            analyst_result.key_findings if analyst_result else ""
        )
        
        first_task = DelegationTask(
            agent=first_agent,
            objective=f"First step in multi-agent task: {intent_analysis.formulated_objective}",
            expected_output="Partial results that will inform next agent in sequence",
            context_from_session=context_from_analyst,
            priority=Priority.HIGH,
        )
        
        _logger.info(
            "starting_multi_agent_sequence",
            sequence=[a.value for a in intent_analysis.agent_sequence],
            first_agent=first_agent.value,
        )
        
        result = await self.delegation_engine.delegate_task(first_task, session)
        
        # Return decision for first agent
        decision = OrchestratorDecision(
            rationale=f"Multi-agent task started with {first_agent.value} "
                     f"(sequence: {[a.value for a in intent_analysis.agent_sequence]})",
            agent=first_agent,
            task=first_task.objective,
            thinking=ThinkingLevel.HIGH,
            tools=self._get_tools_for_agent(first_agent),
            priority=Priority.HIGH,
        )
        
        return decision
    
    def _get_tools_for_agent(self, agent_type: AgentType) -> list[ToolScope]:
        """Get appropriate tools for an agent type."""
        tool_mapping = {
            AgentType.CODER: [ToolScope.FILESYSTEM, ToolScope.SHELL],
            AgentType.ANALYST: [ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM],
            AgentType.RESEARCHER: [ToolScope.WEB_SEARCH],
            AgentType.ORCHESTRATOR: [],  # Orchestrator doesn't use tools directly
        }
        return tool_mapping.get(agent_type, [])


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
) -> OrchestratorDecision:
    """Route a user message using intelligent LLM analysis.
    
    This replaces the old keyword-based routing with intelligent intent analysis.
    """
    router = get_intelligent_router()
    return await router.route_message_intelligently(message, session)
