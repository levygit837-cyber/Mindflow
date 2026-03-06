"""Full Analyst composite system prompt.

Pre-built combination of core Analyst personality with specialized functions.
Maintains backward compatibility with the original ANALYST_SYSTEM_PROMPT.
"""

from __future__ import annotations

from mindflow_backend.agents.prompts.core.analyst import compose_analyst_prompt
from mindflow_backend.agents.prompts.specialized.security_analysis import SECURITY_ANALYSIS
from mindflow_backend.agents.prompts.specialized.code_review import CODE_REVIEW
from mindflow_backend.agents.prompts.specialized.brainstorming import BRAINSTORMING
from mindflow_backend.agents.prompts.specialized.deep_analysis import DEEP_ANALYSIS


def build_full_analyst_prompt(*segments: str) -> str:
    """Build a full Analyst system prompt from core and specialized segments.
    
    Args:
        *segments: Segment keys including core ("core", "read") and specialized
                 ("security", "review", "brainstorm", "deep").
        
    Returns:
        A fully composed system prompt combining core and specialized functions.
    """
    parts = []
    
    # Core segments
    core_segments = ["core", "read"]
    for seg in core_segments:
        if seg in segments:
            parts.append(compose_analyst_prompt(seg))
            segments = tuple(s for s in segments if s != seg)
    
    # Specialized segments
    specialized_map = {
        "security": SECURITY_ANALYSIS,
        "review": CODE_REVIEW,
        "brainstorm": BRAINSTORMING,
        "deep": DEEP_ANALYSIS,
    }
    
    for seg in segments:
        if seg in specialized_map:
            parts.append(specialized_map[seg])
        else:
            raise KeyError(f"Unknown analyst segment {seg!r}. Valid: core, read, security, review, brainstorm, deep")
    
    return "\n\n".join(parts)


# Default full analyst prompt (core + read + all specialized functions)
FULL_ANALYST_PROMPT = build_full_analyst_prompt(
    "core", "read", "security", "review", "brainstorm", "deep"
)
