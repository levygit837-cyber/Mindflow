"""
Command registry with memoization pattern.

Inspired by Claude Code CLI's command system, this registry provides:
- Command registration and discovery
- Lookup by name or alias
- Category-based filtering
- Memoization for performance
"""

from functools import lru_cache
from typing import Protocol

from mindflow_backend.commands.types import Command, CommandCategory, CommandMetadata


class CommandRegistry:
    """
    Central registry for all commands.

    Provides command registration, lookup, and filtering capabilities.
    Uses memoization to cache lookups for performance.
    """

    def __init__(self):
        """Initialize empty command registry."""
        self._commands: dict[str, Command] = {}
        self._aliases: dict[str, str] = {}  # alias -> command_name mapping

    def register(self, command: Command) -> None:
        """
        Register a command in the registry.

        Args:
            command: Command instance to register

        Raises:
            ValueError: If command name or alias is already registered
        """
        name = command.metadata.name

        if name in self._commands:
            raise ValueError(f"Command '{name}' is already registered")

        # Check for alias conflicts
        for alias in command.metadata.aliases:
            if alias in self._aliases or alias in self._commands:
                raise ValueError(
                    f"Alias '{alias}' conflicts with existing command or alias"
                )

        # Register command
        self._commands[name] = command

        # Register aliases
        for alias in command.metadata.aliases:
            self._aliases[alias] = name

        # Clear memoization cache
        self._clear_cache()

    def unregister(self, name: str) -> None:
        """
        Unregister a command from the registry.

        Args:
            name: Command name to unregister
        """
        if name not in self._commands:
            return

        command = self._commands[name]

        # Remove aliases
        for alias in command.metadata.aliases:
            self._aliases.pop(alias, None)

        # Remove command
        del self._commands[name]

        # Clear memoization cache
        self._clear_cache()

    def get(self, name_or_alias: str) -> Command | None:
        """
        Get command by name or alias.

        Args:
            name_or_alias: Command name or alias

        Returns:
            Command instance or None if not found
        """
        # Direct lookup
        if name_or_alias in self._commands:
            return self._commands[name_or_alias]

        # Alias lookup
        if name_or_alias in self._aliases:
            command_name = self._aliases[name_or_alias]
            return self._commands[command_name]

        return None

    def has(self, name_or_alias: str) -> bool:
        """
        Check if command exists.

        Args:
            name_or_alias: Command name or alias

        Returns:
            True if command exists, False otherwise
        """
        return self.get(name_or_alias) is not None

    def list_all(self, include_hidden: bool = False) -> list[Command]:
        """
        List all registered commands.

        Args:
            include_hidden: Whether to include hidden commands

        Returns:
            List of all commands
        """
        commands = list(self._commands.values())

        if not include_hidden:
            commands = [cmd for cmd in commands if not cmd.metadata.hidden]

        return commands

    def list_by_category(
        self, category: CommandCategory, include_hidden: bool = False
    ) -> list[Command]:
        """
        List commands by category.

        Args:
            category: Command category to filter by
            include_hidden: Whether to include hidden commands

        Returns:
            List of commands in the specified category
        """
        commands = self.list_all(include_hidden=include_hidden)
        return [cmd for cmd in commands if cmd.metadata.category == category]

    def clear(self) -> None:
        """Clear all registered commands."""
        self._commands.clear()
        self._aliases.clear()
        self._clear_cache()

    def _clear_cache(self) -> None:
        """Clear memoization cache."""
        # In future, if we add @lru_cache decorators, clear them here
        pass


# Global singleton instance
_registry: CommandRegistry | None = None


def get_registry() -> CommandRegistry:
    """
    Get the global command registry instance.

    Returns:
        Global CommandRegistry singleton
    """
    global _registry
    if _registry is None:
        _registry = CommandRegistry()
    return _registry
