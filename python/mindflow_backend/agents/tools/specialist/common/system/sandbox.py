"""
Sandbox tool for secure code execution. Provides isolated environment for running 
untrusted code with comprehensive security controls and resource limits.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any

from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools.system_schemas import SANDBOX_SCHEMA

_logger = get_logger(__name__)


class SandboxTool(AsyncToolInterface):
    """
    Sandbox tool for secure code execution with process isolation.
    """

    def __init__(self):
        super().__init__()
        self.name = "sandbox"
        self.description = "Secure code execution sandbox with process isolation"
        
        # Security settings
        self.max_execution_time = 30  # seconds
        self.max_memory = 100 * 1024 * 1024  # 100MB
        self.max_output_size = 1024 * 1024  # 1MB
        self.allowed_languages = ["python", "bash", "javascript"]
        self.restricted_modules = {
            "os", "subprocess", "sys", "importlib", "imp",
            "eval", "exec", "compile", "__import__"
        }
        self.restricted_commands = [
            "rm -rf /", "dd if=", "mkfs", "fdisk", "format",
            "shutdown", "reboot", "halt", "poweroff", "sudo"
        ]

        self._schema = SANDBOX_SCHEMA

    async def execute(self, **kwargs) -> dict[str, Any]:
        """
        Execute code in sandbox environment.
        Args:
            code: Code to execute
            language: Programming language
            timeout: Execution timeout
            working_directory: Working directory
            environment_vars: Environment variables
        Returns:
            Dictionary with execution result
        """
        try:
            code = kwargs["code"]
            language = kwargs.get("language", "python")
            timeout = kwargs.get("timeout", self.max_execution_time)
            working_directory = kwargs.get("working_directory")
            environment_vars = kwargs.get("environment_vars", {})

            # Security validation
            validation_result = self._validate_code(code, language)
            if not validation_result["valid"]:
                return self._format_result(
                    success=False,
                    error=validation_result["error"]
                )

            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Write code to file
                code_file = self._prepare_code_file(code, language, temp_path)
                
                # Prepare execution command
                command = self._get_execution_command(language, code_file, working_directory or temp_dir)
                
                # Execute in sandbox
                result = await self._execute_in_sandbox(
                    command, timeout, environment_vars, temp_dir
                )

                return self._format_result(
                    success=result["exit_code"] == 0,
                    result=result
                )

        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Sandbox execution error: {str(e)}"
            )

    def _validate_code(self, code: str, language: str) -> dict[str, Any]:
        """
        Validate code for security restrictions.
        Args:
            code: Code to validate
            language: Programming language
        Returns:
            Validation result
        """
        # Check language
        if language not in self.allowed_languages:
            return {
                "valid": False,
                "error": f"Language '{language}' not allowed. Allowed: {self.allowed_languages}"
            }

        # Check for restricted modules (Python)
        if language == "python":
            for restricted in self.restricted_modules:
                if restricted in code:
                    return {
                        "valid": False,
                        "error": f"Use of restricted module '{restricted}' not allowed"
                    }

        # Check for restricted commands (Bash)
        if language == "bash":
            for restricted in self.restricted_commands:
                if restricted in code.lower():
                    return {
                        "valid": False,
                        "error": f"Use of restricted command '{restricted}' not allowed"
                    }

        # Check code length
        if len(code) > 10000:  # 10KB limit
            return {
                "valid": False,
                "error": "Code too long (max 10KB)"
            }

        return {"valid": True}

    def _prepare_code_file(self, code: str, language: str, temp_dir: Path) -> Path:
        """
        Prepare code file for execution.
        Args:
            code: Code content
            language: Programming language
            temp_dir: Temporary directory
        Returns:
            Path to code file
        """
        if language == "python":
            code_file = temp_dir / "script.py"
            code_file.write_text(code)
        elif language == "bash":
            code_file = temp_dir / "script.sh"
            code_file.write_text(code)
            os.chmod(code_file, 0o755)
        elif language == "javascript":
            code_file = temp_dir / "script.js"
            code_file.write_text(code)
        else:
            raise ValueError(f"Unsupported language: {language}")

        return code_file

    def _get_execution_command(self, language: str, code_file: Path, working_dir: Path) -> list[str]:
        """
        Get execution command for language.
        Args:
            language: Programming language
            code_file: Path to code file
            working_dir: Working directory
        Returns:
            Command list
        """
        if language == "python":
            return [
                "python3", "-u", str(code_file)
            ]
        elif language == "bash":
            return [
                "bash", str(code_file)
            ]
        elif language == "javascript":
            return [
                "node", str(code_file)
            ]
        else:
            raise ValueError(f"Unsupported language: {language}")

    async def _execute_in_sandbox(
        self,
        command: list[str],
        timeout: int,
        environment_vars: dict[str, str],
        temp_dir: str
    ) -> dict[str, Any]:
        """
        Execute command in sandbox environment.
        Args:
            command: Command to execute
            timeout: Execution timeout
            environment_vars: Environment variables
            temp_dir: Temporary directory
        Returns:
            Execution result
        """
        import time
        start_time = time.time()

        # Prepare environment
        env = os.environ.copy()
        env.update(environment_vars)
        
        # Add security restrictions
        env.update({
            "PYTHONPATH": "",
            "PYTHONHOME": "",
            "TMPDIR": temp_dir,
            "HOME": temp_dir
        })

        try:
            # Execute with resource limits
            process = await asyncio.create_subprocess_exec(
                command,
                cwd=temp_dir,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=self._setup_sandbox_limits
            )

            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                exit_code = process.returncode
            except TimeoutError:
                process.kill()
                await process.wait()
                return {
                    "stdout": "",
                    "stderr": f"Execution timed out after {timeout} seconds",
                    "exit_code": -1,
                    "execution_time": timeout,
                    "memory_used": 0
                }

            execution_time = time.time() - start_time

            # Truncate output if too large
            if len(stdout) > self.max_output_size:
                stdout = stdout[:self.max_output_size] + "\n... Output truncated"

            if len(stderr) > self.max_output_size:
                stderr = stderr[:self.max_output_size] + "\n... Error output truncated"

            return {
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": exit_code,
                "execution_time": execution_time,
                "memory_used": self._estimate_memory_usage(process.pid)
            }

        except Exception as e:
            return {
                "stdout": "",
                "stderr": f"Sandbox execution failed: {str(e)}",
                "exit_code": -1,
                "execution_time": time.time() - start_time,
                "memory_used": 0
            }

    def _setup_sandbox_limits(self):
        """
        Setup resource limits for sandbox.
        """
        import resource
        
        # Set memory limit
        try:
            resource.setrlimit(resource.RLIMIT_AS, (self.max_memory, self.max_memory))
        except (ValueError, OSError):
            pass

        # Set CPU time limit
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (self.max_execution_time, self.max_execution_time))
        except (ValueError, OSError):
            pass

        # Set file size limit
        try:
            resource.setrlimit(resource.RLIMIT_FSIZE, (self.max_output_size, self.max_output_size))
        except (ValueError, OSError):
            pass

    def _estimate_memory_usage(self, pid: int) -> int:
        """
        Estimate memory usage of process.
        Args:
            pid: Process ID
        Returns:
            Memory usage in bytes
        """
        try:
            import psutil
            process = psutil.Process(pid)
            return process.memory_info().rss
        except ImportError:
            return 0
        except psutil.NoSuchProcess:
            return 0

    def get_schema(self) -> dict[str, Any]:
        """
        Get tool schema.
        """
        return self._schema.dict()
