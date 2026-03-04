"""Full Orchestrator composite system prompt.

Pre-built combination of core Orchestrator personality with specialized functions.
Maintains backward compatibility with the original ORCHESTRATOR_SYSTEM_PROMPT.
"""

from __future__ import annotations

from omnimind_backend.agents.prompts.core.orchestrator import compose_orchestrator_prompt
from omnimind_backend.agents.prompts.specialized.context_governance import CONTEXT_GOVERNANCE
from omnimind_backend.agents.prompts.specialized.agent_delegation import AGENT_DELEGATION
from omnimind_backend.agents.prompts.specialized.orchestrator_reflection import ORCHESTRATOR_REFLECTION


def build_full_orchestrator_prompt(*segments: str) -> str:
    """Build a full Orchestrator system prompt from core and specialized segments.

    Args:
        *segments: Segment keys including core ("core") and specialized
                 ("governance", "delegation", "reflection").

    Returns:
        A fully composed system prompt combining core and specialized functions.
    """
    parts = []

    # Core segments
    core_segments = ["core"]
    for seg in core_segments:
        if seg in segments:
            parts.append(compose_orchestrator_prompt(seg))
            segments = tuple(s for s in segments if s != seg)

    # Specialized segments
    specialized_map = {
        "governance": CONTEXT_GOVERNANCE,
        "delegation": AGENT_DELEGATION,
        "reflection": ORCHESTRATOR_REFLECTION,
    }

    for seg in segments:
        if seg in specialized_map:
            parts.append(specialized_map[seg])
        else:
            valid = ", ".join(["core", *sorted(specialized_map)])
            raise KeyError(f"Unknown orchestrator segment {seg!r}. Valid: {valid}")

    return "\n\n".join(parts)


# Default full orchestrator prompt (core + governance + delegation)
FULL_ORCHESTRATOR_PROMPT = build_full_orchestrator_prompt("core", "governance", "delegation")
