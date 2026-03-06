"""Full Coder composite system prompt.

Pre-built combination of core Coder personality with specialized functions.
Maintains backward compatibility with the original CODER_SYSTEM_PROMPT.
"""

from __future__ import annotations

from omnimind_backend.agents.prompts.core.coder import compose_coder_prompt


def build_full_coder_prompt(*segments: str) -> str:
    """Build a full Coder system prompt from core and specialized segments.
    
    Args:
        *segments: Segment keys including core ("core", "tool_use").
        
    Returns:
        A fully composed system prompt combining core functions.
    """
    parts = []
    
    # Core segments
    core_segments = ["core", "tool_use"]
    for seg in core_segments:
        if seg in segments:
            parts.append(compose_coder_prompt(seg))
            segments = tuple(s for s in segments if s != seg)
    
    # No specialized segments available
    
    for seg in segments:
        raise KeyError(f"Unknown coder segment {seg!r}. Valid: core, tool_use")
    
    return "\n\n".join(parts)


# Default full coder prompt (core + tool_use)
FULL_CODER_PROMPT = build_full_coder_prompt("core", "tool_use")
