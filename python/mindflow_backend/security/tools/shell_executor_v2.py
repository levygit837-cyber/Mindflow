"""Enhanced shell executor with Docker sandbox and comprehensive security.

Integrates all Phase 0 security components:
- Docker sandbox isolation
- Bash command validation
- Network policy enforcement
- Security audit logging
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools.system_schemas import SHELL_EXECUTOR_SCHEMA
from mindflow_backend.security.sandbox.docker_sandbox import DockerSandbox, DockerSandboxConfig
from mindflow_backend.security.validators.bash_validators import validate_bash_command, SecurityDecision
from mindflow_backend.security.policies.network_policy import NetworkPolicy, NetworkAction
from mindflow_backend.security.audit.security_logger import get_security_logger

_logger = get_logger(__name__)


class ShellExecutorToolV2(AsyncToolInterface):
    """Enhanced shell executor with Docker sandbox and comprehensive security.

    Features:
    - Docker container isolation
    - Bash command validation (14 validators)
    - Network policy enforcement
    - Security audit logging
    - Resource limits (CPU, memory)
    - Automatic cleanup
    """

    def __init__(self, root_dir: str | None = None, use_docker: bool = True):
        """Initialize enhanced shell executor.

        Args:
            root_dir: Root directory for workspace isolation
            use_docker: Use Docker sandbox (default: True)
        """
        super().__init__()
        self.root_dir = root_dir
        self.use_docker = use_docker
        self.name = "shell_execute"
        self.description = "Execute shell commands with Docker isolation and security controls"
        self.default_timeout = 30
        self.max_output_bytes = 100_000

        # Initialize security components
        self.docker_sandbox = DockerSandbox() if use_docker else None
        self.network_policy = NetworkPolicy()
        self.security_logger = get_security_logger()

        self._schema = SHELL_EXECUTOR_SCHEMA

    async def execute(self, **kwargs) -> dict[str, Any]:
        """Execute shell command with comprehensive security.

        Args:
            command: Shell command to execute
            timeout: Timeout in seconds
            working_dir: Working directory
            environment: Environment variables
            capture_output: Capture command output

        Returns:
            Dictionary with execution result
        """
        try:
            command = kwargs["command"]
            timeout = kwargs.get("timeout") or self.default_timeout
            working_dir = kwargs.get("working_dir") or self.root_dir
            environment = kwargs.get("environment") or {}

            start_time = time.time()

            # Step 1: Bash command validation
            validation_result = validate_bash_command(command)

            if validation_result.behavior == "block":
                self.security_logger.log_command_blocked(
                    command=command,
                    reason=validation_result.message,
                    validator="bash_validators",
                )
                return self._format_result(
                    success=False,
                    error=f"Command blocked: {validation_result.message}",
                )

            # Step 2: Network policy validation
            network_action, network_reason = self.network_policy.validate_command(command)

            if network_action == NetworkAction.DENY:
                self.security_logger.log_network_blocked(
                    url="",
                    reason=network_reason,
                    command=command,
                )
                return self._format_result(
                    success=False,
                    error=f"Network access denied: {network_reason}",
                )

            if network_action == NetworkAction.ASK:
                # In production, this would prompt the user
                # For now, we log and allow
                _logger.warning(
                    "network_access_requires_approval",
                    command=command[:100],
                    reason=network_reason,
                )

            # Step 3: Execute in Docker sandbox
            if self.use_docker and self.docker_sandbox:
                result = await self.docker_sandbox.execute(
                    command=command,
                    working_dir=working_dir,
                    env=environment,
                )

                execution_time = time.time() - start_time

                # Log successful execution
                _logger.info(
                    "shell_command_executed",
                    command=command[:100],
                    success=result.get("success"),
                    execution_time=execution_time,
                    sandbox="docker",
                )

                return self._format_result(
                    success=result.get("success", False),
                    result={
                        "output": result.get("stdout", ""),
                        "stderr": result.get("stderr", ""),
                        "return_code": result.get("exit_code", 1),
                        "execution_time": execution_time,
                        "sandbox_type": "docker",
                    },
                )

            else:
                # Fallback to subprocess (not recommended for production)
                _logger.warning(
                    "docker_sandbox_disabled",
                    message="Falling back to subprocess execution (less secure)",
                )

                import subprocess

                try:
                    process = subprocess.Popen(
                        command,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        cwd=working_dir,
                        env=environment,
                        text=True,
                    )

                    stdout, stderr = process.communicate(timeout=timeout)
                    return_code = process.returncode
                    execution_time = time.time() - start_time

                    return self._format_result(
                        success=return_code == 0,
                        result={
                            "output": stdout or "",
                            "stderr": stderr or "",
                            "return_code": return_code,
                            "execution_time": execution_time,
                            "sandbox_type": "subprocess",
                        },
                    )

                except subprocess.TimeoutExpired:
                    process.kill()
                    return self._format_result(
                        success=False,
                        error=f"Command timed out after {timeout} seconds",
                    )

        except Exception as e:
            self.security_logger.log_suspicious_activity(
                activity="shell_execution_error",
                details={"error": str(e), "command": command[:100]},
            )

            return self._format_result(
                success=False,
                error=f"Shell execution failed: {str(e)}",
            )

    def get_schema(self) -> dict[str, Any]:
        """Get tool schema."""
        return self._schema.dict()
