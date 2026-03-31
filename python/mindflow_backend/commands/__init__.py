"""
Command system for MindFlow.

This module provides a command registry and execution system inspired by Claude Code CLI.
Commands can be invoked via slash syntax (e.g., /help, /status) and support:
- Dynamic discovery from multiple sources (builtin, custom, plugins)
- Memoization for performance
- Metadata (name, description, aliases, category)
- Permission requirements
"""

from mindflow_backend.commands.registry import CommandRegistry, Command
from mindflow_backend.commands.types import CommandCategory, CommandMetadata

__all__ = [
    "CommandRegistry",
    "Command",
    "CommandCategory",
    "CommandMetadata",
]
