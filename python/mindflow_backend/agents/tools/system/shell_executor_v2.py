"""Shell executor tool v2 compatibility adapter.

The v2 surface still owns validator-heavy compatibility behavior, but the
actual shell execution lifecycle now delegates to the canonical unsuffixed
shell tool.
"""

from __future__ import annotations

import os
import re
from typing import Any

from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.agents.tools.security.bash_validators import (
    get_command_security_issues,
    is_command_safe,
    validate_bash_command,
)
from mindflow_backend.agents.tools.system.shell_executor import ShellExecutorTool
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.runtime.execution.background_task_manager import BackgroundTaskManager
from mindflow_backend.schemas.tools.shell_schemas_v2 import (
    BashSecurityLevel,
    CommandSemanticType,
    ShellExecutorInput,
)
from mindflow_backend.schemas.tools.tool_permissions import PermissionBehavior
from mindflow_backend.services.orchestration import get_execution_task_service

_logger = get_logger(__name__)


# ============================================================================
# ShellExecutorTool v2
# ============================================================================

class ShellExecutorToolV2(AsyncToolInterface):
    """Enhanced shell command executor matching Claude Code standards.

    Features:
    - All 11 bash security validators integrated
    - Command semantic analysis (READ, WRITE, DANGEROUS, etc.)
    - Security level classification (SAFE, MODERATE, DANGEROUS, CRITICAL)
    - Background execution support
    - Command streaming/progress
    - Timeout control
    - Working directory management
    - Environment variable isolation
    """

    name = "shell_execute_v2"
    description = (
        "Execute shell commands with comprehensive security validation, "
        "semantic analysis, background execution, and progress tracking."
    )

    def __init__(
        self,
        root_dir: str | None = None,
        background_task_manager: BackgroundTaskManager | None = None,
    ):
        """Initialize ShellExecutorTool v2.

        Args:
            root_dir: Root directory for command execution (workspace root)
        """
        super().__init__()
        self.root_dir = root_dir
        self._background_task_manager = background_task_manager or BackgroundTaskManager(
            execution_task_service=get_execution_task_service(),
        )
        self._canonical_tool = ShellExecutorTool(
            background_task_manager=self._background_task_manager,
        )

    async def execute(self, **kwargs) -> dict[str, Any]:
        """Execute shell command with full validation and security checks."""
        execution_kwargs = dict(kwargs)
        session_id = execution_kwargs.pop("session_id", None)
        task_id = execution_kwargs.pop("task_id", None)
        tool_call_id = execution_kwargs.pop("tool_call_id", None)
        description = execution_kwargs.pop("description", None)

        # Parse and validate input
        try:
            input_data = ShellExecutorInput(**execution_kwargs)
        except Exception as e:
            return {
                "success": False,
                "error": f"Invalid input: {e}",
                "error_code": "INVALID_INPUT"
            }

        command = input_data.command

        # Security validation: run all 11 bash validators
        security_decision = validate_bash_command(command, input_data.sandbox_mode)

        if security_decision.behavior == PermissionBehavior.DENY:
            return {
                "success": False,
                "error": security_decision.message,
                "error_code": "SECURITY_VIOLATION",
                "security_level": "CRITICAL",
                "blocked_by": "bash_validators"
            }

        if security_decision.behavior == PermissionBehavior.ASK:
            # In production, this would trigger user confirmation
            # For now, we'll log and proceed with caution
            _logger.warning(
                f"Command requires approval: {command[:100]}",
                extra={"reason": security_decision.message}
            )

        # Analyze command semantics
        semantic_type = self._analyze_command_semantics(command)
        security_level = self._classify_security_level(command, security_decision)

        # Get all security issues (for logging/debugging)
        security_issues = get_command_security_issues(command)
        if security_issues:
            _logger.info(
                f"Command has {len(security_issues)} security concerns",
                extra={"command": command[:100], "issues": security_issues}
            )

        if security_decision.behavior == PermissionBehavior.ASK and self._should_block_ask_command(
            command=command,
            semantic_type=semantic_type,
            security_issues=security_issues,
            security_message=security_decision.message,
            security_reason=getattr(security_decision, "reason", None),
        ):
            return {
                "success": False,
                "error": security_decision.message or "Command blocked by security policy",
                "error_code": "SECURITY_VIOLATION",
                "security_level": security_level.value,
                "blocked_by": "bash_validators",
            }

        # Determine working directory
        cwd = input_data.working_dir or self.root_dir or os.getcwd()
        cwd = os.path.abspath(cwd)

        # Prepare environment
        env = os.environ.copy()
        if input_data.environment:
            env.update(input_data.environment)

        try:
            # Background execution
            if input_data.run_in_background:
                return await self._execute_background(
                    command=command,
                    cwd=cwd,
                    env=env,
                    timeout=input_data.timeout,
                    semantic_type=semantic_type,
                    security_level=security_level,
                    session_id=session_id,
                    task_id=task_id,
                    tool_call_id=tool_call_id,
                    description=description,
                )

            # Foreground execution
            return await self._execute_foreground(
                command=command,
                cwd=cwd,
                env=env,
                timeout=input_data.timeout,
                capture_output=input_data.capture_output,
                semantic_type=semantic_type,
                security_level=security_level
            )

        except Exception as e:
            _logger.error(f"Error executing command: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Command execution failed: {e}",
                "error_code": "EXECUTION_ERROR",
                "command": command[:100]
            }

    async def _execute_foreground(
        self,
        command: str,
        cwd: str,
        env: dict[str, str],
        timeout: int | None,
        capture_output: bool,
        semantic_type: CommandSemanticType,
        security_level: BashSecurityLevel
    ) -> dict[str, Any]:
        """Execute command through the canonical shell tool and normalize v2 output."""
        canonical_tool = self._get_canonical_tool()
        result = await canonical_tool.execute(
            command=command,
            timeout=timeout,
            working_dir=cwd,
            environment=env,
            capture_output=capture_output,
            shell=True,
            check_return_code=False,
        )
        return self._normalize_canonical_execution(
            result,
            command=command,
            cwd=cwd,
            timeout=timeout,
            semantic_type=semantic_type,
            security_level=security_level,
        )

    async def _execute_background(
        self,
        command: str,
        cwd: str,
        env: dict[str, str],
        timeout: int | None,
        semantic_type: CommandSemanticType,
        security_level: BashSecurityLevel,
        session_id: str | None,
        task_id: str | None,
        tool_call_id: str | None,
        description: str | None,
    ) -> dict[str, Any]:
        """Execute command in background via the canonical shell tool."""
        canonical_tool = self._get_canonical_tool()
        result = await canonical_tool.execute(
            command=command,
            timeout=timeout,
            working_dir=cwd,
            environment=env,
            run_in_background=True,
            session_id=session_id,
            task_id=task_id,
            tool_call_id=tool_call_id,
            description=description,
        )
        if not result.get("success"):
            return {
                "success": False,
                "error": result.get("error") or "Failed to start background process",
                "error_code": "BACKGROUND_START_ERROR",
                "command": command[:100],
            }

        payload = result.get("result", {})
        return {
            "success": True,
            "background_task_id": payload.get("background_task_id"),
            "process_id": payload.get("process_id"),
            "pid": payload.get("pid"),
            "command": command,
            "cwd": cwd,
            "background": True,
            "semantic_type": semantic_type.value,
            "security_level": security_level.value,
            "message": payload.get("message") or f"Command started in background with PID {payload.get('pid')}",
            "timeout": timeout,
        }

    def _analyze_command_semantics(self, command: str) -> CommandSemanticType:
        """Analyze command to determine semantic type.

        This is a basic implementation. For production, use more sophisticated
        parsing (e.g., bashlex) to analyze AST.
        """
        command_lower = command.lower()

        # Check for dangerous operations
        dangerous_keywords = ['rm -rf', 'dd if=', 'mkfs', 'format', 'shutdown', 'reboot']
        if any(kw in command_lower for kw in dangerous_keywords):
            return CommandSemanticType.DANGEROUS

        # Check for network operations
        network_keywords = ['curl', 'wget', 'nc', 'netcat', 'ssh', 'scp', 'rsync']
        if any(kw in command_lower for kw in network_keywords):
            return CommandSemanticType.NETWORK

        # Check for git operations
        if command_lower.startswith('git '):
            return CommandSemanticType.GIT

        # Check for write operations
        write_keywords = ['>', '>>', 'tee', 'mv', 'cp', 'mkdir', 'touch']
        if any(kw in command_lower for kw in write_keywords):
            return CommandSemanticType.WRITE

        # Check for search operations
        search_keywords = ['grep', 'find', 'locate', 'ag', 'rg']
        if any(kw in command_lower for kw in search_keywords):
            return CommandSemanticType.SEARCH

        # Check for read operations
        read_keywords = ['cat', 'less', 'more', 'head', 'tail', 'ls', 'stat']
        if any(kw in command_lower for kw in read_keywords):
            return CommandSemanticType.READ

        # Check for execute operations
        execute_keywords = ['python', 'node', 'npm', 'cargo', 'go run', 'java']
        if any(kw in command_lower for kw in execute_keywords):
            return CommandSemanticType.EXECUTE

        # Default to system
        return CommandSemanticType.SYSTEM

    def _classify_security_level(
        self,
        command: str,
        security_decision: Any
    ) -> BashSecurityLevel:
        """Classify command security level based on validators."""
        # If validators blocked it, it's critical
        if security_decision.behavior == PermissionBehavior.DENY:
            return BashSecurityLevel.CRITICAL

        # Approval-required commands are not all equally risky.
        if security_decision.behavior == PermissionBehavior.ASK:
            if self._has_high_risk_security_signal(
                command=command,
                security_issues=get_command_security_issues(command),
                security_message=getattr(security_decision, "message", None),
                security_reason=getattr(security_decision, "reason", None),
            ):
                return BashSecurityLevel.DANGEROUS
            return BashSecurityLevel.MODERATE

        # Check if command is safe according to validators
        if is_command_safe(command):
            return BashSecurityLevel.SAFE

        # Get security issues
        issues = get_command_security_issues(command)

        # If no issues, it's safe
        if not issues:
            return BashSecurityLevel.SAFE

        # If has issues but not blocked, it's moderate
        return BashSecurityLevel.MODERATE

    @classmethod
    def _has_high_risk_security_signal(
        cls,
        *,
        command: str,
        security_issues: list[str],
        security_message: str | None,
        security_reason: str | None,
    ) -> bool:
        """Detect approval-required cases that should be treated as dangerous."""
        haystack = " ".join(
            filter(None, [command, security_message, security_reason, *security_issues])
        ).lower()
        high_risk_markers = (
            "eval",
            "command injection",
            "newline",
            "jq system",
            "cannot write to system path",
            "ifs",
            "binary hijack",
            "redirect binary execution",
        )
        if cls._is_literal_multiline_echo(command):
            high_risk_markers = tuple(
                marker
                for marker in high_risk_markers
                if marker not in {"command injection", "newline"}
            )
        return any(marker in haystack for marker in high_risk_markers)

    @staticmethod
    def _is_literal_multiline_echo(command: str) -> bool:
        """Allow quoted multiline echo literals without downgrading other safeguards."""
        stripped = command.strip()
        if "\n" not in stripped:
            return False
        return bool(re.fullmatch(r"echo\s+'(?:[^']|\n)*'", stripped))

    @classmethod
    def _should_block_ask_command(
        cls,
        *,
        command: str,
        semantic_type: CommandSemanticType,
        security_issues: list[str],
        security_message: str | None,
        security_reason: str | None,
    ) -> bool:
        """Convert high-risk ASK decisions into hard blocks for non-interactive runs."""
        if semantic_type == CommandSemanticType.DANGEROUS:
            return True
        return cls._has_high_risk_security_signal(
            command=command,
            security_issues=security_issues,
            security_message=security_message,
            security_reason=security_reason,
        )

    async def get_background_status(self, process_id: str) -> dict[str, Any]:
        """Get status of background process."""
        status = await self._get_canonical_tool().get_background_status(process_id)
        if not status.get("success"):
            status["error_code"] = "PROCESS_NOT_FOUND"
        if status.get("success"):
            status.setdefault("background_task_id", process_id)
            status.setdefault("process_id", process_id)
        return status

    async def kill_background_process(self, process_id: str) -> dict[str, Any]:
        """Kill a background process."""
        result = await self._get_canonical_tool().kill_background_process(process_id)
        if not result.get("success"):
            result["error_code"] = "PROCESS_NOT_FOUND"
        if result.get("success"):
            result.setdefault("background_task_id", process_id)
            result.setdefault("process_id", process_id)
            result.setdefault("message", "Process killed successfully")
        return result

    def _get_canonical_tool(self) -> ShellExecutorTool:
        """Return the configured canonical shell tool."""
        self._canonical_tool.root_dir = self.root_dir
        self._canonical_tool.sandbox_mode = self.sandbox_mode
        return self._canonical_tool

    @staticmethod
    def _normalize_canonical_execution(
        result: dict[str, Any],
        *,
        command: str,
        cwd: str,
        timeout: int | None,
        semantic_type: CommandSemanticType,
        security_level: BashSecurityLevel,
    ) -> dict[str, Any]:
        """Convert canonical shell results to the v2 response contract."""
        if not result.get("success"):
            return {
                "success": False,
                "error": result.get("error") or "Execution failed",
                "error_code": "EXECUTION_ERROR",
                "command": command[:100],
            }

        payload = result.get("result", {}) or {}
        if payload.get("timeout"):
            return {
                "success": False,
                "error": f"Command timed out after {timeout}s",
                "error_code": "TIMEOUT",
                "command": command[:100],
                "timeout": timeout,
            }

        stdout = payload.get("output", "")
        stderr = payload.get("stderr", "")
        exit_code = payload.get("return_code", -1)
        success = exit_code == 0
        response = {
            "success": success,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "command": command,
            "cwd": cwd,
            "execution_time": payload.get("execution_time", 0.0),
            "semantic_type": semantic_type.value,
            "security_level": security_level.value,
            "output_lines": stdout.count("\n") if stdout else 0,
        }

        combined_output = f"{stdout}\n{stderr}".lower()
        if exit_code == 127 and "not found" in combined_output:
            response["success"] = False
            response["error"] = stderr or stdout or "Command not found"
            response["error_code"] = "COMMAND_NOT_FOUND"
        elif not success:
            response["error"] = stderr or stdout or f"Command exited with code {exit_code}"

        return response

    def get_schema(self) -> dict[str, Any]:
        """Return tool schema for LangChain adapter."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute"
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Working directory for command execution",
                        "default": None
                    },
                    "env": {
                        "type": "object",
                        "description": "Environment variables (merged with current env)",
                        "default": None
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (null = no timeout)",
                        "default": 120
                    },
                    "capture_output": {
                        "type": "boolean",
                        "description": "Capture stdout/stderr",
                        "default": True
                    },
                    "run_in_background": {
                        "type": "boolean",
                        "description": "Run command in background",
                        "default": False
                    },
                    "sandbox_mode": {
                        "type": "string",
                        "description": "Sandbox mode for security validation",
                        "default": None
                    }
                },
                "required": ["command"]
            }
        }
