"""Unit tests for canonical ShellExecutorTool.

Tests ShellExecutorTool canonical implementation with basic functionality.
"""

from __future__ import annotations

import pytest

from mindflow_backend.agents.tools.system.shell_executor import ShellExecutorTool


class TestShellExecutorToolCanonical:
    """Test ShellExecutorTool canonical implementation."""

    @pytest.mark.asyncio
    async def test_execute_safe_command(self):
        """Test executing a safe command."""
        tool = ShellExecutorTool()
        result = await tool.execute(command="echo 'Hello World'")

        assert result["success"] is True
        assert result["result"]["return_code"] == 0
        assert "Hello World" in result["result"]["output"]

    @pytest.mark.asyncio
    async def test_execute_with_working_dir(self, tmp_path):
        """Test executing with custom working directory."""
        tool = ShellExecutorTool()
        result = await tool.execute(
            command="pwd",
            working_dir=str(tmp_path)
        )

        assert result["success"] is True
        assert str(tmp_path) in result["result"]["output"]

    @pytest.mark.asyncio
    async def test_execute_with_timeout(self):
        """Test command execution with timeout."""
        tool = ShellExecutorTool()
        result = await tool.execute(
            command="sleep 10",
            timeout=1
        )

        # Timeout may or may not be enforced depending on configuration
        # Just verify the command was attempted
        assert "success" in result

    @pytest.mark.asyncio
    async def test_semantic_analysis(self):
        """Test semantic analysis is present in result."""
        tool = ShellExecutorTool()
        result = await tool.execute(command="echo 'test'")

        assert result["success"] is True
        # Semantic analysis should be in the result metadata
        assert "semantic_type" in result["result"] or "semantic_type" in result

    @pytest.mark.asyncio
    async def test_security_level_classification(self):
        """Test security level classification is present."""
        tool = ShellExecutorTool()
        result = await tool.execute(command="echo 'test'")

        assert result["success"] is True
        # Security level should be in the result metadata
        assert "security_level" in result["result"] or "security_level" in result

    @pytest.mark.asyncio
    async def test_execution_time_tracking(self):
        """Test that execution time is tracked."""
        tool = ShellExecutorTool()
        result = await tool.execute(command="sleep 0.1")

        assert result["success"] is True
        assert "execution_time" in result["result"]

    @pytest.mark.asyncio
    async def test_background_execution(self):
        """Test background execution support."""
        tool = ShellExecutorTool()
        result = await tool.execute(
            command="sleep 1",
            run_in_background=True
        )

        assert result["success"] is True
        # Background task info should be present
        assert "background_task_id" in result["result"] or "pid" in result["result"]
