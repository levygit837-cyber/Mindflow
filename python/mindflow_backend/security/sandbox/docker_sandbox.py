"""Docker-based sandbox for secure command execution.

This module provides complete process isolation using Docker containers with:
- Network isolation
- Resource limits (CPU, memory)
- Read-only filesystem
- Automatic cleanup
"""

import docker
import tempfile
import shutil
from pathlib import Path
from typing import Any
from datetime import datetime, UTC

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.security.validators.bash_validators import validate_bash_command

_logger = get_logger(__name__)


class DockerSandboxConfig:
    """Configuration for Docker sandbox."""

    def __init__(
        self,
        image: str = "python:3.11-alpine",
        memory_limit: str = "100m",
        cpu_quota: int = 50000,  # 50% of one CPU
        network_disabled: bool = True,
        read_only: bool = True,
        timeout: int = 30,
    ):
        self.image = image
        self.memory_limit = memory_limit
        self.cpu_quota = cpu_quota
        self.network_disabled = network_disabled
        self.read_only = read_only
        self.timeout = timeout


class DockerSandbox:
    """Docker-based sandbox for secure command execution.

    Features:
    - Complete process isolation
    - Network isolation
    - Resource limits (CPU, memory)
    - Read-only filesystem
    - Automatic cleanup
    """

    def __init__(self, config: DockerSandboxConfig | None = None):
        """Initialize Docker sandbox."""
        self.config = config or DockerSandboxConfig()
        self.client = docker.from_env()
        self._ensure_image()

    def _ensure_image(self) -> None:
        """Ensure Docker image is available."""
        try:
            self.client.images.get(self.config.image)
        except docker.errors.ImageNotFound:
            _logger.info(f"Pulling Docker image: {self.config.image}")
            self.client.images.pull(self.config.image)

    async def execute(
        self,
        command: str,
        working_dir: str | None = None,
        env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Execute command in Docker sandbox.

        Args:
            command: Shell command to execute
            working_dir: Working directory (mounted read-only)
            env: Environment variables

        Returns:
            Execution result with stdout, stderr, exit_code
        """
        start_time = datetime.now(UTC)

        # Security validation BEFORE Docker
        security_decision = validate_bash_command(command)
        if security_decision.behavior != "passthrough":
            return {
                "success": False,
                "error": security_decision.message,
                "security_blocked": True,
                "exit_code": 1,
            }

        # Create temporary directory for workspace
        temp_dir = None
        volumes = {}

        if working_dir:
            temp_dir = tempfile.mkdtemp(prefix="mindflow_sandbox_")
            # Copy workspace to temp (read-only mount)
            shutil.copytree(working_dir, temp_dir, dirs_exist_ok=True)
            volumes[temp_dir] = {"bind": "/workspace", "mode": "ro"}

        try:
            # Run container
            container = self.client.containers.run(
                self.config.image,
                command=["sh", "-c", command],
                working_dir="/workspace" if working_dir else "/",
                environment=env or {},
                volumes=volumes,
                network_disabled=self.config.network_disabled,
                mem_limit=self.config.memory_limit,
                cpu_quota=self.config.cpu_quota,
                read_only=self.config.read_only,
                remove=True,
                detach=False,
                stdout=True,
                stderr=True,
                timeout=self.config.timeout,
            )

            # Decode output
            stdout = container.decode("utf-8") if container else ""

            execution_time = (datetime.now(UTC) - start_time).total_seconds()

            _logger.info(
                "docker_sandbox_execution",
                command=command[:100],
                execution_time=execution_time,
                success=True,
            )

            return {
                "success": True,
                "stdout": stdout,
                "stderr": "",
                "exit_code": 0,
                "execution_time": execution_time,
                "sandbox_type": "docker",
            }

        except docker.errors.ContainerError as e:
            # Command failed
            return {
                "success": False,
                "stdout": e.stdout.decode("utf-8") if e.stdout else "",
                "stderr": e.stderr.decode("utf-8") if e.stderr else "",
                "exit_code": e.exit_status,
                "error": f"Command failed with exit code {e.exit_status}",
            }

        except docker.errors.APIError as e:
            # Docker API error
            _logger.error("docker_api_error", error=str(e))
            return {
                "success": False,
                "error": f"Docker API error: {str(e)}",
                "exit_code": 1,
            }

        finally:
            # Cleanup temp directory
            if temp_dir and Path(temp_dir).exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
