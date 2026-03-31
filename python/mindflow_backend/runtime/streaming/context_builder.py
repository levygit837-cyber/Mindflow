# Context bundle builder for streaming runtime
# Extracted from AgentRuntime in stream.py

from __future__ import annotations

from typing import Any


def _build_context_bundle(state_values: dict[str, Any], *, next_nodes: tuple[str, ...] | list[str]) -> dict[str, Any]:
    """Build a context bundle from graph state values.
    
    Extracts relevant information from the current graph state
    to provide context for decision making and event processing.
    """
    context: dict[str, Any] = {}
    
    # Extract messages if present
    if "messages" in state_values:
        context["messages"] = state_values["messages"]
    
    # Extract current node information
    if next_nodes:
        context["next_nodes"] = list(next_nodes)
    
    # Extract metadata if present
    if "metadata" in state_values:
        context["metadata"] = state_values["metadata"]
    
    # Extract any tool results
    if "tool_results" in state_values:
        context["tool_results"] = state_values["tool_results"]
    
    # Extract decision information
    if "decision" in state_values:
        context["decision"] = state_values["decision"]
    
    return context


def _snapshot_json(value: Any) -> Any:
    """Recursively serialize a value to JSON-compatible format.
    
    Handles complex objects, dataclasses, and nested structures.
    """
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {k: _snapshot_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_snapshot_json(item) for item in value]
    if hasattr(value, "__dict__"):
        return _snapshot_json(value.__dict__)
    if hasattr(value, "model_dump"):
        return _snapshot_json(value.model_dump())
    return str(value)


__all__ = ["_build_context_bundle", "_snapshot_json"]
