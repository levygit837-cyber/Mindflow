"""Session Review Agent for context governance and memory management.

Specialized agent that reviews session windows, extracts actions,
generates insights, and creates structured documentation for
future context retrieval by other agents.
Refactored to use modular architecture with dependency injection.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from omnimind_backend.agents._base import BaseAgent
from omnimind_backend.agents.core.interfaces import ContentAnalyzer, ResultParser
from omnimind_backend.agents.core.exceptions import SessionReviewError
from omnimind_backend.infra.config import get_settings
from omnimind_backend.infra.logging import get_logger
from omnimind_backend.agents.review.analyzer import get_session_review_analyzer
from omnimind_backend.agents.review.parser import get_session_review_parser
from omnimind_backend.schemas.session.review import (
    ActionDocumentation,
    ContextInsight,
    ReviewExecutionContext,
    ReviewTask,
    SessionReviewAgent,
    SessionReviewResult,
    WindowSize,
)

_logger = get_logger(__name__)


class SessionReviewAgentImplementation(BaseAgent):
    """Specialized agent for reviewing session windows and extracting context.
    Refactored to use modular components.
    """
    
    def __init__(
        self,
        analyzer: ContentAnalyzer | None = None,
        parser: ResultParser | None = None,
    ) -> None:
        super().__init__()
        self.agent_config = SessionReviewAgent()
        self.settings = get_settings()
        self.analyzer = analyzer or get_session_review_analyzer()
        self.parser = parser or get_session_review_parser()
        
    @property
    def agent_type(self) -> str:
        return "session_reviewer"
    
    @property
    def system_prompt(self) -> str:
        return """You are a Session Review Agent, specialized in analyzing agent conversations 
and extracting structured documentation of actions, decisions, and insights.

Your primary responsibilities:
1. Extract and document specific actions taken by agents
2. Identify key insights and patterns from the conversation
3. Generate comprehensive summaries of token windows
4. Create structured documentation for future context retrieval

Focus on:
- Concrete actions (file modifications, commands executed, code written)
- Decision points and reasoning
- Outcomes and results
- Dependencies and relationships
- Patterns and recurring themes

Be thorough but concise. Your documentation will be used by other agents 
to understand what happened in earlier parts of long conversations.

Always structure your output in the requested format and include specific
details that would be valuable for future context reconstruction."""
    
    async def review_session_window(
        self,
        task: ReviewTask,
        context: ReviewExecutionContext,
    ) -> SessionReviewResult:
        """Perform a comprehensive review of a session window."""
        try:
            _logger.info(
                "session_review_started_modular",
                task_id=str(task.task_id),
                session_id=str(task.session_id),
                window_range=context.window_range,
            )
            
            start_time = datetime.now(UTC)
            
            # Analyze session content using modular analyzer
            analysis_content = await self.analyzer.analyze_window(context)
            
            # Parse analysis into structured results using modular parser
            result = await self._parse_analysis_response(
                task=task,
                context=context,
                analysis_content=analysis_content,
                start_time=start_time,
            )
            
            _logger.info(
                "session_review_completed_modular",
                task_id=str(task.task_id),
                actions_extracted=len(result.actions_documented),
                insights_extracted=len(result.insights_extracted),
                processing_time=result.processing_time_seconds,
            )
            
            return result
            
        except Exception as exc:
            _logger.error(
                "session_review_failed_modular",
                task_id=str(task.task_id),
                error=str(exc),
            )
            raise SessionReviewError(
                f"Session review failed: {exc}",
                session_id=str(task.session_id),
                task_id=str(task.task_id)
            )
    
    def _prepare_analysis_messages(self, context: ReviewExecutionContext) -> list[BaseMessage]:
        """Prepare messages for LLM analysis."""
        system_prompt = self.system_prompt
        
        # Add specific instructions based on task requirements
        task_instructions = self._generate_task_instructions(context)
        system_prompt += f"\n\n{task_instructions}"
        
        # Prepare context from session messages
        context_content = self._format_session_context(context)
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"""
Please analyze the following session window (tokens {context.window_range[0]}-{context.window_range[1]}):

{context_content}

Extract and document:
1. All specific actions taken by agents
2. Key insights and patterns
3. Important decisions and outcomes
4. Dependencies and relationships

Provide your analysis in a structured format that can be parsed programmatically.
            """)
        ]
        
        return messages
    
    def _generate_task_instructions(self, context: ReviewExecutionContext) -> str:
        """Generate specific instructions based on task requirements."""
        instructions = []
        
        instructions.append(f"Window Size: {context.get_window_size()} tokens")
        instructions.append(f"Time Limit: {context.time_limit_minutes} minutes")
        instructions.append(f"Quality Threshold: {context.quality_threshold}")
        
        if context.agent_capabilities:
            instructions.append(f"Agent Capabilities: {', '.join(context.agent_capabilities)}")
        
        return "\n".join(instructions)
    
    def _format_session_context(self, context: ReviewExecutionContext) -> str:
        """Format session messages for analysis."""
        if not context.session_messages:
            return "No session messages available for analysis."
        
        formatted_messages = []
        for i, msg in enumerate(context.session_messages):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            
            # Truncate very long messages for analysis
            if len(content) > 2000:
                content = content[:2000] + "... [truncated]"
            
            formatted_messages.append(f"[{i+1}] {role.upper()}: {content}")
        
        return "\n\n".join(formatted_messages)
    
    async def _parse_analysis_response(
        self,
        task: ReviewTask,
        context: ReviewExecutionContext,
        analysis_content: str,
        start_time: datetime,
    ) -> SessionReviewResult:
        """Parse LLM analysis into structured SessionReviewResult using modular parser."""
        from uuid import uuid4
        
        result = SessionReviewResult(
            review_id=uuid4(),
            session_id=task.session_id,
            window_range=context.window_range,
            window_index=task.window_index,
            review_config_id=uuid4(),  # TODO: Get from actual config
            reviewer_agent_id=self.agent_type,
            trigger_reason="automatic_threshold",
        )
        
        # Extract actions using modular parser
        result.actions_documented = self.parser.parse_actions(
            analysis_content, task.session_id, context.window_range
        )
        
        # Extract insights using modular parser
        result.insights_extracted = self.parser.parse_insights(
            analysis_content, task.session_id, context.window_range
        )
        
        # Extract summary using parser
        result.summary_text = self.parser.parse_summary(analysis_content)
        
        # Calculate metrics
        end_time = datetime.now(UTC)
        result.processing_time_seconds = (end_time - start_time).total_seconds()
        result.total_actions = len(result.actions_documented)
        result.total_insights = len(result.insights_extracted)
        result.completed_at = end_time
        
        # Calculate quality scores
        result.confidence_score = self._calculate_confidence_score(
            analysis_content, result.total_actions, result.total_insights
        )
        result.completeness_score = self._calculate_completeness_score(
            context.get_window_size(), result.total_actions, result.total_insights
        )
        result.relevance_score = self._calculate_relevance_score(
            result.actions_documented, result.insights_extracted
        )
        
        return result
    
    def _generate_task_instructions(self, context: ReviewExecutionContext) -> str:
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
    
    def _format_session_context(self, context: ReviewExecutionContext) -> str:
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
    
    def _calculate_confidence_score(
        self,
        analysis_content: str,
        actions_count: int,
        insights_count: int,
    ) -> float:
        """Calculate confidence score for the review."""
        base_score = 0.5
        
        # More structured content increases confidence
        if "Action:" in analysis_content:
            base_score += 0.1
        if "Insight:" in analysis_content:
            base_score += 0.1
        if "Summary:" in analysis_content:
            base_score += 0.1
        
        # Balance of actions and insights
        if actions_count > 0 and insights_count > 0:
            base_score += 0.1
        
        # Length of analysis (longer = more detailed)
        if len(analysis_content) > 500:
            base_score += 0.1
        
        return min(base_score, 1.0)
    
    def _calculate_completeness_score(
        self,
        window_size: int,
        actions_count: int,
        insights_count: int,
    ) -> float:
        """Calculate completeness score based on extraction results."""
        # Expected minimums based on window size
        expected_actions = max(1, window_size // 5000)  # 1 action per 5K tokens
        expected_insights = max(1, window_size // 10000)  # 1 insight per 10K tokens
        
        action_score = min(actions_count / expected_actions, 1.0) if expected_actions > 0 else 0.5
        insight_score = min(insights_count / expected_insights, 1.0) if expected_insights > 0 else 0.5
        
        return (action_score + insight_score) / 2
    
    def _calculate_relevance_score(
        self,
        actions: list[ActionDocumentation],
        insights: list[ContextInsight],
    ) -> float:
        """Calculate relevance score based on quality of extractions."""
        if not actions and not insights:
            return 0.0
        
        # Average confidence scores
        action_confidence = sum(a.confidence_score for a in actions) / len(actions) if actions else 0.5
        insight_importance = sum(i.importance_score for i in insights) / len(insights) if insights else 0.5
        
        return (action_confidence + insight_importance) / 2


# Global instance
_session_review_agent: SessionReviewAgentImplementation | None = None


def get_session_review_agent() -> SessionReviewAgentImplementation:
    """Get or create a global session review agent instance."""
    global _session_review_agent
    if _session_review_agent is None:
        _session_review_agent = SessionReviewAgentImplementation()
    return _session_review_agent
