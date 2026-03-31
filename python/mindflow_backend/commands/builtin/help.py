"""
Help command - shows available commands and their usage.
"""

from mindflow_backend.commands.types import (
    CommandCategory,
    CommandContext,
    CommandMetadata,
    CommandResult,
)
from mindflow_backend.commands.registry import get_registry


class HelpCommand:
    """
    Display help information about available commands.

    Usage:
        /help              - List all commands
        /help <command>    - Show detailed help for a command
        /help category:<category> - List commands in a category
    """

    metadata = CommandMetadata(
        name="help",
        description="Show help information about commands",
        category=CommandCategory.SYSTEM,
        aliases=("h", "?"),
        examples=(
            "/help",
            "/help status",
            "/help category:agent",
        ),
    )

    def __init__(self, registry=None):
        """
        Initialize help command.

        Args:
            registry: Command registry (uses global if None)
        """
        self._registry = registry

    async def execute(self, context: CommandContext) -> CommandResult:
        """Execute help command."""
        registry = self._registry or get_registry()

        # No arguments - show all commands
        if not context.args:
            return self._list_all_commands(registry)

        # Check if filtering by category
        arg = context.args[0]
        if arg.startswith("category:"):
            category_name = arg.split(":", 1)[1]
            return self._list_commands_by_category(registry, category_name)

        # Show help for specific command
        command_name = arg
        return self._show_command_help(registry, command_name)

    def _list_all_commands(self, registry) -> CommandResult:
        """List all available commands."""
        commands = registry.list_all()

        if not commands:
            return CommandResult(
                success=True,
                message="No commands available",
            )

        # Group by category
        by_category: dict[CommandCategory, list] = {}
        for cmd in commands:
            category = cmd.metadata.category
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(cmd)

        # Build help text
        lines = ["Available commands:\n"]

        for category in sorted(by_category.keys(), key=lambda c: c.value):
            lines.append(f"\n{category.value.upper()}:")
            for cmd in sorted(by_category[category], key=lambda c: c.metadata.name):
                aliases = (
                    f" (aliases: {', '.join(cmd.metadata.aliases)})"
                    if cmd.metadata.aliases
                    else ""
                )
                lines.append(f"  /{cmd.metadata.name}{aliases}")
                lines.append(f"    {cmd.metadata.description}")

        lines.append("\n\nUse '/help <command>' for detailed help on a command")

        return CommandResult(
            success=True,
            message="\n".join(lines),
            data={"command_count": len(commands)},
        )

    def _list_commands_by_category(
        self, registry, category_name: str
    ) -> CommandResult:
        """List commands in a specific category."""
        try:
            category = CommandCategory(category_name.lower())
        except ValueError:
            valid_categories = ", ".join(c.value for c in CommandCategory)
            return CommandResult(
                success=False,
                message=f"Invalid category '{category_name}'. Valid categories: {valid_categories}",
                error="INVALID_CATEGORY",
            )

        commands = registry.list_by_category(category)

        if not commands:
            return CommandResult(
                success=True,
                message=f"No commands in category '{category.value}'",
            )

        lines = [f"Commands in category '{category.value}':\n"]
        for cmd in sorted(commands, key=lambda c: c.metadata.name):
            lines.append(f"  /{cmd.metadata.name}")
            lines.append(f"    {cmd.metadata.description}")

        return CommandResult(
            success=True,
            message="\n".join(lines),
            data={"command_count": len(commands)},
        )

    def _show_command_help(self, registry, command_name: str) -> CommandResult:
        """Show detailed help for a specific command."""
        command = registry.get(command_name)

        if command is None:
            return CommandResult(
                success=False,
                message=f"Command '{command_name}' not found",
                error="COMMAND_NOT_FOUND",
            )

        meta = command.metadata
        lines = [
            f"Command: /{meta.name}",
            f"Category: {meta.category.value}",
            f"Description: {meta.description}",
        ]

        if meta.aliases:
            lines.append(f"Aliases: {', '.join(f'/{a}' for a in meta.aliases)}")

        if meta.examples:
            lines.append("\nExamples:")
            for example in meta.examples:
                lines.append(f"  {example}")

        if meta.permission_required:
            lines.append(f"\nPermission required: {meta.permission_required}")

        return CommandResult(
            success=True,
            message="\n".join(lines),
            data={"command": meta.name},
        )
