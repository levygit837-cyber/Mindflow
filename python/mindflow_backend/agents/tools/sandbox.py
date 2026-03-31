"""
Sandbox tool for secure command execution.
"""

from __future__ import annotations

import subprocess
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.orchestration.orchestrator import SandboxMode

from .security import (
    normalize_sandbox_mode,
    sanitize_environment,
    secure_sandbox_enabled,
    validate_shell_command,
)

if TYPE_CHECKING:
    from pathlib import Path

_logger = get_logger(__name__)


class _SandboxResult(dict):
    """Backward-compatible sandbox result with dict and attribute access."""

    def __getattr__(self, item: str):
        try:
            return self[item]
        except KeyError as exc:
            raise AttributeError(item) from exc


class MindFlowSandbox:
    """
    Secure background sandbox for shell command execution.
    Provides process-level isolation with timeouts and output limits.
    """
    
    def __init__(
        self, 
        root_dir: str | Path | None = None, 
        timeout: int = 60, 
        max_output_bytes: int = 100_000, 
        env: dict[str, str] | None = None, 
        read_only: bool = False,
        mode: SandboxMode | str | None = None,
    ):
        """
        Initialize the sandbox with a specific working directory.
        """
        from pathlib import Path
        
        self.cwd = Path(root_dir).resolve() if root_dir else Path.cwd()
        self._default_timeout = timeout
        self._max_output_bytes = max_output_bytes
        self._env = env if env is not None else {}
        self._id = f"mindflow-{uuid.uuid4().hex[:8]}"
        self._read_only = read_only
        if mode is None:
            mode = SandboxMode.READ_ONLY if read_only else SandboxMode.FULL
        self.mode = normalize_sandbox_mode(mode)
        self.secure_mode = secure_sandbox_enabled()
    
    @property
    def id(self) -> str:
        return self._id
    
    def execute(self, command: str, *, timeout: int | None = None) -> dict:
        """
        Execute a shell command within the sandbox (subprocess-level).
        """
        if not command:
            return _SandboxResult({
                "output": "Error: Empty command",
                "exit_code": 1,
                "truncated": False
            })
        
        if self.secure_mode:
            validation_error = validate_shell_command(command, self.mode)
            if validation_error:
                return _SandboxResult({
                    "output": f"Error: {validation_error}",
                    "exit_code": 1,
                    "truncated": False
                })
        
        effective_timeout = timeout if timeout is not None else self._default_timeout
        
        try:
            _logger.info("sandbox_executing", sandbox_id=self.id, command=command)
            
            # Execute in a shell-like environment but with limited context
            result = subprocess.run(
                command,
                shell=True,
                check=False,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
                env=sanitize_environment(self._env, cwd=self.cwd),
                cwd=str(self.cwd),
            )
            
            output_parts = []
            if result.stdout:
                output_parts.append(result.stdout)
            if result.stderr:
                output_parts.append(f"[stderr] {result.stderr}")
            
            output = "\n".join(output_parts) if output_parts else "<no output>"
            truncated = False
            
            if len(output) > self._max_output_bytes:
                output = output[:self._max_output_bytes] + "\n\n... [output truncated]"
                truncated = True
            
            return _SandboxResult({
                "output": output,
                "exit_code": result.returncode,
                "truncated": truncated
            })
            
        except subprocess.TimeoutExpired:
            return _SandboxResult({
                "output": f"Error: Command timed out after {effective_timeout}s",
                "exit_code": 124,
                "truncated": False
            })
        except Exception as e:
            return _SandboxResult({
                "output": f"Error executing command: {str(e)}",
                "exit_code": 1,
                "truncated": False
            })

    def write(self, path: str, content: str, *, encoding: str = "utf-8") -> _SandboxResult:
        """Legacy convenience helper for writing a file inside the sandbox."""
        try:
            full_path = (self.cwd / path).resolve()
            full_path.relative_to(self.cwd)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding=encoding)
            return _SandboxResult({"error": None, "path": str(full_path)})
        except Exception as e:
            return _SandboxResult({"error": str(e), "path": path})

    def read(self, path: str, *, encoding: str = "utf-8") -> str:
        """Legacy convenience helper for reading a file inside the sandbox."""
        full_path = (self.cwd / path).resolve()
        full_path.relative_to(self.cwd)
        return full_path.read_text(encoding=encoding)
    
    def upload_files(self, files: list[tuple[str, bytes]]) -> list:
        """
        Upload files to the sandbox.
        """
        responses = []
        for path, content in files:
            full_path = self.cwd / path
            try:
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_bytes(content)
                responses.append({"path": path, "error": None})
            except Exception as e:
                responses.append({"path": path, "error": str(e)})
        return responses
    
    def download_files(self, paths: list[str]) -> list:
        """
        Download files from the sandbox.
        """
        responses = []
        for path in paths:
            full_path = self.cwd / path
            try:
                if full_path.exists():
                    content = full_path.read_bytes()
                    responses.append({"path": path, "content": content, "error": None})
                else:
                    responses.append({"path": path, "content": None, "error": "not_found"})
            except Exception as e:
                responses.append({"path": path, "content": None, "error": str(e)})
        return responses
