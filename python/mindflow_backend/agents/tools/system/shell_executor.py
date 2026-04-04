"""System and shell tools for MindFlow agents.

Provides system monitoring, process management, and shell execution
capabilities with security controls and performance optimizations.
"""

from __future__ import annotations

import os
import platform
import subprocess
import time
from pathlib import Path
from typing import Any

from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.agents.tools.workspace_security import (
    WorkspaceSecurityError,
    get_docker_sandbox_config,
    get_sandbox_type,
    resolve_workspace_path,
    resolve_workspace_root,
    sanitize_environment,
    validate_shell_command,
)
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.runtime.execution.background_task_manager import BackgroundTaskManager
from mindflow_backend.schemas.tools.system_schemas import SHELL_EXECUTOR_SCHEMA
from mindflow_backend.security.audit.security_logger import get_security_logger
from mindflow_backend.security.policies.network_policy import NetworkAction, NetworkPolicy

_logger = get_logger(__name__)


class ShellExecutorTool(AsyncToolInterface):
    """Shell execution tool with security controls."""
    
    def __init__(
        self,
        backend: Any | None = None,
        background_task_manager: BackgroundTaskManager | None = None,
        network_policy: NetworkPolicy | None = None,
        security_logger: Any | None = None,
        use_docker: bool | None = None,
    ):
        """Initialize the shell executor tool.
        
        Args:
            backend: Optional backend for compatibility
        """
        super().__init__()
        self.backend = backend
        self.name = "shell_execute"
        self.description = "Execute shell commands with security controls and monitoring"
        self.default_timeout = 30  # 30 seconds (reduced from 120 for security)
        self.max_output_bytes = 100_000  # 100KB
        self._background_task_manager = background_task_manager or BackgroundTaskManager()
        self._network_policy = network_policy or NetworkPolicy()
        self._security_logger = security_logger or get_security_logger()
        self._use_docker = use_docker
        
        self._schema = SHELL_EXECUTOR_SCHEMA

    @staticmethod
    def _analyze_command_semantics(command: str) -> str:
        """Classify shell commands into a stable semantic type."""
        command_lower = command.lower()

        dangerous_keywords = ["rm -rf", "dd if=", "mkfs", "format", "shutdown", "reboot"]
        if any(keyword in command_lower for keyword in dangerous_keywords):
            return "dangerous"

        network_keywords = ["curl", "wget", "nc", "netcat", "ssh", "scp", "rsync"]
        if any(keyword in command_lower for keyword in network_keywords):
            return "network"

        if command_lower.startswith("git "):
            return "git"

        write_keywords = [">", ">>", "tee", "mv", "cp", "mkdir", "touch"]
        if any(keyword in command_lower for keyword in write_keywords):
            return "write"

        search_keywords = ["grep", "find", "locate", "ag", "rg"]
        if any(keyword in command_lower for keyword in search_keywords):
            return "search"

        read_keywords = ["cat", "less", "more", "head", "tail", "ls", "stat"]
        if any(keyword in command_lower for keyword in read_keywords):
            return "read"

        execute_keywords = ["python", "node", "npm", "cargo", "go run", "java"]
        if any(keyword in command_lower for keyword in execute_keywords):
            return "execute"

        return "system"

    def _classify_security_level(self, command: str, validation_error: str | None) -> str:
        """Classify risk level for the current command."""
        if validation_error:
            return "critical"

        semantic_type = self._analyze_command_semantics(command)
        if semantic_type == "dangerous":
            return "dangerous"
        if semantic_type in {"write", "execute", "network", "git"}:
            return "moderate"
        return "safe"

    def _log_command_blocked(self, *, command: str, reason: str) -> None:
        """Emit a structured audit event for blocked commands when available."""
        if hasattr(self._security_logger, "log_command_blocked"):
            self._security_logger.log_command_blocked(
                command=command,
                reason=reason,
                validator="workspace_security",
            )

    def _log_network_blocked(self, *, command: str, reason: str) -> None:
        """Emit a structured audit event for blocked network access when available."""
        if hasattr(self._security_logger, "log_network_blocked"):
            self._security_logger.log_network_blocked(
                url="",
                reason=reason,
                command=command,
            )

    def _log_suspicious_activity(self, *, activity: str, details: dict[str, Any]) -> None:
        """Emit suspicious-activity audit events without hard dependency on logger shape."""
        if hasattr(self._security_logger, "log_suspicious_activity"):
            self._security_logger.log_suspicious_activity(
                activity=activity,
                details=details,
            )

    def _can_use_docker(self) -> bool:
        """Return whether Docker sandbox execution is available for this runtime."""
        try:
            return get_sandbox_type() == "docker"
        except Exception as exc:  # pragma: no cover - defensive fallback
            _logger.warning("docker_sandbox_check_failed", error=str(exc))
            return False

    @staticmethod
    def _cpu_limit_to_quota(raw_cpu_limit: Any) -> int:
        """Convert a CPU limit value to Docker's quota units."""
        try:
            return max(1, int(float(raw_cpu_limit) * 100000))
        except (TypeError, ValueError):
            return 100000

    def _build_docker_sandbox(self):
        """Build a Docker sandbox lazily to avoid import-time Docker dependency."""
        from mindflow_backend.security.sandbox.docker_sandbox import (
            DockerSandbox,
            DockerSandboxConfig,
        )

        config = get_docker_sandbox_config()
        return DockerSandbox(
            DockerSandboxConfig(
                image=config["image"],
                memory_limit=config["memory_limit"],
                cpu_quota=self._cpu_limit_to_quota(config["cpu_limit"]),
                network_disabled=str(config["network_mode"]).lower() in {"none", "disabled", "false"},
                read_only=bool(config["read_only_root_fs"]),
                timeout=int(config["timeout_seconds"]),
            )
        )

    async def _execute_docker_foreground(
        self,
        *,
        command: str,
        cwd: str,
        env: dict[str, str],
        timeout: int,
        capture_output: bool,
    ) -> dict[str, Any]:
        """Execute the command in the optional Docker sandbox."""
        sandbox = self._build_docker_sandbox()
        result = await sandbox.execute(
            command=command,
            working_dir=cwd,
            env=env,
        )

        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        if not capture_output:
            stdout = ""
            stderr = ""

        return {
            "success": result.get("success", False),
            "stdout": stdout,
            "stderr": stderr,
            "return_code": result.get("exit_code", 1),
            "execution_time": result.get("execution_time", float(timeout)),
            "timed_out": "timeout" in str(result.get("error", "")).lower(),
            "sandbox_type": result.get("sandbox_type", "docker"),
            "error": result.get("error"),
        }
    
    async def execute(self, **kwargs) -> dict[str, Any]:
        """Execute shell command.
        
        Args:
            command: Shell command to execute
            timeout: Timeout in seconds
            working_dir: Working directory
            environment: Environment variables
            capture_output: Capture command output
            shell: Use system shell
            check_return_code: Check return code for success
            
        Returns:
            Dictionary with execution result
        """
        command = kwargs.get("command", "")
        try:
            command = kwargs["command"]
            timeout = kwargs.get("timeout") or self.default_timeout
            working_dir = kwargs.get("working_dir") or None
            # Use `or {}` instead of default= so None from Pydantic optional fields is handled
            environment = kwargs.get("environment") or {}
            capture_output = kwargs.get("capture_output") if kwargs.get("capture_output") is not None else True
            shell = kwargs.get("shell") if kwargs.get("shell") is not None else True
            check_return_code = kwargs.get("check_return_code") or False
            run_in_background = kwargs.get("run_in_background") or False
            use_docker = kwargs.get("use_docker")
            if use_docker is None:
                use_docker = self._use_docker
            session_id = kwargs.get("session_id")
            task_id = kwargs.get("task_id")
            tool_call_id = kwargs.get("tool_call_id")
            description = kwargs.get("description")
            secure_runtime = bool(self.secure_mode or self.root_dir)
            validation_error = None
            semantic_type = self._analyze_command_semantics(command)
            security_level = self._classify_security_level(command, validation_error)

            network_action, network_reason = self._network_policy.validate_command(command)
            if network_action == NetworkAction.DENY:
                self._log_network_blocked(command=command, reason=network_reason)
                return self._format_result(
                    success=False,
                    result={
                        "semantic_type": semantic_type,
                        "security_level": "critical",
                    },
                    error=f"Network access denied: {network_reason}",
                )
            if network_action == NetworkAction.ASK:
                _logger.warning(
                    "network_access_requires_approval",
                    command=command[:100],
                    reason=network_reason,
                )

            if secure_runtime:
                validation_error = validate_shell_command(command, self.sandbox_mode)
                security_level = self._classify_security_level(command, validation_error)
                if validation_error:
                    self._log_command_blocked(command=command, reason=validation_error)
                    return self._format_result(
                        success=False,
                        result={
                            "semantic_type": semantic_type,
                            "security_level": security_level,
                        },
                        error=validation_error,
                    )

            if secure_runtime:
                if working_dir:
                    effective_cwd = resolve_workspace_path(working_dir, self.root_dir)
                else:
                    effective_cwd = resolve_workspace_root(self.root_dir)
            else:
                effective_cwd = Path(working_dir).resolve() if working_dir else Path.cwd()
            
            start_time = time.time()
            
            if secure_runtime:
                env = sanitize_environment(environment, cwd=effective_cwd)
            else:
                env = os.environ.copy()
                env.update(environment)

            if run_in_background:
                return await self._execute_background(
                    command=command,
                    cwd=str(effective_cwd),
                    env=env,
                    timeout=timeout,
                    semantic_type=semantic_type,
                    security_level=security_level,
                    session_id=session_id,
                    task_id=task_id,
                    tool_call_id=tool_call_id,
                    description=description,
                )

            sandbox_type = "subprocess"
            docker_result: dict[str, Any] | None = None
            if use_docker:
                if self._can_use_docker():
                    docker_result = await self._execute_docker_foreground(
                        command=command,
                        cwd=str(effective_cwd),
                        env=env,
                        timeout=timeout,
                        capture_output=capture_output,
                    )
                    sandbox_type = docker_result.get("sandbox_type", "docker")
                else:
                    _logger.warning(
                        "docker_sandbox_unavailable",
                        command=command[:100],
                        message="Docker sandbox requested but unavailable. Falling back to subprocess.",
                    )
            
            if docker_result is None:
                # Build resource-limiting preexec_fn for subprocess (Linux only)
                preexec = None
                if platform.system() == "Linux" and secure_runtime:
                    import resource as _resource

                    cpu_limit = min(int(timeout), 30)
                    mem_limit = 256 * 1024 * 1024  # 256 MB

                    def _set_resource_limits() -> None:  # noqa: WPS430
                        # CPU time limit (seconds)
                        _resource.setrlimit(_resource.RLIMIT_CPU, (cpu_limit, cpu_limit))
                        # Virtual memory limit
                        _resource.setrlimit(_resource.RLIMIT_AS, (mem_limit, mem_limit))

                    preexec = _set_resource_limits

                # Execute command
                try:
                    process = subprocess.Popen(
                        command,
                        shell=shell,
                        stdout=subprocess.PIPE if capture_output else None,
                        stderr=subprocess.PIPE if capture_output else None,
                        cwd=str(effective_cwd),
                        env=env,
                        text=True,
                        preexec_fn=preexec,
                    )
                    
                    stdout, stderr = process.communicate(timeout=timeout)
                    return_code = process.returncode
                    execution_time = time.time() - start_time
                    timed_out = False
                    pid = process.pid
                    
                except subprocess.TimeoutExpired:
                    process.kill()
                    stdout, stderr = process.communicate()
                    return_code = -1
                    execution_time = timeout
                    timed_out = True
                    pid = process.pid
            else:
                stdout = docker_result.get("stdout", "")
                stderr = docker_result.get("stderr", "")
                return_code = docker_result.get("return_code", 1)
                execution_time = docker_result.get("execution_time", time.time() - start_time)
                timed_out = docker_result.get("timed_out", False)
                success = docker_result.get("success", False)
                pid = None
            
            # Check return code if requested
            if docker_result is None:
                success = True
            if check_return_code and return_code != 0:
                success = False
            
            # Truncate output if too large
            if stdout and len(stdout) > self.max_output_bytes:
                stdout = stdout[:self.max_output_bytes] + "\n...[truncated]"
            
            if stderr and len(stderr) > self.max_output_bytes:
                stderr = stderr[:self.max_output_bytes] + "\n...[truncated]"
            
            return self._format_result(
                success=success,
                result={
                    "output": stdout or "",
                    "stderr": stderr or "",
                    "return_code": return_code,
                    "pid": pid,
                    "working_dir": str(effective_cwd),
                    "execution_time": execution_time,
                    "timeout": timed_out,
                    "sandbox_type": sandbox_type,
                    "semantic_type": semantic_type,
                    "security_level": security_level,
                }
            )
        except WorkspaceSecurityError as e:
            self._log_suspicious_activity(
                activity="shell_workspace_security_error",
                details={"error": str(e), "command": command[:100]},
            )
            return self._format_result(
                success=False,
                result={
                    "semantic_type": self._analyze_command_semantics(command),
                    "security_level": "critical",
                },
                error=f"Workspace security error: {str(e)}"
            )
            
        except Exception as e:
            self._log_suspicious_activity(
                activity="shell_execution_error",
                details={"error": str(e), "command": command[:100] if command else ""},
            )
            return self._format_result(
                success=False,
                result={
                    "semantic_type": self._analyze_command_semantics(command) if command else "system",
                    "security_level": self._classify_security_level(command, None) if command else "safe",
                },
                error=f"Shell execution failed: {str(e)}"
            )

    async def _execute_background(
        self,
        *,
        command: str,
        cwd: str,
        env: dict[str, str],
        timeout: int,
        semantic_type: str,
        security_level: str,
        session_id: str | None,
        task_id: str | None,
        tool_call_id: str | None,
        description: str | None,
    ) -> dict[str, Any]:
        """Run a shell command in the background via the canonical task manager."""
        try:
            background_task = await self._background_task_manager.spawn(
                command=command,
                cwd=cwd,
                env=env,
                description=description or f"Shell command: {command[:120]}",
                session_id=session_id,
                task_id=task_id,
                tool_call_id=tool_call_id,
            )
        except Exception as e:
            return self._format_result(
                success=False,
                result={
                    "semantic_type": semantic_type,
                    "security_level": security_level,
                },
                error=f"Failed to start background process: {str(e)}",
            )

        return self._format_result(
            success=True,
            result={
                "background": True,
                "background_task_id": background_task.background_task_id,
                "process_id": background_task.background_task_id,
                "pid": background_task.pid,
                "command": command,
                "working_dir": cwd,
                "timeout": timeout,
                "sandbox_type": "background_task",
                "semantic_type": semantic_type,
                "security_level": security_level,
                "message": f"Command started in background with PID {background_task.pid}",
            },
        )

    async def get_background_status(self, process_id: str) -> dict[str, Any]:
        """Return canonical status for a managed background process."""
        status = await self._background_task_manager.get_status(process_id)
        if not status.get("success"):
            status["error_code"] = "PROCESS_NOT_FOUND"
        if status.get("success"):
            status.setdefault("background_task_id", process_id)
            status.setdefault("process_id", process_id)
        return status

    async def kill_background_process(self, process_id: str) -> dict[str, Any]:
        """Terminate a managed background process."""
        result = await self._background_task_manager.kill(process_id)
        if not result.get("success"):
            result["error_code"] = "PROCESS_NOT_FOUND"
        if result.get("success"):
            result.setdefault("background_task_id", process_id)
            result.setdefault("process_id", process_id)
            result.setdefault("message", "Process killed successfully")
        return result
    
    def get_schema(self) -> dict[str, Any]:
        """Get tool schema."""
        return self._schema.dict()
