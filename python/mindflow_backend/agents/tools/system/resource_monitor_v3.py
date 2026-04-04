"""ResourceMonitorTool v3 compatibility wrapper.

Delegates execution to the canonical unsuffixed resource monitor while
preserving the V3 input schema, state shape, and flattened response contract.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.agents.tools.filesystem._legacy_adapter import (
    flatten_legacy_result,
    get_context_root_dir,
)
from mindflow_backend.agents.tools.system.resource_monitor import ResourceMonitorTool
from mindflow_backend.schemas.tools import build_tool
from mindflow_backend.schemas.tools.context import ToolContext


class ResourceMonitorInput(BaseModel):
    """Input schema for ResourceMonitorTool v3."""

    action: str = Field(
        description="Action to perform: 'get_current', 'get_history', 'start', 'stop'",
    )
    resources: list[str] = Field(
        default=["cpu", "memory"],
        description="Resources to monitor: 'cpu', 'memory', 'disk', 'network'",
    )
    duration: int = Field(
        default=60,
        ge=1,
        le=3600,
        description="Monitoring duration in seconds (for 'start' action)",
    )
    interval: int = Field(
        default=5,
        ge=1,
        le=60,
        description="Monitoring interval in seconds (for 'start' action)",
    )
    alert_conditions: dict[str, float] = Field(
        default={},
        description="Alert thresholds (e.g., {'cpu': 80.0, 'memory': 85.0})",
    )


_legacy_resource_monitor = ResourceMonitorTool()
_monitoring_state = {
    "active": False,
    "task": None,
    "history": {
        "cpu": [],
        "memory": [],
        "disk": [],
        "network": [],
    },
    "alerts": [],
    "thresholds": {
        "cpu": 80.0,
        "memory": 85.0,
        "disk": 90.0,
        "network": 1000000,
    },
    "history_size": 100,
}


def _configure_resource_monitor(context: ToolContext) -> ResourceMonitorTool:
    """Hydrate the canonical monitor from the V3 compatibility state."""
    tool = _legacy_resource_monitor
    root_dir = get_context_root_dir(context)
    if root_dir:
        tool.root_dir = root_dir
    tool.sandbox_mode = context.sandbox_mode
    tool._monitoring = _monitoring_state["active"]
    tool._monitoring_task = _monitoring_state["task"]
    tool._history = _monitoring_state["history"]
    tool._alerts = _monitoring_state["alerts"]
    tool.alert_thresholds = _monitoring_state["thresholds"]
    tool.history_size = _monitoring_state["history_size"]
    return tool


def _sync_monitoring_state(tool: ResourceMonitorTool) -> None:
    """Persist canonical monitor state back into the V3 compatibility store."""
    _monitoring_state["active"] = tool._monitoring
    _monitoring_state["task"] = tool._monitoring_task
    _monitoring_state["history"] = tool._history
    _monitoring_state["alerts"] = tool._alerts
    _monitoring_state["thresholds"] = tool.alert_thresholds
    _monitoring_state["history_size"] = tool.history_size


async def resource_monitor_execute(input: ResourceMonitorInput, context: ToolContext) -> dict[str, Any]:
    """Execute resource monitoring through the canonical V1 implementation."""
    tool = _configure_resource_monitor(context)
    result = await tool.execute(
        action=input.action,
        resources=input.resources,
        duration=input.duration,
        interval=input.interval,
        alert_conditions=input.alert_conditions,
    )
    _sync_monitoring_state(tool)
    flattened = flatten_legacy_result(
        result,
        error_map={
            "monitoring not started": "NOT_MONITORING",
            "unknown action": "UNKNOWN_ACTION",
            "psutil library not available": "MISSING_DEPENDENCY",
        },
        default_error_code="MONITORING_ERROR",
    )
    flattened.setdefault("action", input.action)
    return flattened


ResourceMonitorToolV3 = build_tool(
    name="resource_monitor",
    description=(
        "Monitor system resources (CPU, memory, disk, network) with alerting. "
        "Supports real-time monitoring with configurable intervals, historical data tracking, "
        "and threshold-based alerts. Can start/stop monitoring sessions or get current/historical data."
    ),
    input_schema=ResourceMonitorInput,
    execute=resource_monitor_execute,
    is_read_only=True,
    is_concurrency_safe=False,
    is_destructive=False,
)
