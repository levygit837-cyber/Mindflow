# Event processing utilities for streaming runtime
# Extracted from AgentRuntime in stream.py

from __future__ import annotations

from typing import Any


def _next_seq(counter: list[int]) -> int:
    """Get the next sequence number for event ordering.
    
    Increments the counter in place and returns the new value.
    """
    counter[0] += 1
    return counter[0]


def _resolve_execution_mode(payload: Any) -> str:
    """Determine the execution mode from a request payload.
    
    Returns one of: "direct", "planning", "deep_work", "chain"
    """
    if payload is None:
        return "direct"
    
    # Check for explicit mode in payload
    if hasattr(payload, "mode"):
        return str(payload.mode)
    
    # Check for planning indicators
    if hasattr(payload, "requires_planning") and payload.requires_planning:
        return "planning"
    
    # Check for deep work indicators
    if hasattr(payload, "deep_work") and payload.deep_work:
        return "deep_work"
    
    # Check for chain indicators
    if hasattr(payload, "chain") and payload.chain:
        return "chain"
    
    return "direct"


def _should_force_structured_analyst_flow(payload: Any) -> bool:
    """Check if structured analyst flow should be forced.
    
    Returns True if the request should use structured analysis.
    """
    if payload is None:
        return False
    
    # Check for analysis indicators
    if hasattr(payload, "analysis_mode") and payload.analysis_mode:
        return True
    
    # Check for structured output requirements
    if hasattr(payload, "structured_output") and payload.structured_output:
        return True
    
    return False


def _resolve_memory_agent_id(payload: Any) -> str:
    """Resolve the agent ID for memory operations.
    
    Extracts or generates an agent ID for memory persistence.
    """
    if payload is None:
        return "default"
    
    # Check for explicit agent ID
    if hasattr(payload, "agent_id"):
        return str(payload.agent_id)
    
    # Check for agent type
    if hasattr(payload, "agent_type"):
        return str(payload.agent_type)
    
    return "default"


__all__ = [
    "_next_seq",
    "_resolve_execution_mode",
    "_should_force_structured_analyst_flow",
    "_resolve_memory_agent_id",
]
