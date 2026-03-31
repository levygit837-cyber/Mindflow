# Decision handling utilities for streaming runtime
# Extracted from AgentRuntime in stream.py

from __future__ import annotations

from typing import Any


def _is_direct_response(decision: Any) -> bool:
    """Check if a decision represents a direct response to the user.
    
    A direct response is one that doesn't require delegation to other agents.
    """
    if decision is None:
        return False
    
    # Check if decision has a direct response flag
    if hasattr(decision, "direct_response"):
        return bool(decision.direct_response)
    
    # Check if decision type indicates direct response
    if hasattr(decision, "type"):
        return decision.type in ("respond", "direct", "answer")
    
    # Check if decision has response content
    if hasattr(decision, "response"):
        return True
    
    return False


def _serialize_decision(decision: Any) -> str:
    """Serialize a decision to a string representation.
    
    Used for logging and debugging purposes.
    """
    if decision is None:
        return "None"
    
    if hasattr(decision, "model_dump_json"):
        return decision.model_dump_json()
    
    if hasattr(decision, "dict"):
        return str(decision.dict())
    
    if hasattr(decision, "__dict__"):
        return str(decision.__dict__)
    
    return str(decision)


def _decision_payload(decision: Any) -> dict[str, Any]:
    """Extract payload from a decision for event emission.
    
    Returns a dictionary suitable for creating StreamEvent objects.
    """
    if decision is None:
        return {}
    
    payload: dict[str, Any] = {}
    
    # Extract common decision fields
    if hasattr(decision, "type"):
        payload["type"] = decision.type
    if hasattr(decision, "agent"):
        payload["agent"] = decision.agent
    if hasattr(decision, "task"):
        payload["task"] = decision.task
    if hasattr(decision, "response"):
        payload["response"] = decision.response
    if hasattr(decision, "reasoning"):
        payload["reasoning"] = decision.reasoning
    
    return payload


def _decision_agent_task(decision: Any) -> tuple[str, str]:
    """Extract agent type and task description from a decision.
    
    Returns a tuple of (agent_type, task_description).
    """
    if decision is None:
        return ("unknown", "")
    
    agent_type = getattr(decision, "agent", "unknown")
    task = getattr(decision, "task", "")
    
    return (str(agent_type), str(task))


__all__ = [
    "_is_direct_response",
    "_serialize_decision",
    "_decision_payload",
    "_decision_agent_task",
]
