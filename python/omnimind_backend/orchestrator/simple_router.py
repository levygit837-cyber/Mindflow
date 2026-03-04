"""Simple Intelligent Router — Basic LLM-powered routing without external dependencies.

Temporary implementation that replaces keyword matching with intelligent intent analysis
using only the existing infrastructure without langchain/langgraph dependencies.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from omnimind_backend.agents._registry import get_agent
from omnimind_backend.infra.config import get_settings
from omnimind_backend.infra.logging import get_logger
from omnimind_backend.runtime.providers import get_model_for_provider
from omnimind_backend.schemas.orchestration.delegation import (
    DelegationTask,
    DelegationResult,
    OrchestratorSession,
)
from omnimind_backend.schemas.orchestration.orchestrator import (
    AgentType,
    OrchestratorDecision,
    Priority,
    ThinkingLevel,
    ToolScope,
)

_logger = get_logger(__name__)


class SimpleIntentAnalysis(BaseModel):
    """Simplified result of intent analysis."""
    
    user_intent: str = Field(description="Clear interpretation of what user wants to accomplish")
    needs_code_context: bool = Field(description="Whether we need codebase context to decide")
    recommended_agent: AgentType = Field(description="Which agent should handle this")
    formulated_objective: str = Field(description="Precise objective for the target agent")
    confidence: float = Field(description="Confidence in this analysis (0-1)")


class SimpleIntelligentRouter:
    """Simplified LLM-powered intelligent routing."""
    
    def __init__(self):
        self.settings = get_settings()
        
    async def analyze_intent_with_llm(
        self, 
        message: str, 
        session_context: str = ""
    ) -> SimpleIntentAnalysis:
        """Use LLM to analyze user intent and recommend actions."""
        
        # Create the intent analysis prompt
        analysis_prompt = f"""You are an intelligent task analyzer. Analyze this user request and determine:

1. What the user actually wants to accomplish
2. Whether you need codebase context to make good decisions  
3. Which specialized agent should handle this

User Request: {message}

Session Context: {session_context if session_context else "No previous context"}

Available Agents:
- CODER: Implementation, bug fixes, refactoring, code generation, testing
- ANALYST: Code analysis, structure mapping, context collection, flow tracing
- RESEARCHER: Web search, documentation lookup, technology comparison
- CRITIC: Code review, quality evaluation, best practice assessment, brainstorming
- SECURITY_GUARD: Security audit, vulnerability detection, compliance

Respond ONLY with a JSON object:
{{
    "user_intent": "clear interpretation",
    "needs_code_context": true/false,
    "recommended_agent": "CODER|ANALYST|RESEARCHER|CRITIC|SECURITY_GUARD",
    "formulated_objective": "precise objective",
    "confidence": 0.0-1.0
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
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Parse JSON response manually
            import json
            try:
                data = json.loads(response_text)
                intent_analysis = SimpleIntentAnalysis(**data)
            except (json.JSONDecodeError, TypeError) as e:
                _logger.warning("intent_parse_failed", error=str(e))
                # Fallback to basic analysis
                intent_analysis = SimpleIntentAnalysis(
                    user_intent=message,
                    needs_code_context=self._needs_context_for_message(message),
                    recommended_agent=self._guess_agent_from_message(message),
                    formulated_objective=message,
                    confidence=0.3,
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
            return SimpleIntentAnalysis(
                user_intent=message,
                needs_code_context=self._needs_context_for_message(message),
                recommended_agent=self._guess_agent_from_message(message),
                formulated_objective=message,
                confidence=0.3,
            )
    
    def _needs_context_for_message(self, message: str) -> bool:
        """Simple heuristic to determine if code context is needed."""
        message_lower = message.lower()
        context_keywords = [
            "analyze", "analysis", "understand", "explain", "how does", "architecture",
            "structure", "flow", "implement", "fix", "bug", "error", "refactor"
        ]
        return any(keyword in message_lower for keyword in context_keywords)
    
    def _guess_agent_from_message(self, message: str) -> AgentType:
        """Simple heuristic to guess agent from message."""
        message_lower = message.lower()
        
        # Agent keyword mappings (simplified version)
        agent_keywords = {
            AgentType.CODER: ["code", "implement", "fix", "bug", "debug", "refactor", "function", "class"],
            AgentType.ANALYST: ["analyze", "analysis", "understand", "explain", "how does", "architecture", "structure"],
            AgentType.RESEARCHER: ["research", "search", "find", "documentation", "docs", "tutorial"],
            AgentType.CRITIC: ["review", "critique", "evaluate", "improve", "feedback", "quality", "brainstorm", "ideate", "alternative"],
            AgentType.SECURITY_GUARD: ["security", "vulnerability", "cve", "owasp", "audit"],
        }
        
        # Score each agent
        scores = {}
        for agent_type, keywords in agent_keywords.items():
            score = sum(1 for keyword in keywords if keyword in message_lower)
            if score > 0:
                scores[agent_type] = score
        
        if scores:
            return max(scores, key=scores.get)
        return AgentType.CODER  # Default fallback
    
    async def route_message_intelligently(
        self,
        message: str,
        session: OrchestratorSession | None = None,
    ) -> OrchestratorDecision:
        """Route message using intelligent LLM analysis."""
        
        # Create or get session
        if session is None:
            session = OrchestratorSession(
                user_intent=message,
            )
        
        # Step 1: Analyze intent with LLM
        session_context = session.session_checkpoints[-1] if session.session_checkpoints else ""
        intent_analysis = await self.analyze_intent_with_llm(message, session_context)
        
        # Step 2: Get code context if needed
        if intent_analysis.needs_code_context:
            _logger.info(
                "delegating_to_analyst_for_context",
                objective="Analyze codebase for context",
            )
            # For now, skip actual Analyst delegation and proceed
            # TODO: Implement full Analyst delegation in Phase 2
            session.session_checkpoints.append(
                f"Context needed: {intent_analysis.user_intent}"
            )
        
        # Step 3: Create decision
        decision = OrchestratorDecision(
            rationale=f"Intelligent routing selected {intent_analysis.recommended_agent.value} "
                     f"(confidence: {intent_analysis.confidence:.2f})",
            agent=intent_analysis.recommended_agent,
            task=intent_analysis.formulated_objective,
            thinking=ThinkingLevel.HIGH,
            tools=self._get_tools_for_agent(intent_analysis.recommended_agent),
            priority=Priority.NORMAL,
        )
        
        # Store in session
        session.delegation_log.append({
            "agent": intent_analysis.recommended_agent.value,
            "objective": intent_analysis.formulated_objective,
            "status": "routed",
            "confidence": intent_analysis.confidence,
        })
        
        return decision
    
    def _get_tools_for_agent(self, agent_type: AgentType) -> list[ToolScope]:
        """Get appropriate tools for an agent type."""
        tool_mapping = {
            AgentType.CODER: [ToolScope.FILESYSTEM, ToolScope.SHELL],
            AgentType.ANALYST: [ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM],
            AgentType.RESEARCHER: [ToolScope.WEB_SEARCH],
            AgentType.CRITIC: [ToolScope.CODE_ANALYSIS],
            AgentType.SECURITY_GUARD: [ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM],
            AgentType.ORCHESTRATOR: [],  # Orchestrator doesn't use tools directly
        }
        return tool_mapping.get(agent_type, [])


# Global router instance
_simple_intelligent_router: SimpleIntelligentRouter | None = None


def get_simple_intelligent_router() -> SimpleIntelligentRouter:
    """Get or create the global simple intelligent router instance."""
    global _simple_intelligent_router
    if _simple_intelligent_router is None:
        _simple_intelligent_router = SimpleIntelligentRouter()
    return _simple_intelligent_router


async def route_message_intelligently(
    message: str,
    session: OrchestratorSession | None = None,
) -> OrchestratorDecision:
    """Route a user message using intelligent LLM analysis.
    
    This replaces the old keyword-based routing with intelligent intent analysis.
    """
    router = get_simple_intelligent_router()
    return await router.route_message_intelligently(message, session)
