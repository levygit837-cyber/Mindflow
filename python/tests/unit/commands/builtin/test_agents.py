"""
Unit tests for Agents command.
"""

import pytest
from mindflow_backend.commands.builtin.agents import AgentsCommand
from mindflow_backend.commands.types import CommandContext


@pytest.mark.unit
class TestAgentsCommand:
    """Test suite for AgentsCommand."""

    @pytest.mark.asyncio
    async def test_agents_list(self):
        """Test /agents list shows all agents."""
        cmd = AgentsCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["list"],
            raw_input="/agents list",
        )

        result = await cmd.execute(context)

        assert result.success is True
        assert "Active agents" in result.message
        assert result.data is not None
        assert "agents" in result.data

    @pytest.mark.asyncio
    async def test_agents_spawn_valid_type(self):
        """Test /agents spawn with valid agent type."""
        cmd = AgentsCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["spawn", "planner"],
            raw_input="/agents spawn planner",
        )

        result = await cmd.execute(context)

        # Should fail with NOT_IMPLEMENTED since spawner not integrated yet
        assert result.success is False
        assert result.error == "NOT_IMPLEMENTED"
        assert "planner" in result.message

    @pytest.mark.asyncio
    async def test_agents_spawn_invalid_type(self):
        """Test /agents spawn with invalid agent type."""
        cmd = AgentsCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["spawn", "invalid"],
            raw_input="/agents spawn invalid",
        )

        result = await cmd.execute(context)

        assert result.success is False
        assert result.error == "INVALID_AGENT_TYPE"
        assert "Invalid agent type" in result.message

    @pytest.mark.asyncio
    async def test_agents_spawn_missing_type(self):
        """Test /agents spawn without agent type."""
        cmd = AgentsCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["spawn"],
            raw_input="/agents spawn",
        )

        result = await cmd.execute(context)

        assert result.success is False
        assert result.error == "MISSING_AGENT_TYPE"

    @pytest.mark.asyncio
    async def test_agents_kill(self):
        """Test /agents kill command."""
        cmd = AgentsCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["kill", "agent-123"],
            raw_input="/agents kill agent-123",
        )

        result = await cmd.execute(context)

        assert result.success is False
        assert result.error == "NOT_IMPLEMENTED"
        assert "agent-123" in result.message

    @pytest.mark.asyncio
    async def test_agents_status(self):
        """Test /agents status command."""
        cmd = AgentsCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["status", "agent-123"],
            raw_input="/agents status agent-123",
        )

        result = await cmd.execute(context)

        assert result.success is False
        assert result.error == "NOT_IMPLEMENTED"

    @pytest.mark.asyncio
    async def test_agents_missing_subcommand(self):
        """Test /agents without subcommand."""
        cmd = AgentsCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=[],
            raw_input="/agents",
        )

        result = await cmd.execute(context)

        assert result.success is False
        assert result.error == "MISSING_SUBCOMMAND"

    @pytest.mark.asyncio
    async def test_agents_invalid_subcommand(self):
        """Test /agents with invalid subcommand."""
        cmd = AgentsCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["invalid"],
            raw_input="/agents invalid",
        )

        result = await cmd.execute(context)

        assert result.success is False
        assert result.error == "INVALID_SUBCOMMAND"
