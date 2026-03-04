"""Content analyzer for session review.

Provides content analysis capabilities for extracting
meaningful information from session data.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List
from datetime import UTC, datetime

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from omnimind_backend.agents.core.interfaces import ContentAnalyzer
from omnimind_backend.agents.core.exceptions import ContentAnalysisError
from omnimind_backend.infra.logging import get_logger
from omnimind_backend.runtime.providers import get_model_for_provider
from omnimind_backend.config.agents import get_agent_config

_logger = get_logger(__name__)


class SessionReviewContentAnalyzer(ContentAnalyzer):
    """Analyzes session content for review and documentation."""
    
    def __init__(self, model_provider: str | None = None, model_name: str | None = None):
        self.model_provider = model_provider or "openai"
        self.model_name = model_name or "gpt-3.5-turbo"
        self.config = get_agent_config()
    
    async def analyze_window(
        self,
        context: Any,  # ReviewExecutionContext
    ) -> str:
        """Analyze session window and extract insights."""
        try:
            _logger.info(
                "session_review_analysis_started",
                session_id=getattr(context, 'session_id', 'unknown'),
                window_range=getattr(context, 'window_range', (0, 0))
            )
            
            start_time = datetime.now(UTC)
            
            # Prepare messages for LLM analysis
            messages = self._prepare_analysis_messages(context)
            
            # Get model for analysis
            llm = get_model_for_provider(self.model_provider, self.model_name)
            
            # Generate analysis with timeout
            try:
                response = await asyncio.wait_for(
                    llm.ainvoke(messages),
                    timeout=self.config.review_quality_threshold * 60  # Convert to seconds
                )
                analysis_content = response.content
            except asyncio.TimeoutError:
                _logger.warning("analysis_timeout", session_id=getattr(context, 'session_id'))
                analysis_content = self._generate_fallback_analysis(context)
            
            processing_time = (datetime.now(UTC) - start_time).total_seconds()
            
            _logger.info(
                "session_review_analysis_completed",
                session_id=getattr(context, 'session_id', 'unknown'),
                analysis_length=len(analysis_content),
                processing_time=processing_time
            )
            
            return analysis_content
        
        except Exception as e:
            _logger.error("session_review_analysis_failed", error=str(e))
            raise ContentAnalysisError(
                f"Session review analysis failed: {e}",
                session_id=getattr(context, 'session_id', None),
                window_range=getattr(context, 'window_range', None)
            )
    
    def _prepare_analysis_messages(self, context: Any) -> List[BaseMessage]:
        """Prepare messages for LLM analysis."""
        system_prompt = self._build_system_prompt()
        
        # Add specific instructions based on task requirements
        task_instructions = self._generate_task_instructions(context)
        system_prompt += f"\n\n{task_instructions}"
        
        # Prepare context from session messages
        context_content = self._format_session_context(context)
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"""
Please analyze the following session window (tokens {getattr(context, 'window_range', (0, 0))[0]}-{getattr(context, 'window_range', (0, 0))[1]}):

{context_content}

Extract and document:
1. All specific actions taken by agents
2. Key insights and patterns
3. Important decisions and outcomes
4. Dependencies and relationships
5. Issues or problems identified

Provide your analysis in this structured format:

## Actions
- **Action Type**: Description of the action
- **Files Modified**: List of files affected (if any)
- **Commands Executed**: List of commands run (if any)

## Insights
- **Insight Type**: Description of the insight
- **Importance**: High/Medium/Low
- **Evidence**: Supporting information

## Decisions
- **Decision**: Description of the decision made
- **Rationale**: Reasoning behind the decision
- **Impact**: High/Medium/Low

## Dependencies
- **Dependency**: Description of the dependency
- **Type**: Internal/External/Data
- **Criticality**: Critical/Important/Optional

## Summary
[Brief summary of the window's key points and outcomes]
            """)
        ]
        
        return messages
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for session review analysis."""
        return """You are a Session Review Agent, specialized in analyzing agent conversations 
and extracting structured documentation of actions, decisions, and insights.

Your primary responsibilities:
1. Extract and document specific actions taken by agents
2. Identify key insights and patterns from the conversation
3. Generate comprehensive summaries of token windows
4. Create structured documentation for future context retrieval
5. Identify issues, problems, or blockers encountered

Focus on:
- Concrete actions (file modifications, commands executed, code written)
- Decision points and reasoning
- Outcomes and results
- Dependencies and relationships
- Patterns and recurring themes
- Issues or problems that arose
- Solutions implemented

Be thorough but concise. Your documentation will be used by other agents 
to understand what happened in earlier parts of long conversations.

Always structure your output clearly with the requested sections.
Provide specific, actionable information that would be valuable for future context reconstruction."""
    
    def _generate_task_instructions(self, context: Any) -> str:
        """Generate specific instructions based on task requirements."""
        instructions = []
        
        window_size = getattr(context, 'get_window_size', lambda: 0)()
        if window_size > 0:
            instructions.append(f"Window Size: {window_size} tokens")
        
        time_limit = getattr(context, 'time_limit_minutes', 10)
        instructions.append(f"Time Limit: {time_limit} minutes")
        
        quality_threshold = getattr(context, 'quality_threshold', 0.8)
        instructions.append(f"Quality Threshold: {quality_threshold}")
        
        agent_capabilities = getattr(context, 'agent_capabilities', [])
        if agent_capabilities:
            instructions.append(f"Agent Capabilities: {', '.join(agent_capabilities)}")
        
        return "\\n".join(instructions)
    
    def _format_session_context(self, context: Any) -> str:
        """Format session messages for analysis."""
        session_messages = getattr(context, 'session_messages', [])
        
        if not session_messages:
            return "No session messages available for analysis."
        
        formatted_messages = []
        for i, msg in enumerate(session_messages):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            
            # Truncate very long messages for analysis
            max_content_length = 2000
            if len(content) > max_content_length:
                content = content[:max_content_length] + f"... [truncated, was {len(content)} chars]"
            
            # Add timestamp if available
            timestamp = msg.get("timestamp", "")
            if timestamp:
                formatted_messages.append(f"[{i+1}] {role.upper()} ({timestamp}): {content}")
            else:
                formatted_messages.append(f"[{i+1}] {role.upper()}: {content}")
        
        return "\\n\\n".join(formatted_messages)
    
    def _generate_fallback_analysis(self, context: Any) -> str:
        """Generate fallback analysis when LLM fails or times out."""
        session_messages = getattr(context, 'session_messages', [])
        
        if not session_messages:
            return "## Summary\\nNo session messages available for analysis."
        
        # Simple heuristic analysis
        actions = []
        insights = []
        decisions = []
        dependencies = []
        
        for msg in session_messages:
            content = msg.get("content", "").lower()
            role = msg.get("role", "unknown")
            
            # Extract actions based on keywords
            if any(word in content for word in ["created", "updated", "deleted", "implemented", "fixed"]):
                actions.append(f"- **{role}**: Action detected in message")
            
            # Extract insights based on keywords
            if any(word in content for word in ["noticed", "observed", "found", "discovered"]):
                insights.append(f"- **{role}**: Insight detected in message")
            
            # Extract decisions based on keywords
            if any(word in content for word in ["decided", "chose", "selected", "agreed"]):
                decisions.append(f"- **{role}**: Decision detected in message")
            
            # Extract dependencies based on keywords
            if any(word in content for word in ["depends", "requires", "needs", "relies"]):
                dependencies.append(f"- **{role}**: Dependency detected in message")
        
        fallback_content = "## Fallback Analysis\\n\\n"
        
        if actions:
            fallback_content += "## Actions\\n" + "\\n".join(actions[:5]) + "\\n\\n"
        
        if insights:
            fallback_content += "## Insights\\n" + "\\n".join(insights[:3]) + "\\n\\n"
        
        if decisions:
            fallback_content += "## Decisions\\n" + "\\n".join(decisions[:3]) + "\\n\\n"
        
        if dependencies:
            fallback_content += "## Dependencies\\n" + "\\n".join(dependencies[:3]) + "\\n\\n"
        
        fallback_content += "## Summary\\n"
        fallback_content += f"Analysis based on {len(session_messages)} messages. "
        fallback_content += "This is a fallback analysis due to processing constraints."
        
        return fallback_content
    
    def calculate_quality_metrics(
        self,
        analysis_content: str,
        processing_time: float,
        window_size: int,
    ) -> Dict[str, float]:
        """Calculate quality metrics for the analysis."""
        metrics = {}
        
        # Completeness score based on sections present
        sections = ["actions", "insights", "decisions", "dependencies", "summary"]
        sections_found = sum(
            1 for section in sections 
            if section.lower() in analysis_content.lower()
        )
        metrics["completeness"] = sections_found / len(sections)
        
        # Thoroughness score based on content length
        expected_min_length = 200
        if window_size > 0:
            expected_min_length = min(200, window_size // 50)  # Scale with window size
        
        metrics["thoroughness"] = min(len(analysis_content) / expected_min_length, 1.0)
        
        # Timeliness score (faster is better up to a point)
        expected_max_time = 30  # seconds
        metrics["timeliness"] = max(0, 1.0 - (processing_time / expected_max_time))
        
        # Structure score based on formatting
        structure_indicators = ["##", "**", "- ", ":", "\\n"]
        structure_score = sum(
            analysis_content.count(indicator) for indicator in structure_indicators
        )
        metrics["structure"] = min(structure_score / 20, 1.0)  # Normalize
        
        # Overall quality score
        metrics["overall"] = sum(metrics.values()) / len(metrics)
        
        return metrics


# Global analyzer instance
_analyzer: SessionReviewContentAnalyzer | None = None


def get_session_review_analyzer() -> SessionReviewContentAnalyzer:
    """Get the global session review analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = SessionReviewContentAnalyzer()
    return _analyzer
