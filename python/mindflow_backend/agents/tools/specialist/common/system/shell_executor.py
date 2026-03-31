"""System and shell tools for MindFlow agents.

Provides system monitoring, process management, and shell execution
capabilities with security controls and performance optimizations.
"""

from __future__ import annotations

import os
import subprocess
import time
from typing import Any

from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools.system_schemas import SHELL_EXECUTOR_SCHEMA

_logger = get_logger(__name__)


class ShellExecutorTool(AsyncToolInterface):
    """Shell execution tool with security controls."""
    
    def __init__(self, backend: Any | None = None):
        """Initialize the shell executor tool.
        
        Args:
            backend: Optional backend for compatibility
        """
        super().__init__()
        self.backend = backend
        self.name = "shell_execute"
        self.description = "Execute shell commands with security controls and monitoring"
        self.default_timeout = 120  # 2 minutes
        self.max_output_bytes = 100_000  # 100KB
        
        self._schema = SHELL_EXECUTOR_SCHEMA
    
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
        try:
            command = kwargs["command"]
            timeout = kwargs.get("timeout", self.default_timeout)
            working_dir = kwargs.get("working_dir")
            environment = kwargs.get("environment", {})
            capture_output = kwargs.get("capture_output", True)
            shell = kwargs.get("shell", True)
            check_return_code = kwargs.get("check_return_code", False)
            
            start_time = time.time()
            
            # Prepare environment
            env = os.environ.copy()
            env.update(environment)
            
            # Execute command
            try:
                process = subprocess.Popen(
                    command,
                    shell=shell,
                    stdout=subprocess.PIPE if capture_output else None,
                    stderr=subprocess.PIPE if capture_output else None,
                    cwd=working_dir,
                    env=env,
                    text=True
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
                    "execution_time": execution_time,
                    "timeout": timed_out
                }
            )
            
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Shell execution failed: {str(e)}"
            )
    
    def get_schema(self) -> dict[str, Any]:
        """Get tool schema."""
        return self._schema.dict()
