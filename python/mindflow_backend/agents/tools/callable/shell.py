"""System/Shell tools - Callable pattern (Phase 2).

All tools in this module use:
- Pydantic input schemas for type safety
- CallableToolResult return type
- ToolContext for runtime state (root_dir, sandbox_mode, permissions)
- Appropriate factories (build_callable_tool, build_destructive_tool)
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
from mindflow_backend.agents.tools.system.process_manager import ProcessManagerTool
from mindflow_backend.agents.tools.system.shell_executor import ShellExecutorTool
from mindflow_backend.agents.tools.system.system_info import SystemInfoTool
from mindflow_backend.schemas.tools import (
    CallableToolResult,
    ProgressCallback,
    build_callable_tool,
    build_readonly_tool,
)
from mindflow_backend.schemas.tools.context import ToolContext


def _callable_result_from_flattened(
    flattened: dict[str, Any],
    *,
    metadata: dict[str, Any] | None = None,
) -> CallableToolResult[dict[str, Any]]:
    """Convert a flattened legacy result to a callable tool result."""
    if flattened.get("success"):
        data = dict(flattened)
        data.pop("success", None)
        return CallableToolResult(data=data, success=True, metadata=metadata or {})

    result_metadata = dict(metadata or {})
    error_code = flattened.get("error_code")
    if error_code:
        result_metadata.setdefault("error_code", error_code)
    return CallableToolResult(
        data=None,
        success=False,
        error=flattened.get("error") or "Unknown error",
        metadata=result_metadata,
    )


# ---------------------------------------------------------------------------
# ShellExecutorCallable - Priority 3
# ---------------------------------------------------------------------------


class ShellExecutorInput(BaseModel):
    """Input schema for ShellExecutorCallable."""

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


async def shell_executor_impl(
    input: ShellExecutorInput,
    context: ToolContext,
    on_progress: ProgressCallback | None = None,
) -> CallableToolResult[dict[str, Any]]:
    """Execute shell commands through the canonical system shell tool."""
    if (
        context.sandbox_mode
        and hasattr(context.sandbox_mode, "value")
        and context.sandbox_mode.value == "READ_ONLY"
    ):
        return CallableToolResult(
            data=None,
            success=False,
            error="Shell execution blocked in read-only mode",
            metadata={
                "error_code": "READ_ONLY_MODE",
                "command": input.command[:100],
            }
        )

    dangerous_error = get_legacy_dangerous_command_error(input.command)
    if dangerous_error:
        return CallableToolResult(
            data=None,
            success=False,
            error=dangerous_error["error"],
            metadata={
                "error_code": dangerous_error["error_code"],
                "command": dangerous_error["command"],
            },
        )

    permission_error = await deny_if_permission_blocked(
        context,
        tool_name="shell_execute",
        input_data=input.model_dump(),
        tool_content=input.command,
        content_key="command",
    )
    if permission_error:
        return _callable_result_from_flattened(permission_error)

    root_dir = context.root_dir or context.metadata.get("root_dir")
    _, working_dir_error = resolve_explicit_shell_working_dir(
        input.working_dir,
        root_dir=root_dir,
    )
    if working_dir_error:
        return CallableToolResult(
            data=None,
            success=False,
            error=working_dir_error["error"],
            metadata={
                "error_code": working_dir_error["error_code"],
                "working_dir": working_dir_error["working_dir"],
            },
        )

    tool = build_legacy_tool(ShellExecutorTool, context)
    result = await tool.execute(
        command=input.command,
        timeout=input.timeout,
        working_dir=input.working_dir,
        capture_output=input.capture_output,
        shell=input.shell,
        check_return_code=input.check_return_code,
    )
    flattened = flatten_legacy_result(
        result,
        error_map=LEGACY_SHELL_ERROR_MAP,
        default_error_code="EXECUTION_ERROR",
    )
    if flattened.get("success"):
        flattened = normalize_legacy_shell_result(
            flattened,
            command=input.command,
            check_return_code=input.check_return_code,
        )
    return _callable_result_from_flattened(
        flattened,
        metadata={"operation": "shell_execute"},
    )


ShellExecutorCallable = build_callable_tool(
    name="shell_execute",
    description=(
        "Execute shell commands with security controls, timeout limits, and output capture. "
        "Blocks dangerous commands (rm -rf /, fork bombs, etc.), enforces timeouts, "
        "and captures stdout/stderr. Returns execution metadata including return code and timing. "
        "NOT concurrent-safe: shell commands can have shared state conflicts. "
        "DESTRUCTIVE: shell commands can modify the system."
    ),
    input_schema=ShellExecutorInput,
    call_fn=shell_executor_impl,
    is_read_only=False,  # Shell commands can write
    is_destructive=True,  # Shell commands are destructive
    is_concurrency_safe=False,  # Shell execution is not concurrency-safe
    interrupt_behavior="block",  # Don't interrupt running shell commands
)


# ---------------------------------------------------------------------------
# SystemInfoCallable - Priority 3
# ---------------------------------------------------------------------------


class SystemInfoInput(BaseModel):
    """Input schema for SystemInfoCallable."""

    info_type: str = Field(
        default="all",
        description="Type of information to collect: 'all', 'hardware', 'software', 'network', 'environment'"
    )
    include_sensitive: bool = Field(
        default=False,
        description="Include sensitive environment variables (masked)"
    )


async def system_info_impl(
    input: SystemInfoInput,
    context: ToolContext,
    on_progress: ProgressCallback | None = None,
) -> CallableToolResult[dict[str, Any]]:
    """Collect system information through the canonical system tool."""
    tool = build_legacy_tool(SystemInfoTool, context)
    result = await tool.execute(
        info_type=input.info_type,
        include_sensitive=input.include_sensitive,
    )
    flattened = flatten_legacy_result(
        result,
        error_map={
            "system information collection error": "COLLECTION_ERROR",
        },
        default_error_code="COLLECTION_ERROR",
    )
    if flattened.get("success"):
        flattened.setdefault("info_type", input.info_type)
    return _callable_result_from_flattened(
        flattened,
        metadata={"operation": "system_info"},
    )


SystemInfoCallable = build_readonly_tool(
    name="system_info",
    description=(
        "Collect comprehensive system information including hardware (CPU, memory, disk), "
        "software (Python, OS), network (interfaces, connections), and environment variables. "
        "Supports filtering by info type and optional sensitive data masking. "
        "Concurrent-safe: can collect system info in parallel."
    ),
    input_schema=SystemInfoInput,
    call_fn=system_info_impl,
    is_concurrency_safe=True,  # Safe to collect system info in parallel
    interrupt_behavior="cancel",  # Safe to interrupt system info collection
)


# ---------------------------------------------------------------------------
# ProcessManagerCallable - Priority 3
# ---------------------------------------------------------------------------


class ProcessManagerInput(BaseModel):
    """Input schema for ProcessManagerCallable."""

    action: str = Field(
        description="Action to perform: 'list', 'kill', 'monitor'"
    )
    pid: int | None = Field(
        default=None,
        description="Process ID (required for 'kill' and 'monitor' actions)"
    )
    signal_name: str = Field(
        default="SIGTERM",
        description="Signal to send when killing process (e.g., 'SIGTERM', 'SIGKILL')"
    )
    filter_name: str | None = Field(
        default=None,
        description="Filter processes by name (for 'list' action)"
    )
    filter_user: str | None = Field(
        default=None,
        description="Filter processes by user (for 'list' action)"
    )


async def process_manager_impl(
    input: ProcessManagerInput,
    context: ToolContext,
    on_progress: ProgressCallback | None = None,
) -> CallableToolResult[dict[str, Any]]:
    """Execute process management through the canonical system tool."""
    if (
        context.sandbox_mode
        and hasattr(context.sandbox_mode, "value")
        and context.sandbox_mode.value == "READ_ONLY"
        and input.action.lower() == "kill"
    ):
        return CallableToolResult(
            data=None,
            success=False,
            error="Process kill blocked in read-only mode",
            metadata={
                "error_code": "READ_ONLY_MODE",
                "action": input.action,
            },
        )

    tool = build_legacy_tool(ProcessManagerTool, context)
    result = await tool.execute(
        action=input.action,
        pid=input.pid,
        signal=input.signal_name,
        filter_name=input.filter_name,
        filter_user=input.filter_user,
    )
    flattened = flatten_legacy_result(
        result,
        error_map={
            "not authorized": "UNAUTHORIZED_USER",
            "psutil library not available": "MISSING_DEPENDENCY",
            "pid is required": "INVALID_INPUT",
            "unknown action": "UNKNOWN_ACTION",
            "unknown signal": "INVALID_INPUT",
            "process not found": "PROCESS_NOT_FOUND",
            "access denied": "PERMISSION_DENIED",
            "cannot kill critical system process": "PERMISSION_DENIED",
        },
        default_error_code="OPERATION_ERROR",
    )
    if flattened.get("success"):
        flattened.setdefault("action", input.action.lower())
    return _callable_result_from_flattened(
        flattened,
        metadata={"operation": "process_manager"},
    )


ProcessManagerCallable = build_callable_tool(
    name="process_manager",
    description=(
        "Manage system processes with security controls. "
        "List processes with filtering, kill processes by PID with signal control, "
        "and monitor process resource usage. Blocks critical system processes and "
        "requires user authorization. NOT concurrent-safe: process operations can conflict."
    ),
    input_schema=ProcessManagerInput,
    call_fn=process_manager_impl,
    is_read_only=False,  # Can kill processes
    is_destructive=True,  # Killing processes is destructive
    is_concurrency_safe=False,  # Process operations are not concurrency-safe
    interrupt_behavior="block",  # Don't interrupt process operations
)
