"""
Unit tests for CommandRegistry.
"""

import pytest
from mindflow_backend.commands.registry import CommandRegistry
from mindflow_backend.commands.types import (
    Command,
    CommandCategory,
    CommandContext,
    CommandMetadata,
    CommandResult,
)


class MockCommand:
    """Mock command for testing."""

    def __init__(
        self,
        name: str,
        description: str = "Test command",
        category: CommandCategory = CommandCategory.SYSTEM,
        aliases: tuple[str, ...] = (),
    ):
        self.metadata = CommandMetadata(
            name=name,
            description=description,
            category=category,
            aliases=aliases,
        )

    async def execute(self, context: CommandContext) -> CommandResult:
        return CommandResult(
            success=True,
            message=f"Executed {self.metadata.name}",
        )


@pytest.mark.unit
class TestCommandRegistry:
    """Test suite for CommandRegistry."""

    def test_register_command(self):
        """Test registering a command."""
        registry = CommandRegistry()
        cmd = MockCommand("test")

        registry.register(cmd)

        assert registry.get("test") == cmd

    def test_register_duplicate_raises_error(self):
        """Test that registering duplicate command raises error."""
        registry = CommandRegistry()
        cmd1 = MockCommand("test")
        cmd2 = MockCommand("test")

        registry.register(cmd1)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(cmd2)

    def test_get_nonexistent_command_returns_none(self):
        """Test getting non-existent command returns None."""
        registry = CommandRegistry()

        assert registry.get("nonexistent") is None

    def test_get_by_alias(self):
        """Test getting command by alias."""
        registry = CommandRegistry()
        cmd = MockCommand("help", aliases=("h", "?"))

        registry.register(cmd)

        assert registry.get("h") == cmd
        assert registry.get("?") == cmd
        assert registry.get("help") == cmd

    def test_list_all_commands(self):
        """Test listing all commands."""
        registry = CommandRegistry()
        cmd1 = MockCommand("test1")
        cmd2 = MockCommand("test2")

        registry.register(cmd1)
        registry.register(cmd2)

        commands = registry.list_all()

        assert len(commands) == 2
        assert cmd1 in commands
        assert cmd2 in commands

    def test_list_by_category(self):
        """Test listing commands by category."""
        registry = CommandRegistry()
        cmd1 = MockCommand("test1", category=CommandCategory.SYSTEM)
        cmd2 = MockCommand("test2", category=CommandCategory.AGENT)
        cmd3 = MockCommand("test3", category=CommandCategory.SYSTEM)

        registry.register(cmd1)
        registry.register(cmd2)
        registry.register(cmd3)

        system_commands = registry.list_by_category(CommandCategory.SYSTEM)

        assert len(system_commands) == 2
        assert cmd1 in system_commands
        assert cmd3 in system_commands
        assert cmd2 not in system_commands

    def test_unregister_command(self):
        """Test unregistering a command."""
        registry = CommandRegistry()
        cmd = MockCommand("test")

        registry.register(cmd)
        assert registry.get("test") == cmd

        registry.unregister("test")
        assert registry.get("test") is None

    def test_unregister_nonexistent_command_silent(self):
        """Test unregistering non-existent command is silent."""
        registry = CommandRegistry()

        # Should not raise
        registry.unregister("nonexistent")

    def test_has_command(self):
        """Test checking if command exists."""
        registry = CommandRegistry()
        cmd = MockCommand("test", aliases=("t",))

        registry.register(cmd)

        assert registry.has("test") is True
        assert registry.has("t") is True
        assert registry.has("nonexistent") is False

    def test_clear_registry(self):
        """Test clearing all commands."""
        registry = CommandRegistry()
        cmd1 = MockCommand("test1")
        cmd2 = MockCommand("test2")

        registry.register(cmd1)
        registry.register(cmd2)

        assert len(registry.list_all()) == 2

        registry.clear()

        assert len(registry.list_all()) == 0

    def test_hidden_commands_not_in_list(self):
        """Test that hidden commands are not included in list_all by default."""
        registry = CommandRegistry()
        visible_cmd = MockCommand("visible")
        hidden_cmd = MockCommand("hidden")
        hidden_cmd.metadata = CommandMetadata(
            name="hidden",
            description="Hidden command",
            category=CommandCategory.DEBUG,
            hidden=True,
        )

        registry.register(visible_cmd)
        registry.register(hidden_cmd)

        # Default list should not include hidden
        commands = registry.list_all()
        assert len(commands) == 1
        assert visible_cmd in commands

        # Explicit include_hidden should show all
        all_commands = registry.list_all(include_hidden=True)
        assert len(all_commands) == 2
