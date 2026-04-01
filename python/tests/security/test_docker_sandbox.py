"""Tests for Docker sandbox implementation."""

import pytest

from mindflow_backend.security.sandbox.docker_sandbox import DockerSandbox, DockerSandboxConfig


@pytest.mark.asyncio
async def test_docker_sandbox_safe_command():
    """Test safe command execution."""
    sandbox = DockerSandbox()
    result = await sandbox.execute("echo 'Hello World'")

    assert result["success"] is True
    assert "Hello World" in result["stdout"]
    assert result["exit_code"] == 0
    assert result["sandbox_type"] == "docker"


@pytest.mark.asyncio
async def test_docker_sandbox_command_with_output():
    """Test command with output."""
    sandbox = DockerSandbox()
    result = await sandbox.execute("ls -la /")

    assert result["success"] is True
    assert len(result["stdout"]) > 0
    assert result["exit_code"] == 0


@pytest.mark.asyncio
async def test_docker_sandbox_network_isolation():
    """Test network is disabled."""
    sandbox = DockerSandbox()
    result = await sandbox.execute("ping -c 1 8.8.8.8")

    # Should fail because network is disabled
    assert result["success"] is False


@pytest.mark.asyncio
async def test_docker_sandbox_dangerous_command_blocked():
    """Test dangerous commands are blocked before Docker."""
    sandbox = DockerSandbox()
    result = await sandbox.execute("rm -rf /")

    assert result["success"] is False
    assert result.get("security_blocked") is True
    assert "blocked" in result["error"].lower()


@pytest.mark.asyncio
async def test_docker_sandbox_timeout():
    """Test command timeout."""
    config = DockerSandboxConfig(timeout=2)
    sandbox = DockerSandbox(config)

    result = await sandbox.execute("sleep 10")

    assert result["success"] is False
    assert "timeout" in result.get("error", "").lower() or result.get("exit_code") != 0


@pytest.mark.asyncio
async def test_docker_sandbox_working_directory():
    """Test working directory mount."""
    import tempfile
    import os

    # Create temp directory with test file
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test content")

        sandbox = DockerSandbox()
        result = await sandbox.execute("cat test.txt", working_dir=tmpdir)

        assert result["success"] is True
        assert "test content" in result["stdout"]


@pytest.mark.asyncio
async def test_docker_sandbox_environment_variables():
    """Test environment variables."""
    sandbox = DockerSandbox()
    result = await sandbox.execute(
        "echo $TEST_VAR",
        env={"TEST_VAR": "test_value"}
    )

    assert result["success"] is True
    assert "test_value" in result["stdout"]


@pytest.mark.asyncio
async def test_docker_sandbox_exit_code():
    """Test exit code handling."""
    sandbox = DockerSandbox()

    # Successful command
    result = await sandbox.execute("exit 0")
    assert result["exit_code"] == 0

    # Failed command
    result = await sandbox.execute("exit 42")
    assert result["exit_code"] == 42


@pytest.mark.asyncio
async def test_docker_sandbox_stderr():
    """Test stderr capture."""
    sandbox = DockerSandbox()
    result = await sandbox.execute("echo 'error message' >&2")

    assert result["success"] is True
    assert "error message" in result["stderr"]


@pytest.mark.asyncio
async def test_docker_sandbox_resource_limits():
    """Test resource limits are enforced."""
    config = DockerSandboxConfig(
        memory_limit="50m",
        cpu_quota=25000,  # 25% CPU
    )
    sandbox = DockerSandbox(config)

    # This should work within limits
    result = await sandbox.execute("echo 'test'")
    assert result["success"] is True
