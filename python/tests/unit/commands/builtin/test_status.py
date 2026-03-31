"""
Unit tests for Status command.
"""

import pytest
from mindflow_backend.commands.builtin.status import StatusCommand
from mindflow_backend.commands.types import CommandContext


@pytest.mark.unit
class TestStatusCommand:
    """Test suite for StatusCommand."""

    @pytest.mark.asyncio
    async def test_status_all(self):
        """Test /status shows all status information."""
        cmd = StatusCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=[],
            raw_input="/status",
        )

        result = await cmd.execute(context)

        assert result.success is True
        assert "System Status" in result.message
        assert "AGENTS:" in result.message
        assert "TASKS:" in result.message
        assert "MEMORY:" in result.message
        assert "SERVICES:" in result.message
        assert result.data is not None
        assert "agents" in result.data
        assert "tasks" in result.data
        assert "memory" in result.data
        assert "services" in result.data

    @pytest.mark.asyncio
    async def test_status_agents(self):
        """Test /status agents shows only agent status."""
        cmd = StatusCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["agents"],
            raw_input="/status agents",
        )

        result = await cmd.execute(context)

        assert result.success is True
        assert "Active agents" in result.message
        assert result.data is not None
        assert "active_count" in result.data

    @pytest.mark.asyncio
    async def test_status_tasks(self):
        """Test /status tasks shows only task status."""
        cmd = StatusCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["tasks"],
            raw_input="/status tasks",
        )

        result = await cmd.execute(context)

        assert result.success is True
        assert "Running tasks" in result.message
        assert result.data is not None
        assert "running" in result.data
        assert "queued" in result.data

    @pytest.mark.asyncio
    async def test_status_memory(self):
        """Test /status memory shows only memory status."""
        cmd = StatusCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["memory"],
            raw_input="/status memory",
        )

        result = await cmd.execute(context)

        assert result.success is True
        assert "Total entries" in result.message
        assert result.data is not None
        assert "total_entries" in result.data

    @pytest.mark.asyncio
    async def test_status_services(self):
        """Test /status services shows only service health."""
        cmd = StatusCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["services"],
            raw_input="/status services",
        )

        result = await cmd.execute(context)

        assert result.success is True
        assert "postgresql" in result.message
        assert "rabbitmq" in result.message
        assert result.data is not None
        assert "services" in result.data

    @pytest.mark.asyncio
    async def test_status_invalid_section(self):
        """Test /status with invalid section returns error."""
        cmd = StatusCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["invalid"],
            raw_input="/status invalid",
        )

        result = await cmd.execute(context)

        assert result.success is False
        assert "Unknown status section" in result.message
        assert result.error == "INVALID_SECTION"
