"""
Unit tests for Config command.
"""

import pytest
from mindflow_backend.commands.builtin.config import ConfigCommand
from mindflow_backend.commands.types import CommandContext


@pytest.mark.unit
class TestConfigCommand:
    """Test suite for ConfigCommand."""

    @pytest.mark.asyncio
    async def test_config_get(self):
        """Test /config get command."""
        cmd = ConfigCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["get", "max_agents"],
            raw_input="/config get max_agents",
        )

        result = await cmd.execute(context)

        assert result.success is False
        assert result.error == "NOT_IMPLEMENTED"
        assert "max_agents" in result.message

    @pytest.mark.asyncio
    async def test_config_get_missing_key(self):
        """Test /config get without key."""
        cmd = ConfigCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["get"],
            raw_input="/config get",
        )

        result = await cmd.execute(context)

        assert result.success is False
        assert result.error == "MISSING_KEY"

    @pytest.mark.asyncio
    async def test_config_set(self):
        """Test /config set command."""
        cmd = ConfigCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["set", "max_agents", "10"],
            raw_input="/config set max_agents 10",
        )

        result = await cmd.execute(context)

        assert result.success is False
        assert result.error == "NOT_IMPLEMENTED"
        assert "max_agents" in result.message
        assert "10" in result.message

    @pytest.mark.asyncio
    async def test_config_set_missing_arguments(self):
        """Test /config set without key or value."""
        cmd = ConfigCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["set", "key"],
            raw_input="/config set key",
        )

        result = await cmd.execute(context)

        assert result.success is False
        assert result.error == "MISSING_ARGUMENTS"

    @pytest.mark.asyncio
    async def test_config_list(self):
        """Test /config list command."""
        cmd = ConfigCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["list"],
            raw_input="/config list",
        )

        result = await cmd.execute(context)

        assert result.success is True
        assert "Configuration keys" in result.message
        assert result.data is not None
        assert "keys" in result.data

    @pytest.mark.asyncio
    async def test_config_reset(self):
        """Test /config reset command."""
        cmd = ConfigCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["reset", "max_agents"],
            raw_input="/config reset max_agents",
        )

        result = await cmd.execute(context)

        assert result.success is False
        assert result.error == "NOT_IMPLEMENTED"

    @pytest.mark.asyncio
    async def test_config_missing_subcommand(self):
        """Test /config without subcommand."""
        cmd = ConfigCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=[],
            raw_input="/config",
        )

        result = await cmd.execute(context)

        assert result.success is False
        assert result.error == "MISSING_SUBCOMMAND"

    @pytest.mark.asyncio
    async def test_config_invalid_subcommand(self):
        """Test /config with invalid subcommand."""
        cmd = ConfigCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["invalid"],
            raw_input="/config invalid",
        )

        result = await cmd.execute(context)

        assert result.success is False
        assert result.error == "INVALID_SUBCOMMAND"
