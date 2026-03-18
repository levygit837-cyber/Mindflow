"""Deep Work Protocol for MindFlow Agents

This module implements continuation logic that allows agents to perform
multi-turn deep investigations until they signal completion.

Key Concepts:
- Agents can signal "continue_investigation" in their responses
- Context accumulates across continuation turns
- Safety limits prevent infinite loops
- Orchestrator manages the continuation flow
"""

from typing import Any, TypedDict


class ContinuationSignal(TypedDict, total=False):
    """Signal from agent indicating desire to continue investigation."""

    continue_investigation: bool
    reason: str  # Why agent wants to continue
    next_focus: str  # What to investigate next
    depth: int  # Current investigation depth


def should_continue_investigation(
    agent_response: str,
    current_depth: int,
    max_depth: int = 10,
) -> tuple[bool, str]:
    """
    Determine if agent wants to continue investigating.

    Args:
        agent_response: The agent's response text
        current_depth: Current investigation depth
        max_depth: Maximum allowed depth

    Returns:
        (should_continue, reason)
    """
    if current_depth >= max_depth:
        return False, f"Max depth {max_depth} reached"

    # Check for continuation signals in response
    continuation_markers = [
        "continue investigating",
        "need to explore further",
        "requires deeper analysis",
        "let me investigate",
        "I should check",
        "preciso investigar mais",
        "vou continuar",
        "deixe-me explorar",
    ]

    response_lower = agent_response.lower()
    for marker in continuation_markers:
        if marker in response_lower:
            return True, f"Agent signaled continuation: '{marker}'"

    return False, "Agent completed investigation"


def build_continuation_context(
    previous_response: str,
    investigation_history: list[str],
    current_depth: int,
) -> str:
    """
    Build context for next investigation turn.

    Args:
        previous_response: Agent's last response
        investigation_history: List of previous investigation summaries
        current_depth: Current depth

    Returns:
        Context string for next turn
    """
    context_parts = [
        f"CONTINUATION TURN {current_depth + 1}",
        "",
        "Previous Investigation:",
        previous_response[-500:] if len(previous_response) > 500 else previous_response,
        "",
    ]

    if investigation_history:
        context_parts.extend([
            "Investigation History:",
            *[f"- Turn {i+1}: {summary[:100]}" for i, summary in enumerate(investigation_history[-3:])],
            "",
        ])

    context_parts.append("Continue your investigation based on the above context.")

    return "\n".join(context_parts)
