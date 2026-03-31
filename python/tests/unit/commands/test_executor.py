"""
Unit tests for Command Executor.
"""

import pytest
from mindflow_backend.commands.executor import CommandExecutor
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
        should_succeed: bool = True,
        permission_required: str | None = None,
    ):
        self.metadata = CommandMetadata(
            name=name,
            description="Test command",
            category=CommandCategory.SYSTEM,
            permission_required=permission_required,
        )
        self.should_succeed = should_succeed
        self.executed = False
        self.last_context: CommandContext | None = None

    async def execute(self, context: CommandContext) -> CommandResult:
        self.executed = True
        self.last_context = context

        if self.should_succeed:
            return CommandResult(
                success=True,
                message=f"Command {self.metadata.name} executed successfully",
                data={"args": context.args},
            )
        else:
            return CommandResult(
                success=False,
                message="Command execution failed",
                error="MOCK_ERROR",
            )


@pytest.mark.unit
class TestCommandExecutor:
    """Test suite for CommandExecutor."""

    @pytest.mark.asyncio
    async def test_execute_command_success(self):
        """Test successful command execution."""
        registry = CommandRegistry()
        cmd = MockCommand("test")
        registry.register(cmd)

        executor = CommandExecutor(registry=registry)
        result = await executor.execute(
            command_name="test",
            args=["arg1", "arg2"],
            session_id="session-123",
            user_id="user-456",
        )

        assert result.success is True
        assert "executed successfully" in result.message
        assert cmd.executed is True
        assert cmd.last_context is not None
        assert cmd.last_context.args == ["arg1", "arg2"]
        assert cmd.last_context.session_id == "session-123"
        assert cmd.last_context.user_id == "user-456"

    @pytest.mark.asyncio
    async def test_execute_command_not_found(self):
        """Test executing non-existent command."""
        registry = CommandRegistry()
        executor = CommandExecutor(registry=registry)

        result = await executor.execute(
            command_name="nonexistent",
            args=[],
            session_id="session-123",
        )

        assert result.success is False
        assert "not found" in result.message
        assert result.error == "COMMAND_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_execute_command_failure(self):
        """Test command that returns failure."""
        registry = CommandRegistry()
        cmd = MockCommand("failing", should_succeed=False)
        registry.register(cmd)

        executor = CommandExecutor(registry=registry)
        result = await executor.execute(
            command_name="failing",
            args=[],
            session_id="session-123",
        )

        assert result.success is False
        assert result.error == "MOCK_ERROR"

    @pytest.mark.asyncio
    async def test_execute_command_with_exception(self):
        """Test command that raises exception."""

        class FailingCommand:
            metadata = CommandMetadata(
                name="exception",
                description="Raises exception",
                category=CommandCategory.SYSTEM,
            )

            async def execute(self, context: CommandContext) -> CommandResult:
                raise ValueError("Test exception")

        registry = CommandRegistry()
        registry.register(FailingCommand())

        executor = CommandExecutor(registry=registry)
        result = await executor.execute(
            command_name="exception",
            args=[],
            session_id="session-123",
        )

        assert result.success is False
        assert "Error executing command" in result.message
        assert result.error == "EXECUTION_ERROR"
        assert result.data is not None
        assert result.data["exception_type"] == "ValueError"

    @pytest.mark.asyncio
    async def test_execute_generates_execution_id(self):
        """Test that execution ID is generated if not provided."""
        registry = CommandRegistry()
        cmd = MockCommand("test")
        registry.register(cmd)

        executor = CommandExecutor(registry=registry)
        result = await executor.execute(
            command_name="test",
            args=[],
            session_id="session-123",
        )

        assert result.success is True
        assert cmd.last_context is not None
        assert cmd.last_context.execution_id is not None
        assert len(cmd.last_context.execution_id) > 0

    @pytest.mark.asyncio
    async def test_execute_uses_provided_execution_id(self):
        """Test that provided execution ID is used."""
        registry = CommandRegistry()
        cmd = MockCommand("test")
        registry.register(cmd)

        executor = CommandExecutor(registry=registry)
        result = await executor.execute(
            command_name="test",
            args=[],
            session_id="session-123",
            execution_id="exec-789",
        )

        assert result.success is True
        assert cmd.last_context is not None
        assert cmd.last_context.execution_id == "exec-789"

    @pytest.mark.asyncio
    async def test_execute_with_metadata(self):
        """Test executing command with metadata."""
        registry = CommandRegistry()
        cmd = MockCommand("test")
        registry.register(cmd)

        executor = CommandExecutor(registry=registry)
        metadata = {"key": "value", "number": 42}
        result = await executor.execute(
            command_name="test",
            args=[],
            session_id="session-123",
            metadata=metadata,
        )

        assert result.success is True
        assert cmd.last_context is not None
        assert cmd.last_context.metadata == metadata

    @pytest.mark.asyncio
    async def test_execute_with_raw_input(self):
        """Test executing command with raw input."""
        registry = CommandRegistry()
        cmd = MockCommand("test")
        registry.register(cmd)

        executor = CommandExecutor(registry=registry)
        raw_input = "/test arg1 arg2"
        result = await executor.execute(
            command_name="test",
            args=["arg1", "arg2"],
            session_id="session-123",
            raw_input=raw_input,
        )

        assert result.success is True
        assert cmd.last_context is not None
        assert cmd.last_context.raw_input == raw_input
