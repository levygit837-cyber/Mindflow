"""Result parser for session review.

Provides parsing capabilities for extracting structured
information from LLM analysis results.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List
from uuid import uuid4

from omnimind_backend.agents.core.interfaces import ResultParser
from omnimind_backend.agents.core.exceptions import ResultParsingError
from omnimind_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class SessionReviewResultParser(ResultParser):
    """Parses session review results from LLM analysis."""
    
    def __init__(self):
        self.action_patterns = [
            r"Actions?:\s*(.+?)(?=\n\n|\n[A-Z][a-z]+:|$)",
            r"- \*\*(.+?)\*\*:\s*(.+?)(?=\n-|\n\n|$)",
            r"(\w+)\s+(?:file|code|command):\s*(.+?)(?=\n|$)",
            r"^\d+\.\s*(.+?)(?=\n\d+\.|\n\n|$)",  # Numbered lists
        ]
        
        self.insight_patterns = [
            r"Insights?:\s*(.+?)(?=\n\n|\n[A-Z][a-z]+:|$)",
            r"Key\s+Insights?:\s*(.+?)(?=\n\n|\n[A-Z][a-z]+:|$)",
            r"Pattern\s+Detected:\s*(.+?)(?=\n\n|\n[A-Z][a-z]+:|$)",
            r"Important\s+Notes?:\s*(.+?)(?=\n\n|\n[A-Z][a-z]+:|$)",
        ]
        
        self.decision_patterns = [
            r"Decisions?:\s*(.+?)(?=\n\n|\n[A-Z][a-z]+:|$)",
            r"Important\s+Decisions?:\s*(.+?)(?=\n\n|\n[A-Z][a-z]+:|$)",
            r"Key\s+Decisions?:\s*(.+?)(?=\n\n|\n[A-Z][a-z]+:|$)",
        ]
        
        self.dependency_patterns = [
            r"Dependencies?:\s*(.+?)(?=\n\n|\n[A-Z][a-z]+:|$)",
            r"Dependencies\s+Identified:\s*(.+?)(?=\n\n|\n[A-Z][a-z]+:|$)",
            r"Required\s+Dependencies?:\s*(.+?)(?=\n\n|\n[A-Z][a-z]+:|$)",
        ]
    
    def parse_actions(
        self,
        analysis_content: str,
        session_id: str,
        window_range: tuple[int, int],
    ) -> List[Dict[str, Any]]:
        """Parse actions from analysis content."""
        try:
            _logger.debug(
                "action_parsing_started",
                session_id=session_id,
                content_length=len(analysis_content)
            )
            
            actions = []
            
            for pattern in self.action_patterns:
                matches = re.findall(pattern, analysis_content, re.MULTILINE | re.DOTALL)
                for match in matches:
                    action = self._parse_action_match(match, session_id, window_range)
                    if action:
                        actions.append(action)
            
            # Remove duplicates based on description
            unique_actions = self._deduplicate_actions(actions)
            
            _logger.debug(
                "action_parsing_completed",
                session_id=session_id,
                total_found=len(actions),
                unique_count=len(unique_actions)
            )
            
            return unique_actions
        
        except Exception as e:
            _logger.error("action_parsing_failed", session_id=session_id, error=str(e))
            raise ResultParsingError(
                f"Failed to parse actions: {e}",
                content_type="actions"
            )
    
    def parse_insights(
        self,
        analysis_content: str,
        session_id: str,
        window_range: tuple[int, int],
    ) -> List[Dict[str, Any]]:
        """Parse insights from analysis content."""
        try:
            _logger.debug(
                "insight_parsing_started",
                session_id=session_id,
                content_length=len(analysis_content)
            )
            
            insights = []
            
            for pattern in self.insight_patterns:
                matches = re.findall(pattern, analysis_content, re.MULTILINE | re.DOTALL)
                for match in matches:
                    insight = self._parse_insight_match(match, session_id, window_range)
                    if insight:
                        insights.append(insight)
            
            # Remove duplicates based on content
            unique_insights = self._deduplicate_insights(insights)
            
            _logger.debug(
                "insight_parsing_completed",
                session_id=session_id,
                total_found=len(insights),
                unique_count=len(unique_insights)
            )
            
            return unique_insights
        
        except Exception as e:
            _logger.error("insight_parsing_failed", session_id=session_id, error=str(e))
            raise ResultParsingError(
                f"Failed to parse insights: {e}",
                content_type="insights"
            )
    
    def parse_summary(self, analysis_content: str) -> str:
        """Parse summary from analysis content."""
        summary_patterns = [
            r"Summary:\s*(.+?)(?=\n\n|\n[A-Z][a-z]+:|$)",
            r"Overall\s+Summary:\s*(.+?)(?=\n\n|\n[A-Z][a-z]+:|$)",
            r"##\s*Summary\s*\n(.+?)(?=\n##|\n\n|$)",
            r"Executive\s+Summary:\s*(.+?)(?=\n\n|\n[A-Z][a-z]+:|$)",
        ]
        
        for pattern in summary_patterns:
            match = re.search(pattern, analysis_content, re.MULTILINE | re.DOTALL)
            if match:
                summary = match.group(1).strip()
                if len(summary) > 20:  # Ensure meaningful summary
                    return summary
        
        # Fallback: extract first substantial paragraph
        lines = analysis_content.split('\n')
        for line in lines:
            line = line.strip()
            if line and len(line) > 50 and not line.startswith('#'):
                return line
        
        return "No clear summary found in analysis."
    
    def _parse_action_match(
        self,
        match: Any,
        session_id: str,
        window_range: tuple[int, int],
    ) -> Dict[str, Any] | None:
        """Parse a single action match."""
        try:
            if isinstance(match, tuple):
                if len(match) >= 2:
                    action_type = match[0].strip() if match[0] else "general"
                    description = match[1].strip() if match[1] else ""
                else:
                    action_type = "general"
                    description = match[0].strip() if match[0] else ""
            else:
                action_type = "general"
                description = str(match).strip()
            
            if not description or len(description) < 10:
                return None
            
            return {
                "id": str(uuid4()),
                "session_id": session_id,
                "window_range": window_range,
                "action_type": action_type,
                "description": description,
                "agent_type": self._infer_agent_type(description),
                "files_affected": self._extract_files_from_text(description),
                "commands_executed": self._extract_commands_from_text(description),
                "outcomes": self._extract_outcomes_from_text(description),
                "confidence_score": self._calculate_action_confidence(description),
            }
        
        except Exception as e:
            _logger.warning("action_match_parsing_failed", match=str(match), error=str(e))
            return None
    
    def _parse_insight_match(
        self,
        match: Any,
        session_id: str,
        window_range: tuple[int, int],
    ) -> Dict[str, Any] | None:
        """Parse a single insight match."""
        try:
            insight_text = str(match).strip() if match else ""
            
            if not insight_text or len(insight_text) < 10:
                return None
            
            return {
                "id": str(uuid4()),
                "session_id": session_id,
                "window_range": window_range,
                "insight_type": self._classify_insight_type(insight_text),
                "content": insight_text,
                "importance_score": self._calculate_importance_score(insight_text),
                "supporting_evidence": self._extract_evidence_from_text(insight_text),
                "confidence_score": self._calculate_insight_confidence(insight_text),
            }
        
        except Exception as e:
            _logger.warning("insight_match_parsing_failed", match=str(match), error=str(e))
            return None
    
    def _deduplicate_actions(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate actions based on description."""
        seen_descriptions = set()
        unique_actions = []
        
        for action in actions:
            desc_lower = action["description"].lower().strip()
            if desc_lower not in seen_descriptions:
                seen_descriptions.add(desc_lower)
                unique_actions.append(action)
        
        return unique_actions
    
    def _deduplicate_insights(self, insights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate insights based on content."""
        seen_contents = set()
        unique_insights = []
        
        for insight in insights:
            content_lower = insight["content"].lower().strip()
            if content_lower not in seen_contents:
                seen_contents.add(content_lower)
                unique_insights.append(insight)
        
        return unique_insights
    
    def _infer_agent_type(self, description: str) -> str:
        """Infer agent type from action description."""
        description_lower = description.lower()
        
        if any(word in description_lower for word in ["code", "file", "function", "class", "implement"]):
            return "coder"
        elif any(word in description_lower for word in ["research", "search", "find", "investigate", "explore"]):
            return "researcher"
        elif any(word in description_lower for word in ["analyze", "review", "document", "evaluate"]):
            return "analyst"
        elif any(word in description_lower for word in ["architect", "design", "structure", "pattern"]):
            return "architect"
        else:
            return "general"
    
    def _classify_insight_type(self, insight_text: str) -> str:
        """Classify type of insight."""
        text_lower = insight_text.lower()
        
        if any(word in text_lower for word in ["pattern", "trend", "recurrent", "repeating"]):
            return "pattern"
        elif any(word in text_lower for word in ["decision", "choice", "selected", "chosen"]):
            return "decision"
        elif any(word in text_lower for word in ["result", "outcome", "achieved", "accomplished"]):
            return "outcome"
        elif any(word in text_lower for word in ["depend", "require", "need", "reliant"]):
            return "dependency"
        elif any(word in text_lower for word in ["issue", "problem", "bug", "error"]):
            return "issue"
        elif any(word in text_lower for word in ["improvement", "optimize", "enhance", "better"]):
            return "improvement"
        else:
            return "general"
    
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
            r"`([^`]*(?:git|npm|pip|python|node|docker|kubectl|curl|wget)\s+[^`]+)`",
            r"```(?:bash|shell|sh)\n(.+?)```",
            r"\$ (.+?)(?=\n|$)",
            r"^(?:run|execute|cmd):\s*(.+?)(?=\n|$)",
        ]
        
        commands = set()
        for pattern in command_patterns:
            matches = re.findall(pattern, text, re.MULTILINE | re.DOTALL)
            commands.update(matches)
        
        return list(commands)
    
    def _extract_outcomes_from_text(self, text: str) -> List[str]:
        """Extract outcomes from action description."""
        outcome_patterns = [
            r"(?:result|outcome|achieved|accomplished):\s*(.+?)(?=\n|,|$)",
            r"(?:created|updated|deleted|fixed):\s*(.+?)(?=\n|,|$)",
        ]
        
        outcomes = set()
        for pattern in outcome_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            outcomes.update(matches)
        
        return list(outcomes)
    
    def _extract_evidence_from_text(self, insight_text: str) -> List[str]:
        """Extract supporting evidence for insight."""
        # Simple implementation - look for sentences that contain insight keywords
        evidence = []
        words = insight_text.lower().split()[:3]  # First 3 words
        
        # This would be the full analysis content in practice
        # For now, return empty list
        return evidence
    
    def _calculate_action_confidence(self, description: str) -> float:
        """Calculate confidence score for action."""
        base_score = 0.5
        
        # More specific descriptions get higher confidence
        if len(description) > 50:
            base_score += 0.1
        if len(description) > 100:
            base_score += 0.1
        
        # Presence of files or commands increases confidence
        if self._extract_files_from_text(description):
            base_score += 0.1
        if self._extract_commands_from_text(description):
            base_score += 0.1
        
        # Action verbs increase confidence
        action_verbs = ["created", "updated", "deleted", "implemented", "fixed", "added", "removed"]
        if any(verb in description.lower() for verb in action_verbs):
            base_score += 0.1
        
        return min(base_score, 1.0)
    
    def _calculate_insight_confidence(self, insight_text: str) -> float:
        """Calculate confidence score for insight."""
        base_score = 0.5
        
        # Longer insights might be more reliable
        if len(insight_text) > 30:
            base_score += 0.1
        if len(insight_text) > 80:
            base_score += 0.1
        
        # Insight indicators increase confidence
        insight_indicators = ["identified", "noticed", "observed", "found", "discovered", "recognized"]
        if any(indicator in insight_text.lower() for indicator in insight_indicators):
            base_score += 0.1
        
        return min(base_score, 1.0)
    
    def _calculate_importance_score(self, insight_text: str) -> float:
        """Calculate importance score for insight."""
        high_importance_words = [
            "critical", "important", "key", "essential", "major",
            "significant", "crucial", "vital", "fundamental", "primary"
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


# Global parser instance
_parser: SessionReviewResultParser | None = None


def get_session_review_parser() -> SessionReviewResultParser:
    """Get the global session review parser instance."""
    global _parser
    if _parser is None:
        _parser = SessionReviewResultParser()
    return _parser
