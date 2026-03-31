"""
Unit tests for Memory command.
"""

import pytest
from mindflow_backend.commands.builtin.memory import MemoryCommand
from mindflow_backend.commands.types import CommandContext


@pytest.mark.unit
class TestMemoryCommand:
    """Test suite for MemoryCommand."""

    @pytest.mark.asyncio
    async def test_memory_stats(self):
        """Test /memory stats shows statistics."""
        cmd = MemoryCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["stats"],
            raw_input="/memory stats",
        )

        result = await cmd.execute(context)

        assert result.success is True
        assert "Memory Statistics" in result.message
        assert result.data is not None
        assert "total_entries" in result.data

    @pytest.mark.asyncio
    async def test_memory_clear(self):
        """Test /memory clear command."""
        cmd = MemoryCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["clear", "session-123"],
            raw_input="/memory clear session-123",
        )

        result = await cmd.execute(context)

        assert result.success is False
        assert result.error == "NOT_IMPLEMENTED"
        assert "session-123" in result.message

    @pytest.mark.asyncio
    async def test_memory_clear_missing_session(self):
        """Test /memory clear without session ID."""
        cmd = MemoryCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["clear"],
            raw_input="/memory clear",
        )

        result = await cmd.execute(context)

        assert result.success is False
        assert result.error == "MISSING_SESSION_ID"

    @pytest.mark.asyncio
    async def test_memory_search(self):
        """Test /memory search command."""
        cmd = MemoryCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["search", "authentication"],
            raw_input="/memory search authentication",
        )

        result = await cmd.execute(context)

        assert result.success is False
        assert result.error == "NOT_IMPLEMENTED"
        assert "authentication" in result.message

    @pytest.mark.asyncio
    async def test_memory_search_missing_query(self):
        """Test /memory search without query."""
        cmd = MemoryCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["search"],
            raw_input="/memory search",
        )

        result = await cmd.execute(context)

        assert result.success is False
        assert result.error == "MISSING_QUERY"

    @pytest.mark.asyncio
    async def test_memory_export(self):
        """Test /memory export command."""
        cmd = MemoryCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["export", "session-123"],
            raw_input="/memory export session-123",
        )

        result = await cmd.execute(context)

        assert result.success is False
        assert result.error == "NOT_IMPLEMENTED"

    @pytest.mark.asyncio
    async def test_memory_missing_subcommand(self):
        """Test /memory without subcommand."""
        cmd = MemoryCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=[],
            raw_input="/memory",
        )

        result = await cmd.execute(context)

        assert result.success is False
        assert result.error == "MISSING_SUBCOMMAND"

    @pytest.mark.asyncio
    async def test_memory_invalid_subcommand(self):
        """Test /memory with invalid subcommand."""
        cmd = MemoryCommand()
        context = CommandContext(
            session_id="test",
            user_id=None,
            execution_id="exec-1",
            args=["invalid"],
            raw_input="/memory invalid",
        )

        result = await cmd.execute(context)

        assert result.success is False
        assert result.error == "INVALID_SUBCOMMAND"
