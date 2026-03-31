"""
Unit tests for Help command.
"""

import pytest
from mindflow_backend.commands.builtin.help import HelpCommand
from mindflow_backend.commands.registry import CommandRegistry
from mindflow_backend.commands.types import (
    CommandCategory,
    CommandContext,
    CommandMetadata,
    CommandResult,
)


class MockCommand:
    """Mock command for testing."""

    def __init__(self, name: str, category: CommandCategory = CommandCategory.SYSTEM):
        self.metadata = CommandMetadata(
            name=name,
            description=f"Test {name} command",
            category=category,
            aliases=("alias1",) if name == "test1" else (),
        )

    async def execute(self, context: CommandContext) -> CommandResult:
        return CommandResult(success=True, message="Mock executed")


@pytest.mark.unit
class TestHelpCommand:
    """Test suite for HelpCommand."""

    @pytest.mark.asyncio
    async def test_help_lists_all_commands(self):
        """Test /help lists all commands."""
        registry = CommandRegistry()
        registry.register(MockCommand("test1"))
        registry.register(MockCommand("test2"))
        registry.register(HelpCommand(registry))

        help_cmd = HelpCommand(registry)
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=[],
            raw_input="/help",
        )

        result = await help_cmd.execute(context)

        assert result.success is True
        assert "Available commands" in result.message
        assert "/test1" in result.message
        assert "/test2" in result.message
        assert "/help" in result.message
        assert result.data is not None
        assert result.data["command_count"] == 3

    @pytest.mark.asyncio
    async def test_help_shows_command_details(self):
        """Test /help <command> shows command details."""
        registry = CommandRegistry()
        registry.register(MockCommand("test1"))
        registry.register(HelpCommand(registry))

        help_cmd = HelpCommand(registry)
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["test1"],
            raw_input="/help test1",
        )

        result = await help_cmd.execute(context)

        assert result.success is True
        assert "Command: /test1" in result.message
        assert "Category: system" in result.message
        assert "Description:" in result.message
        assert "Aliases: /alias1" in result.message

    @pytest.mark.asyncio
    async def test_help_command_not_found(self):
        """Test /help <nonexistent> returns error."""
        registry = CommandRegistry()
        registry.register(HelpCommand(registry))

        help_cmd = HelpCommand(registry)
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["nonexistent"],
            raw_input="/help nonexistent",
        )

        result = await help_cmd.execute(context)

        assert result.success is False
        assert "not found" in result.message
        assert result.error == "COMMAND_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_help_filter_by_category(self):
        """Test /help category:<category> filters by category."""
        registry = CommandRegistry()
        registry.register(MockCommand("sys1", CommandCategory.SYSTEM))
        registry.register(MockCommand("agent1", CommandCategory.AGENT))
        registry.register(HelpCommand(registry))

        help_cmd = HelpCommand(registry)
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["category:agent"],
            raw_input="/help category:agent",
        )

        result = await help_cmd.execute(context)

        assert result.success is True
        assert "category 'agent'" in result.message
        assert "/agent1" in result.message
        assert "/sys1" not in result.message

    @pytest.mark.asyncio
    async def test_help_invalid_category(self):
        """Test /help category:<invalid> returns error."""
        registry = CommandRegistry()
        registry.register(HelpCommand(registry))

        help_cmd = HelpCommand(registry)
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["category:invalid"],
            raw_input="/help category:invalid",
        )

        result = await help_cmd.execute(context)

        assert result.success is False
        assert "Invalid category" in result.message
        assert result.error == "INVALID_CATEGORY"

    @pytest.mark.asyncio
    async def test_help_empty_registry(self):
        """Test /help with no commands registered."""
        registry = CommandRegistry()

        help_cmd = HelpCommand(registry)
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=[],
            raw_input="/help",
        )

        result = await help_cmd.execute(context)

        assert result.success is True
        assert "No commands available" in result.message

    @pytest.mark.asyncio
    async def test_help_shows_examples(self):
        """Test /help shows command examples."""
        registry = CommandRegistry()
        registry.register(HelpCommand(registry))

        help_cmd = HelpCommand(registry)
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["help"],
            raw_input="/help help",
        )

        result = await help_cmd.execute(context)

        assert result.success is True
        assert "Examples:" in result.message
        assert "/help" in result.message
