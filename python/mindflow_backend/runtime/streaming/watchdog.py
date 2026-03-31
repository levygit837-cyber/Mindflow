# Watchdog logic for streaming runtime
# Extracted from AgentRuntime in stream.py

from __future__ import annotations

from typing import Any


def _counts_as_watchdog_progress(event: Any) -> bool:
    """Check if an event counts as progress for the watchdog timer.
    
    Events that indicate the agent is making progress and shouldn't be timed out.
    """
    if event is None:
        return False
    
    # Check event type
    if hasattr(event, "type"):
        event_type = event.type
        # These event types indicate progress
        progress_types = {
            "thinking",
            "tool_call",
            "tool_result",
            "message",
            "decision",
            "response",
            "delegation",
            "reflection",
        }
        return event_type in progress_types
    
    return False


def _counts_as_tool_watchdog_progress(event: Any) -> bool:
    """Check if an event counts as progress for tool execution watchdog.
    
    Specific events that indicate tool execution is progressing.
    """
    if event is None:
        return False
    
    # Check event type
    if hasattr(event, "type"):
        event_type = event.type
        # These event types indicate tool progress
        tool_progress_types = {
            "tool_call",
            "tool_result",
            "tool_error",
            "tool_timeout",
        }
        return event_type in tool_progress_types
    
    return False


__all__ = [
    "_counts_as_watchdog_progress",
    "_counts_as_tool_watchdog_progress",
]
