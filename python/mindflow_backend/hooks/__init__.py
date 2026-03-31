"""MindFlow Hooks System.

A comprehensive hook system for agents inspired by Claude Code's hooks architecture.
Provides extensibility points at every stage of agent execution:

- PreToolUse: Before tool execution — can modify input or block
- PostToolUse: After tool execution — can modify output
- PostToolUseFailure: When tool execution fails
- Stop: Session/mission ended
- AgentStart/AgentStop: Agent lifecycle events
- UserPromptSubmit: When user submits a prompt
- SessionStart: Session initialized
- PermissionRequest/PermissionDenied: Permission hooks
- MissionStart/MissionStop: MindFlow-specific mission hooks
"""

from __future__ import annotations

from .context import HookContext
from .manager import HookManager
from .registry import HookRegistry
from .result import AggregatedHookResult, HookCommand, HookMatcher, HookResult
from .types import HookEvent, HookPermissionBehavior

__version__ = "1.0.0"
__author__ = "MindFlow Team"

__all__ = [
    # Core types
    "HookEvent",
    "HookPermissionBehavior",
    # Data classes
    "HookContext",
    "HookResult",
    "AggregatedHookResult",
    "HookCommand",
    "HookMatcher",
    # Core components
    "HookManager",
    "HookRegistry",
]