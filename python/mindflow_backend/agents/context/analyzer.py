"""Content analyzer for context retrieval.

Provides content analysis capabilities for extracting
meaningful information from session data.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List
from uuid import uuid4

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from mindflow_backend.agents.core.interfaces import ContentAnalyzer
from mindflow_backend.agents.core.exceptions import ContentAnalysisError
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.runtime.providers import get_model_for_provider
from mindflow_backend.config.agents import get_agent_config

_logger = get_logger(__name__)


class SessionContentAnalyzer(ContentAnalyzer):
    """Analyzes session content for context extraction."""
    
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
                "content_analysis_started",
                session_id=getattr(context, 'session_id', 'unknown'),
                window_range=getattr(context, 'window_range', (0, 0))
            )
            
            # Prepare messages for LLM analysis
            messages = self._prepare_analysis_messages(context)
            
            # Get model for analysis
            llm = get_model_for_provider(self.model_provider, self.model_name)
            
            # Generate analysis
            response = await llm.ainvoke(messages)
            analysis_content = response.content
            
            _logger.info(
                "content_analysis_completed",
                analysis_length=len(analysis_content)
            )
            
            return analysis_content
        
        except Exception as e:
            _logger.error("content_analysis_failed", error=str(e))
            raise ContentAnalysisError(
                f"Content analysis failed: {e}",
                session_id=getattr(context, 'session_id', None),
                window_range=getattr(context, 'window_range', None)
            )
    
    def _prepare_analysis_messages(self, context: Any) -> List[BaseMessage]:
        """Prepare messages for LLM analysis."""
        system_prompt = self._build_system_prompt()
        
        # Prepare context from session messages
        context_content = self._format_session_context(context)
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"""
Please analyze the following session window:

{context_content}

Extract and document:
1. All specific actions taken by agents
2. Key insights and patterns
3. Important decisions and outcomes
4. Dependencies and relationships

Provide your analysis in a structured format with clear sections for:
- Actions: [List of specific actions]
- Insights: [List of key insights]
- Decisions: [List of important decisions]
- Dependencies: [List of dependencies found]
            """)
        ]
        
        return messages
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for content analysis."""
        return """You are a Content Analysis Agent, specialized in analyzing agent conversations 
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

Always structure your output clearly with:
- Actions: [specific action descriptions]
- Insights: [key insights discovered]
- Decisions: [important decisions made]
- Dependencies: [dependencies identified]"""
    
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
            if len(content) > 2000:
                content = content[:2000] + "... [truncated]"
            
            formatted_messages.append(f"[{i+1}] {role.upper()}: {content}")
        
        return "\n\n".join(formatted_messages)


class ContextExtractor:
    """Extracts structured information from analyzed content."""
    
    def __init__(self):
        self.action_patterns = [
            r"Actions?:\s*(.+?)(?=\n\n|\n[A-Z]|$)",
            r"- \*\*(.+?)\*\*:\s*(.+?)(?=\n-|\n\n|$)",
            r"(\w+)\s+(?:file|code|command):\s*(.+?)(?=\n|$)",
        ]
        
        self.insight_patterns = [
            r"Insights?:\s*(.+?)(?=\n\n|\n[A-Z]|$)",
            r"Key\s+Insights?:\s*(.+?)(?=\n\n|\n[A-Z]|$)",
            r"Pattern\s+Detected:\s*(.+?)(?=\n\n|\n[A-Z]|$)",
        ]
        
        self.decision_patterns = [
            r"Decisions?:\s*(.+?)(?=\n\n|\n[A-Z]|$)",
            r"Important\s+Decisions?:\s*(.+?)(?=\n\n|\n[A-Z]|$)",
        ]
        
        self.dependency_patterns = [
            r"Dependencies?:\s*(.+?)(?=\n\n|\n[A-Z]|$)",
            r"Dependencies\s+Identified:\s*(.+?)(?=\n\n|\n[A-Z]|$)",
        ]
    
    def extract_actions(self, content: str) -> List[Dict[str, Any]]:
        """Extract action information from analyzed content."""
        actions = []
        
        for pattern in self.action_patterns:
            matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
            for match in matches:
                if isinstance(match, tuple):
                    action_type = match[0].strip() if match[0] else "general"
                    description = match[1].strip() if len(match) > 1 else match[0].strip()
                else:
                    action_type = "general"
                    description = match.strip()
                
                action = {
                    "id": str(uuid4()),
                    "type": action_type,
                    "description": description,
                    "files_affected": self._extract_files_from_text(description),
                    "commands_executed": self._extract_commands_from_text(description),
                    "confidence_score": 0.8,
                }
                actions.append(action)
        
        return actions
    
    def extract_insights(self, content: str) -> List[Dict[str, Any]]:
        """Extract insight information from analyzed content."""
        insights = []
        
        for pattern in self.insight_patterns:
            matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
            for match in matches:
                insight_text = match.strip()
                
                insight = {
                    "id": str(uuid4()),
                    "content": insight_text,
                    "type": self._classify_insight_type(insight_text),
                    "importance_score": self._calculate_importance_score(insight_text),
                    "supporting_evidence": self._extract_evidence_from_text(insight_text, content),
                }
                insights.append(insight)
        
        return insights
    
    def extract_decisions(self, content: str) -> List[Dict[str, Any]]:
        """Extract decision information from analyzed content."""
        decisions = []
        
        for pattern in self.decision_patterns:
            matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
            for match in matches:
                decision_text = match.strip()
                
                decision = {
                    "id": str(uuid4()),
                    "description": decision_text,
                    "rationale": self._extract_rationale(decision_text, content),
                    "impact": self._assess_impact(decision_text),
                }
                decisions.append(decision)
        
        return decisions
    
    def extract_dependencies(self, content: str) -> List[Dict[str, Any]]:
        """Extract dependency information from analyzed content."""
        dependencies = []
        
        for pattern in self.dependency_patterns:
            matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
            for match in matches:
                dep_text = match.strip()
                
                dependency = {
                    "id": str(uuid4()),
                    "description": dep_text,
                    "type": self._classify_dependency_type(dep_text),
                    "criticality": self._assess_criticality(dep_text),
                }
                dependencies.append(dependency)
        
        return dependencies
    
    def _extract_files_from_text(self, text: str) -> List[str]:
        """Extract file paths from text."""
        file_patterns = [
            r"`([^`]+\.\w{2,5})`",  # Code blocks
            r"([/\w][/\w\.-]+\.\w{2,5})",  # Unix paths
            r"([A-Za-z]:\\[\w\\.-]+\.\w{2,5})",  # Windows paths
            r"(\w+\.\w{2,5})",  # Simple filenames
        ]
        
        files = set()
        for pattern in file_patterns:
            matches = re.findall(pattern, text)
            files.update(matches)
        
        return list(files)
    
    def _extract_commands_from_text(self, text: str) -> List[str]:
        """Extract command executions from text."""
        command_patterns = [
            r"`([^`]*(?:git|npm|pip|python|node|docker|kubectl)\s+[^`]+)`",
            r"```(?:bash|shell)\n(.+?)```",
            r"\$ (.+?)(?=\n|$)",
        ]
        
        commands = set()
        for pattern in command_patterns:
            matches = re.findall(pattern, text, re.MULTILINE | re.DOTALL)
            commands.update(matches)
        
        return list(commands)
    
    def _classify_insight_type(self, insight_text: str) -> str:
        """Classify type of insight."""
        text_lower = insight_text.lower()
        
        if any(word in text_lower for word in ["pattern", "trend", "recurrent"]):
            return "pattern"
        elif any(word in text_lower for word in ["decision", "choice", "selected"]):
            return "decision"
        elif any(word in text_lower for word in ["result", "outcome", "achieved"]):
            return "outcome"
        elif any(word in text_lower for word in ["depend", "require", "need"]):
            return "dependency"
        else:
            return "general"
    
    def _calculate_importance_score(self, insight_text: str) -> float:
        """Calculate importance score for insight."""
        high_importance_words = [
            "critical", "important", "key", "essential", "major",
            "significant", "crucial", "vital", "fundamental"
        ]
        
        text_lower = insight_text.lower()
        score = 0.5  # Base score
        
        for word in high_importance_words:
            if word in text_lower:
                score += 0.1
        
        # Longer insights might be more important
        if len(insight_text) > 100:
            score += 0.1
        
        return min(score, 1.0)
    
    def _extract_evidence_from_text(self, insight_text: str, full_text: str) -> List[str]:
        """Extract supporting evidence for insight."""
        evidence = []
        sentences = full_text.split('.')
        
        for sentence in sentences:
            if any(word in sentence.lower() for word in insight_text.lower().split()[:3]):
                evidence_sentence = sentence.strip()
                if len(evidence_sentence) > 20 and evidence_sentence != insight_text:
                    evidence.append(evidence_sentence)
        
        return evidence[:3]  # Limit to top 3 pieces of evidence
    
    def _extract_rationale(self, decision_text: str, full_text: str) -> str:
        """Extract rationale for decision."""
        # Look for reasoning patterns around the decision
        patterns = [
            rf"because\s+(.+?){decision_text}",
            rf"{decision_text}.+?reason:.+?(\.+)",
            rf"rationale:\s*(.+?)(?=\n|$)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        
        return "Rationale not explicitly stated"
    
    def _assess_impact(self, decision_text: str) -> str:
        """Assess impact level of decision."""
        text_lower = decision_text.lower()
        
        if any(word in text_lower for word in ["critical", "major", "significant"]):
            return "high"
        elif any(word in text_lower for word in ["moderate", "medium", "some"]):
            return "medium"
        else:
            return "low"
    
    def _classify_dependency_type(self, dep_text: str) -> str:
        """Classify type of dependency."""
        text_lower = dep_text.lower()
        
        if any(word in text_lower for word in ["api", "service", "external"]):
            return "external"
        elif any(word in text_lower for word in ["module", "package", "library"]):
            return "internal"
        elif any(word in text_lower for word in ["data", "database", "storage"]):
            return "data"
        else:
            return "general"
    
    def _assess_criticality(self, dep_text: str) -> str:
        """Assess criticality of dependency."""
        text_lower = dep_text.lower()
        
        if any(word in text_lower for word in ["critical", "essential", "required", "must"]):
            return "critical"
        elif any(word in text_lower for word in ["important", "should", "recommended"]):
            return "important"
        else:
            return "optional"


# Global analyzer instance
_analyzer: ContentAnalyzer | None = None
_extractor: ContextExtractor | None = None


def get_content_analyzer() -> ContentAnalyzer:
    """Get the global content analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = SessionContentAnalyzer()
    return _analyzer


def get_context_extractor() -> ContextExtractor:
    """Get the global context extractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = ContextExtractor()
    return _extractor
