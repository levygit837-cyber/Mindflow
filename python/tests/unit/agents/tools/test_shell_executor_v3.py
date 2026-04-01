"""Unit tests for ShellExecutorToolV3."""

from __future__ import annotations

import pytest

from mindflow_backend.agents.tools.system.shell_executor_v3 import (
    ShellExecutorInput,
    shell_execute,
)


class TestShellExecutorToolV3:
    """Test suite for ShellExecutorToolV3."""

    @pytest.mark.asyncio
    async def test_shell_execute_basic(self, tool_context):
        """Test basic command execution."""
        input_data = ShellExecutorInput(command="echo 'Hello World'")
        result = await shell_execute(input_data, tool_context)

        assert result["success"] is True
        assert "Hello World" in result["output"]
        assert result["return_code"] == 0

    @pytest.mark.asyncio
    async def test_shell_execute_with_output(self, tool_context):
        """Test command with output capture."""
        input_data = ShellExecutorInput(
            command="echo 'test output'",
            capture_output=True
        )
        result = await shell_execute(input_data, tool_context)

        assert result["success"] is True
        assert "test output" in result["output"]

    @pytest.mark.asyncio
    async def test_shell_execute_no_capture(self, tool_context):
        """Test command without output capture."""
        input_data = ShellExecutorInput(
            command="echo 'test'",
            capture_output=False
        )
        result = await shell_execute(input_data, tool_context)

        assert result["success"] is True
        assert result["output"] == ""

    @pytest.mark.asyncio
    async def test_shell_execute_with_timeout(self, tool_context):
        """Test command with timeout."""
        input_data = ShellExecutorInput(
            command="sleep 0.1",
            timeout=1
        )
        result = await shell_execute(input_data, tool_context)

        assert result["success"] is True
        assert result["timed_out"] is False

    @pytest.mark.asyncio
    async def test_shell_execute_timeout_exceeded(self, tool_context):
        """Test command that exceeds timeout."""
        input_data = ShellExecutorInput(
            command="sleep 5",
            timeout=1
        )
        result = await shell_execute(input_data, tool_context)

        assert result["timed_out"] is True
        assert result["return_code"] == -1

    @pytest.mark.asyncio
    async def test_shell_execute_working_directory(self, temp_dir, tool_context):
        """Test command with specific working directory."""
        input_data = ShellExecutorInput(
            command="pwd",
            working_dir=str(temp_dir)
        )
        result = await shell_execute(input_data, tool_context)

        assert result["success"] is True
        assert str(temp_dir) in result["output"]

    @pytest.mark.asyncio
    async def test_shell_execute_nonzero_return_code(self, tool_context):
        """Test command with non-zero return code."""
        input_data = ShellExecutorInput(
            command="exit 1",
            check_return_code=False
        )
        result = await shell_execute(input_data, tool_context)

        assert result["success"] is True
        assert result["return_code"] == 1

    @pytest.mark.asyncio
    async def test_shell_execute_check_return_code(self, tool_context):
        """Test that check_return_code marks failure."""
        input_data = ShellExecutorInput(
            command="exit 1",
            check_return_code=True
        )
        result = await shell_execute(input_data, tool_context)

        assert result["success"] is False
        assert result["return_code"] == 1

    @pytest.mark.asyncio
    async def test_shell_execute_dangerous_command_rm_rf(self, tool_context):
        """Test that dangerous rm -rf / is blocked."""
        input_data = ShellExecutorInput(command="rm -rf /")
        result = await shell_execute(input_data, tool_context)

        assert result["success"] is False
        assert result["error_code"] == "DANGEROUS_COMMAND"
        assert "rm -rf /" in result["error"]

    @pytest.mark.asyncio
    async def test_shell_execute_dangerous_command_mkfs(self, tool_context):
        """Test that dangerous mkfs is blocked."""
        input_data = ShellExecutorInput(command="mkfs /dev/sda")
        result = await shell_execute(input_data, tool_context)

        assert result["success"] is False
        assert result["error_code"] == "DANGEROUS_COMMAND"

    @pytest.mark.asyncio
    async def test_shell_execute_dangerous_command_fork_bomb(self, tool_context):
        """Test that fork bomb is blocked."""
        input_data = ShellExecutorInput(command=":(){ :|:& };:")
        result = await shell_execute(input_data, tool_context)

        assert result["success"] is False
        assert result["error_code"] == "DANGEROUS_COMMAND"

    @pytest.mark.asyncio
    async def test_shell_execute_dangerous_command_chmod_777(self, tool_context):
        """Test that chmod -R 777 is blocked."""
        input_data = ShellExecutorInput(command="chmod -R 777 /")
        result = await shell_execute(input_data, tool_context)

        assert result["success"] is False
        assert result["error_code"] == "DANGEROUS_COMMAND"

    @pytest.mark.asyncio
    async def test_shell_execute_with_permission_denied(self, tool_context_deny_permissions):
        """Test execution with denied permissions."""
        input_data = ShellExecutorInput(command="echo 'test'")
        result = await shell_execute(input_data, tool_context_deny_permissions)

        assert result["success"] is False
        assert result["error_code"] == "PERMISSION_DENIED"

    @pytest.mark.asyncio
    async def test_shell_execute_command_not_found(self, tool_context):
        """Test execution of non-existent command."""
        input_data = ShellExecutorInput(command="nonexistentcommand12345")
        result = await shell_execute(input_data, tool_context)

        assert result["success"] is False
        assert result["error_code"] == "COMMAND_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_shell_execute_stderr_capture(self, tool_context):
        """Test that stderr is captured."""
        input_data = ShellExecutorInput(
            command="echo 'error' >&2",
            capture_output=True
        )
        result = await shell_execute(input_data, tool_context)

        assert result["success"] is True
        assert "error" in result["stderr"]

    @pytest.mark.asyncio
    async def test_shell_execute_execution_time(self, tool_context):
        """Test that execution time is tracked."""
        input_data = ShellExecutorInput(command="sleep 0.1")
        result = await shell_execute(input_data, tool_context)

        assert result["success"] is True
        assert "execution_time" in result
        assert result["execution_time"] >= 0.1

    @pytest.mark.asyncio
    async def test_shell_execute_output_truncation(self, tool_context):
        """Test that large output is truncated."""
        # Generate large output (>100KB)
        input_data = ShellExecutorInput(
            command="python3 -c 'print(\"x\" * 200000)'"
        )
        result = await shell_execute(input_data, tool_context)

        assert result["success"] is True
        assert "[output truncated]" in result["output"]

    @pytest.mark.asyncio
    async def test_shell_execute_working_dir_not_found(self, tool_context):
        """Test execution with non-existent working directory."""
        input_data = ShellExecutorInput(
            command="pwd",
            working_dir="/nonexistent/directory"
        )
        result = await shell_execute(input_data, tool_context)

        assert result["success"] is False
        assert result["error_code"] == "DIRECTORY_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_shell_execute_multiline_command(self, tool_context):
        """Test execution of multiline command."""
        input_data = ShellExecutorInput(
            command="echo 'line1'\necho 'line2'"
        )
        result = await shell_execute(input_data, tool_context)

        assert result["success"] is True
        assert "line1" in result["output"]
        assert "line2" in result["output"]
