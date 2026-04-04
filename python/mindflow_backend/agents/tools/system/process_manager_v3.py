"""ProcessManagerTool v3 compatibility wrapper.

Delegates execution to the canonical unsuffixed process manager while
preserving the V3 input schema and flattened response contract.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.agents.tools.filesystem._legacy_adapter import (
    build_legacy_tool,
    flatten_legacy_result,
)
from mindflow_backend.agents.tools.system.process_manager import ProcessManagerTool
from mindflow_backend.schemas.tools import build_tool
from mindflow_backend.schemas.tools.context import ToolContext


class ProcessManagerInput(BaseModel):
    """Input schema for ProcessManagerTool v3."""

    action: str = Field(
        description="Action to perform: 'list', 'kill', 'monitor'",
    )
    pid: int | None = Field(
        default=None,
        description="Process ID (required for 'kill' and 'monitor' actions)",
    )
    signal_name: str = Field(
        default="SIGTERM",
        description="Signal to send when killing process (e.g., 'SIGTERM', 'SIGKILL')",
    )
    filter_name: str | None = Field(
        default=None,
        description="Filter processes by name (for 'list' action)",
    )
    filter_user: str | None = Field(
        default=None,
        description="Filter processes by user (for 'list' action)",
    )


def _annotate_process_result(
    flattened: dict[str, Any],
    *,
    action: str,
    pid: int | None,
) -> dict[str, Any]:
    """Preserve the V3 response envelope over canonical process results."""
    flattened.setdefault("action", action)
    if pid is not None:
        flattened.setdefault("pid", pid)
    return flattened


async def process_manager_execute(input: ProcessManagerInput, context: ToolContext) -> dict[str, Any]:
    """Execute process management through the canonical V1 implementation."""
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
            "unknown action": "UNKNOWN_ACTION",
            "pid is required": "MISSING_PID",
            "unknown signal": "UNKNOWN_SIGNAL",
            "cannot kill critical system process": "CRITICAL_PROCESS_BLOCKED",
            "process not found": "PROCESS_NOT_FOUND",
            "access denied": "ACCESS_DENIED",
            "psutil library not available": "MISSING_DEPENDENCY",
        },
        default_error_code="OPERATION_ERROR",
    )
    return _annotate_process_result(
        flattened,
        action=input.action,
        pid=input.pid,
    )


ProcessManagerToolV3 = build_tool(
    name="process_manager",
    description=(
        "Manage system processes with security controls. "
        "List processes with filtering, kill processes by PID with signal control, "
        "and monitor process resource usage. Blocks critical system processes and "
        "requires user authorization."
    ),
    input_schema=ProcessManagerInput,
    execute=process_manager_execute,
    is_read_only=False,
    is_destructive=True,
    is_concurrency_safe=False,
)
