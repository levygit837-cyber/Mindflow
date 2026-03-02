from __future__ import annotations

import os
import subprocess
import uuid
from typing import TYPE_CHECKING

from deepagents.backends.protocol import ExecuteResponse
from deepagents.backends.sandbox import BaseSandbox

from omnimind_backend.infra.logging import get_logger

if TYPE_CHECKING:
    from pathlib import Path

_logger = get_logger(__name__)


class OmniMindSandbox(BaseSandbox):
    """Secure background sandbox for shell command execution.

    Implements SandboxBackendProtocol using BaseSandbox logic.
    Provides process-level isolation with timeouts and output limits.
    """

    def __init__(
        self,
        root_dir: str | Path | None = None,
        timeout: int = 60,
        max_output_bytes: int = 100_000,
        env: dict[str, str] | None = None,
        read_only: bool = False,
    ):
        """Initialize the sandbox with a specific working directory."""
        from pathlib import Path
        self.cwd = Path(root_dir).resolve() if root_dir else Path.cwd()
        self._default_timeout = timeout
        self._max_output_bytes = max_output_bytes
        self._env = env if env is not None else {}
        self._id = f"omnimind-{uuid.uuid4().hex[:8]}"
        self._read_only = read_only

    @property
    def id(self) -> str:
        return self._id

    def execute(
        self,
        command: str,
        *,
        timeout: int | None = None,
    ) -> ExecuteResponse:
        """Execute a shell command within the sandbox (subprocess-level)."""
        if not command:
            return ExecuteResponse(output="Error: Empty command", exit_code=1, truncated=False)

        # Enforce read-only mode
        if self._read_only:
            _WRITE_PATTERNS = [
                "rm ", "mv ", "cp ", "mkdir ", "touch ", "chmod ", "chown ",
                ">", ">>", "tee ", "dd ", "write", "delete", "truncate",
            ]
            cmd_lower = command.lower().strip()
            if any(pat in cmd_lower for pat in _WRITE_PATTERNS):
                return ExecuteResponse(
                    output="Error: Write operation blocked — agent is in READ_ONLY sandbox mode.",
                    exit_code=1,
                    truncated=False,
                )

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
                env=self._env,
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

            return ExecuteResponse(
                output=output,
                exit_code=result.returncode,
                truncated=truncated
            )

        except subprocess.TimeoutExpired:
            return ExecuteResponse(
                output=f"Error: Command timed out after {effective_timeout}s",
                exit_code=124,
                truncated=False
            )
        except Exception as e:
            return ExecuteResponse(
                output=f"Error executing command: {str(e)}",
                exit_code=1,
                truncated=False
            )

    def upload_files(self, files: list[tuple[str, bytes]]) -> list:
        # For simplicity in this L2 sandbox, we use local filesystem writes via root_dir
        from deepagents.backends.protocol import FileUploadResponse
        responses = []
        for path, content in files:
            full_path = self.cwd / path
            try:
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_bytes(content)
                responses.append(FileUploadResponse(path=path, error=None))
            except Exception as e:
                responses.append(FileUploadResponse(path=path, error=str(e)))
        return responses

    def download_files(self, paths: list[str]) -> list:
        from deepagents.backends.protocol import FileDownloadResponse
        responses = []
        for path in paths:
            full_path = self.cwd / path
            try:
                if full_path.exists():
                    content = full_path.read_bytes()
                    responses.append(FileDownloadResponse(path=path, content=content, error=None))
                else:
                    responses.append(FileDownloadResponse(path=path, content=None, error="not_found"))
            except Exception as e:
                responses.append(FileDownloadResponse(path=path, content=None, error=str(e)))
        return responses
