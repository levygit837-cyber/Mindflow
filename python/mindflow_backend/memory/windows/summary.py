"""Memory summary generation."""

import hashlib
import re

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.memory.storage.models import AgentMemoryEvent, AgentMemoryFact

_logger = get_logger(__name__)


class MemorySummary:
    """Memory summary generation and management."""
    
    def __init__(self):
        self.logger = _logger
    
    def build_structured_summary(self, events: list[AgentMemoryEvent]) -> tuple[str, list[str]]:
        """Build structured summary from events."""
        timeline: list[str] = []
        for event in events[:18]:
            compact = re.sub(r"\s+", " ", event.content).strip()
            compact = compact[:280]
            timeline.append(f"- [{event.role}] {compact}")
        
        candidate_sentences: list[str] = []
        for event in events:
            for sentence in re.split(r"[\n\.;:!?]", event.content):
                compact = re.sub(r"\s+", " ", sentence).strip()
                if len(compact) >= 24:
                    candidate_sentences.append(compact)
        
        key_points: list[str] = []
        seen: set[str] = set()
        for sentence in candidate_sentences:
            key = sentence.lower()
            if key in seen:
                continue
            seen.add(key)
            key_points.append(sentence[:240])
            if len(key_points) >= 10:
                break
        
        if not key_points and timeline:
            key_points = [line[11:] for line in timeline[:3]]
        
        summary_lines = [
            "Consolidated summary of the agent context window:",
            f"- Total events: {len(events)}",
            "- Main timeline:",
            *timeline,
        ]
        if key_points:
            summary_lines.append("- Key points:")
            summary_lines.extend(f"  - {item}" for item in key_points[:8])
        
        return "\n".join(summary_lines), key_points
    
    def extract_key_facts(
        self,
        events: list[AgentMemoryEvent],
        max_facts: int = 8
    ) -> list[AgentMemoryFact]:
        """Extract key facts from events."""
        facts = []
        
        # Simple fact extraction based on content patterns
        for event in events:
            content = event.content.lower()
            
            # Look for statements that might be facts
            fact_patterns = [
                r"(\w+ is \w+)",
                r"(\w+ are \w+)",
                r"(\w+ has \w+)",
                r"(\w+ can \w+)",
                r"(\w+ will \w+)",
            ]
            
            for pattern in fact_patterns:
                matches = re.findall(pattern, content)
                for match in matches[:2]:  # Limit facts per event
                    if len(facts) < max_facts:
                        fact = AgentMemoryFact(
                            session_id=event.session_id,
                            agent_id=event.agent_id,
                            window_id=0,  # Will be set when creating window
                            fact_type="extracted",
                            content=match,
                            weight=1.0
                        )
                        facts.append(fact)
        
        return facts
    
    def generate_summary_checksum(self, events: list[AgentMemoryEvent]) -> str:
        """Generate checksum for events to detect duplicates."""
        checksum_input = "\n".join(f"{e.id}:{e.content}" for e in events).encode("utf-8")
        return hashlib.sha256(checksum_input).hexdigest()
    
    def calculate_coverage_ratio(
        self,
        events: list[AgentMemoryEvent],
        summary: str
    ) -> float:
        """Calculate how well the summary covers the original content."""
        if not events or not summary:
            return 0.0
        
        # Simple coverage based on content length
        total_content = " ".join(event.content for event in events)
        coverage = len(summary) / len(total_content) if total_content else 0.0
        
        return min(coverage, 1.0)
