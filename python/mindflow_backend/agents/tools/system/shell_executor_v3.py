"""ShellExecutorTool v3 compatibility wrapper.

Delegates execution to the canonical unsuffixed shell tool while
preserving the v3 contract.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.agents.tools.filesystem._legacy_adapter import (
    build_legacy_tool,
    deny_if_permission_blocked,
    flatten_legacy_result,
)
from mindflow_backend.agents.tools.system._shell_compat import (
    LEGACY_SHELL_ERROR_MAP,
    get_legacy_dangerous_command_error,
    normalize_legacy_shell_result,
    resolve_explicit_shell_working_dir,
)
from mindflow_backend.agents.tools.system.shell_executor import ShellExecutorTool
from mindflow_backend.schemas.tools import build_tool
from mindflow_backend.schemas.tools.context import ToolContext

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
    dangerous_error = get_legacy_dangerous_command_error(input.command)
    if dangerous_error:
        return dangerous_error

    permission_error = await deny_if_permission_blocked(
        context,
        tool_name="shell_execute",
        input_data=input.model_dump(),
        tool_content=input.command,
        content_key="command",
    )
    if permission_error:
        return permission_error

    root_dir = context.root_dir or context.metadata.get("root_dir")
    _, working_dir_error = resolve_explicit_shell_working_dir(
        input.working_dir,
        root_dir=root_dir,
    )
    if working_dir_error:
        return {
            "success": False,
            "error": working_dir_error["error"],
            "error_code": working_dir_error["error_code"],
        }

    tool = build_legacy_tool(ShellExecutorTool, context)
    result = await tool.execute(
        command=input.command,
        timeout=input.timeout,
        working_dir=input.working_dir,
        capture_output=input.capture_output,
        shell=input.shell,
        check_return_code=input.check_return_code,
    )
    payload = result.get("result") if isinstance(result.get("result"), dict) else None
    if payload is not None:
        normalized = normalize_legacy_shell_result(
            {"success": result.get("success", False), **payload},
            command=input.command,
            check_return_code=input.check_return_code,
        )
        return normalized

    flattened = flatten_legacy_result(
        result,
        error_map=LEGACY_SHELL_ERROR_MAP,
        default_error_code="EXECUTION_ERROR",
    )
    if not flattened.get("success"):
        return flattened

    return normalize_legacy_shell_result(
        flattened,
        command=input.command,
        check_return_code=input.check_return_code,
    )


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
