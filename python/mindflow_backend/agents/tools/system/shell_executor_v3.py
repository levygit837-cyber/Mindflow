"""ShellExecutorTool v3 - New Tool System Implementation.

Execute shell commands with security controls and resource limits.
"""

from __future__ import annotations

import os
import platform
import subprocess
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.schemas.tools import build_tool
from mindflow_backend.schemas.tools.context import ToolContext
from mindflow_backend.schemas.tools.permission import PermissionBehavior


# ---------------------------------------------------------------------------
# Input Schema
# ---------------------------------------------------------------------------


class ShellExecutorInput(BaseModel):
    """Input schema for ShellExecutorTool v3."""

    command: str = Field(
        description="Shell command to execute"
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Timeout in seconds (max 300s / 5min)"
    )
    working_dir: str | None = Field(
        default=None,
        description="Working directory for command execution (defaults to root_dir)"
    )
    capture_output: bool = Field(
        default=True,
        description="Capture stdout and stderr"
    )
    shell: bool = Field(
        default=True,
        description="Execute command through shell"
    )
    check_return_code: bool = Field(
        default=False,
        description="Mark as failed if return code is non-zero"
    )


# ---------------------------------------------------------------------------
# Execute Function
# ---------------------------------------------------------------------------


async def shell_execute(input: ShellExecutorInput, context: ToolContext) -> dict[str, Any]:
    """Execute shell command with security controls and resource limits.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context (permissions, abort signal, etc.)

    Returns:
        Dictionary with command output and execution metadata or error
    """
    # 1. Security validation: dangerous commands
    dangerous_patterns = [
        "rm -rf /",
        "mkfs",
        "dd if=",
        "> /dev/",
        ":(){ :|:& };:",  # Fork bomb
        "chmod -R 777",
        "chown -R",
    ]

    command_lower = input.command.lower()
    for pattern in dangerous_patterns:
        if pattern.lower() in command_lower:
            return {
                "success": False,
                "error": f"Dangerous command pattern detected: {pattern}",
                "error_code": "DANGEROUS_COMMAND",
                "command": input.command[:100]
            }

    # 2. Check permissions (if manager available)
    if context.permission_manager:
        perm_result = await context.check_permission_async(
            tool_name="shell_execute",
            input=input.dict(),
            tool_content=input.command
        )

        if perm_result.behavior == PermissionBehavior.DENY:
            return {
                "success": False,
                "error": perm_result.reason or "Permission denied",
                "error_code": "PERMISSION_DENIED",
                "command": input.command[:100]
            }

    # 3. Resolve working directory
    working_dir = input.working_dir
    root_dir = context.metadata.get("root_dir")

    if working_dir:
        if root_dir and not os.path.isabs(working_dir):
            working_dir = os.path.join(root_dir, working_dir)
        working_dir = os.path.abspath(working_dir)
    elif root_dir:
        working_dir = root_dir
    else:
        working_dir = os.getcwd()

    # Check working directory exists
    if not os.path.exists(working_dir):
        return {
            "success": False,
            "error": f"Working directory not found: {working_dir}",
            "error_code": "DIRECTORY_NOT_FOUND"
        }

    # 4. Prepare environment
    env = os.environ.copy()

    # 5. Execute command
    start_time = time.time()
    timed_out = False

    try:
        process = subprocess.Popen(
            input.command,
            shell=input.shell,
            stdout=subprocess.PIPE if input.capture_output else None,
            stderr=subprocess.PIPE if input.capture_output else None,
            cwd=working_dir,
            env=env,
            text=True,
        )

        try:
            stdout, stderr = process.communicate(timeout=input.timeout)
            return_code = process.returncode
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            return_code = -1
            timed_out = True

        execution_time = time.time() - start_time

        # 6. Check return code if requested
        success = True
        if input.check_return_code and return_code != 0:
            success = False

        # 7. Truncate output if too large (100KB limit)
        max_output = 100_000
        if stdout and len(stdout) > max_output:
            stdout = stdout[:max_output] + "\n...[output truncated]"

        if stderr and len(stderr) > max_output:
            stderr = stderr[:max_output] + "\n...[output truncated]"

        return {
            "success": success,
            "output": stdout or "",
            "stderr": stderr or "",
            "return_code": return_code,
            "pid": process.pid,
            "working_dir": working_dir,
            "execution_time": round(execution_time, 3),
            "timed_out": timed_out,
            "command": input.command[:200]  # Truncate command in response
        }

    except PermissionError as e:
        return {
            "success": False,
            "error": f"Permission denied: {e}",
            "error_code": "OS_PERMISSION_ERROR",
            "command": input.command[:100]
        }
    except FileNotFoundError as e:
        return {
            "success": False,
            "error": f"Command not found: {e}",
            "error_code": "COMMAND_NOT_FOUND",
            "command": input.command[:100]
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Shell execution failed: {e}",
            "error_code": "EXECUTION_ERROR",
            "command": input.command[:100]
        }


# ---------------------------------------------------------------------------
# Build Tool
# ---------------------------------------------------------------------------


ShellExecutorToolV3 = build_tool(
    name="shell_execute",
    description=(
        "Execute shell commands with security controls, timeout limits, and output capture. "
        "Blocks dangerous commands (rm -rf /, fork bombs, etc.), enforces timeouts, "
        "and captures stdout/stderr. Returns execution metadata including return code and timing."
    ),
    input_schema=ShellExecutorInput,
    execute=shell_execute,
    is_read_only=False,
    is_destructive=True,  # Shell commands are destructive
    is_concurrency_safe=False,  # Shell execution is not concurrency-safe
)
