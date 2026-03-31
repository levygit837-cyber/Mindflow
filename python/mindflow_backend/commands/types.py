"""
Type definitions for the command system.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable, Protocol


class CommandCategory(str, Enum):
    """Command categories for organization."""

    SYSTEM = "system"
    AGENT = "agent"
    MEMORY = "memory"
    TASK = "task"
    CONFIG = "config"
    DEBUG = "debug"
    CUSTOM = "custom"


@dataclass(frozen=True)
class CommandMetadata:
    """Metadata for a command."""

    name: str
    description: str
    category: CommandCategory
    aliases: tuple[str, ...] = field(default_factory=tuple)
    permission_required: str | None = None
    hidden: bool = False
    examples: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CommandContext:
    """Context passed to command execution."""

    session_id: str
    user_id: str | None
    execution_id: str
    args: list[str]
    raw_input: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CommandResult:
    """Result of command execution."""

    success: bool
    message: str
    data: dict[str, Any] | None = None
    error: str | None = None


class Command(Protocol):
    """Protocol for command implementations."""

    metadata: CommandMetadata

    async def execute(self, context: CommandContext) -> CommandResult:
        """Execute the command with given context."""
        ...
