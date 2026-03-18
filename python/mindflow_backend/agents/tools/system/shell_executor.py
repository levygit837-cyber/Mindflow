"""System and shell tools for MindFlow agents.

Provides system monitoring, process management, and shell execution
capabilities with security controls and performance optimizations.
"""

from __future__ import annotations

import os
import platform
import sys
import time
import signal
import uuid
import asyncio
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.agents.tools.security import (
    WorkspaceSecurityError,
    resolve_workspace_path,
    resolve_workspace_root,
    sanitize_environment,
    validate_shell_command,
)
from mindflow_backend.schemas.tools.system_schemas import SHELL_EXECUTOR_SCHEMA
from mindflow_backend.schemas.orchestration.orchestrator import AgentType

_logger = get_logger(__name__)


class ShellExecutorTool(AsyncToolInterface):
    """Shell execution tool with security controls."""
    
    def __init__(self, backend: Optional[Any] = None):
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
        
        self._schema = SHELL_EXECUTOR_SCHEMA
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
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
        try:
            command = kwargs["command"]
            timeout = kwargs.get("timeout") or self.default_timeout
            working_dir = kwargs.get("working_dir") or None
            # Use `or {}` instead of default= so None from Pydantic optional fields is handled
            environment = kwargs.get("environment") or {}
            capture_output = kwargs.get("capture_output") if kwargs.get("capture_output") is not None else True
            shell = kwargs.get("shell") if kwargs.get("shell") is not None else True
            check_return_code = kwargs.get("check_return_code") or False
            secure_runtime = bool(self.secure_mode or self.root_dir)

            if secure_runtime:
                validation_error = validate_shell_command(command, self.sandbox_mode)
                if validation_error:
                    return self._format_result(success=False, error=validation_error)

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
                    # Max number of child processes
                    _resource.setrlimit(_resource.RLIMIT_NPROC, (64, 64))

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
                
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                return_code = -1
                execution_time = timeout
                timed_out = True
            
            # Check return code if requested
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
                    "pid": process.pid,
                    "working_dir": str(effective_cwd),
                    "execution_time": execution_time,
                    "timeout": timed_out
                }
            )
        except WorkspaceSecurityError as e:
            return self._format_result(
                success=False,
                error=f"Workspace security error: {str(e)}"
            )
            
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Shell execution failed: {str(e)}"
            )
    
    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema."""
        return self._schema.dict()
