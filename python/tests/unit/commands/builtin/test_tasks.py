"""
Unit tests for Tasks command.
"""

import pytest
from mindflow_backend.commands.builtin.tasks import TasksCommand
from mindflow_backend.commands.types import CommandContext


@pytest.mark.unit
class TestTasksCommand:
    """Test suite for TasksCommand."""

    @pytest.mark.asyncio
    async def test_tasks_list(self):
        """Test /tasks list shows all tasks."""
        cmd = TasksCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["list"],
            raw_input="/tasks list",
        )

        result = await cmd.execute(context)

        assert result.success is True
        assert "Active tasks" in result.message
        assert result.data is not None
        assert "tasks" in result.data

    @pytest.mark.asyncio
    async def test_tasks_cancel(self):
        """Test /tasks cancel command."""
        cmd = TasksCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["cancel", "task-123"],
            raw_input="/tasks cancel task-123",
        )

        result = await cmd.execute(context)

        assert result.success is False
        assert result.error == "NOT_IMPLEMENTED"
        assert "task-123" in result.message

    @pytest.mark.asyncio
    async def test_tasks_cancel_missing_id(self):
        """Test /tasks cancel without task ID."""
        cmd = TasksCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["cancel"],
            raw_input="/tasks cancel",
        )

        result = await cmd.execute(context)

        assert result.success is False
        assert result.error == "MISSING_TASK_ID"

    @pytest.mark.asyncio
    async def test_tasks_status(self):
        """Test /tasks status command."""
        cmd = TasksCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["status", "task-123"],
            raw_input="/tasks status task-123",
        )

        result = await cmd.execute(context)

        assert result.success is False
        assert result.error == "NOT_IMPLEMENTED"

    @pytest.mark.asyncio
    async def test_tasks_logs(self):
        """Test /tasks logs command."""
        cmd = TasksCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["logs", "task-123"],
            raw_input="/tasks logs task-123",
        )

        result = await cmd.execute(context)

        assert result.success is False
        assert result.error == "NOT_IMPLEMENTED"

    @pytest.mark.asyncio
    async def test_tasks_missing_subcommand(self):
        """Test /tasks without subcommand."""
        cmd = TasksCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=[],
            raw_input="/tasks",
        )

        result = await cmd.execute(context)

        assert result.success is False
        assert result.error == "MISSING_SUBCOMMAND"

    @pytest.mark.asyncio
    async def test_tasks_invalid_subcommand(self):
        """Test /tasks with invalid subcommand."""
        cmd = TasksCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["invalid"],
            raw_input="/tasks invalid",
        )

        result = await cmd.execute(context)

        assert result.success is False
        assert result.error == "INVALID_SUBCOMMAND"
