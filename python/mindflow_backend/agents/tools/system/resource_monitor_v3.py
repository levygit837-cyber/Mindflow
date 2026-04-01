"""ResourceMonitorTool v3 - New Tool System Implementation.

Monitor system resources (CPU, memory, disk, network) with alerting capabilities.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools import build_tool
from mindflow_backend.schemas.tools.context import ToolContext

_logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Input Schema
# ---------------------------------------------------------------------------


class ResourceMonitorInput(BaseModel):
    """Input schema for ResourceMonitorTool v3."""

    action: str = Field(
        description="Action to perform: 'get_current', 'get_history', 'start', 'stop'"
    )
    resources: list[str] = Field(
        default=["cpu", "memory"],
        description="Resources to monitor: 'cpu', 'memory', 'disk', 'network'"
    )
    duration: int = Field(
        default=60,
        ge=1,
        le=3600,
        description="Monitoring duration in seconds (for 'start' action)"
    )
    interval: int = Field(
        default=5,
        ge=1,
        le=60,
        description="Monitoring interval in seconds (for 'start' action)"
    )
    alert_conditions: dict[str, float] = Field(
        default={},
        description="Alert thresholds (e.g., {'cpu': 80.0, 'memory': 85.0})"
    )


# ---------------------------------------------------------------------------
# Global State (for monitoring)
# ---------------------------------------------------------------------------

# Note: In a production system, this should be stored in a proper state manager
# or database. For now, we use module-level state.
_monitoring_state = {
    "active": False,
    "task": None,
    "history": {
        "cpu": [],
        "memory": [],
        "disk": [],
        "network": []
    },
    "alerts": [],
    "thresholds": {
        "cpu": 80.0,
        "memory": 85.0,
        "disk": 90.0,
        "network": 1000000
    },
    "history_size": 100
}


# ---------------------------------------------------------------------------
# Execute Function
# ---------------------------------------------------------------------------


async def resource_monitor_execute(input: ResourceMonitorInput, context: ToolContext) -> dict[str, Any]:
    """Execute resource monitoring operation.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context

    Returns:
        Dictionary with monitoring result or error
    """
    try:
        action = input.action.lower()

        if action == "start":
            return await _start_monitoring(input)
        elif action == "stop":
            return await _stop_monitoring()
        elif action == "get_current":
            return await _get_current_resources(input)
        elif action == "get_history":
            return await _get_history(input)
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}",
                "error_code": "UNKNOWN_ACTION",
                "action": action
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"Resource monitoring error: {e}",
            "error_code": "MONITORING_ERROR",
            "action": input.action
        }


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


async def _start_monitoring(input: ResourceMonitorInput) -> dict[str, Any]:
    """Start resource monitoring."""
    if _monitoring_state["active"]:
        return {
            "success": False,
            "error": "Monitoring already started",
            "error_code": "ALREADY_MONITORING",
            "action": "start"
        }

    # Update alert thresholds
    _monitoring_state["thresholds"].update(input.alert_conditions)

    # Start monitoring task
    _monitoring_state["active"] = True
    _monitoring_state["task"] = asyncio.create_task(
        _monitor_loop(input.resources, input.duration, input.interval)
    )

    return {
        "success": True,
        "action": "start",
        "monitoring": True,
        "resources": input.resources,
        "duration": input.duration,
        "interval": input.interval,
        "start_time": time.time()
    }


async def _stop_monitoring() -> dict[str, Any]:
    """Stop resource monitoring."""
    if not _monitoring_state["active"]:
        return {
            "success": False,
            "error": "Monitoring not started",
            "error_code": "NOT_MONITORING",
            "action": "stop"
        }

    _monitoring_state["active"] = False

    if _monitoring_state["task"]:
        _monitoring_state["task"].cancel()
        try:
            await _monitoring_state["task"]
        except asyncio.CancelledError:
            pass

    return {
        "success": True,
        "action": "stop",
        "monitoring": False,
        "stop_time": time.time(),
        "final_history": _monitoring_state["history"]
    }


async def _get_current_resources(input: ResourceMonitorInput) -> dict[str, Any]:
    """Get current resource usage."""
    try:
        import psutil

        current_data = {}

        if "cpu" in input.resources:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()

            current_data["cpu"] = {
                "percentage": cpu_percent,
                "count": cpu_count,
                "frequency": {
                    "current": cpu_freq.current if cpu_freq else None,
                    "min": cpu_freq.min if cpu_freq else None,
                    "max": cpu_freq.max if cpu_freq else None
                },
                "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            }

        if "memory" in input.resources:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()

            current_data["memory"] = {
                "virtual": {
                    "total": memory.total,
                    "available": memory.available,
                    "used": memory.used,
                    "percentage": memory.percent
                },
                "swap": {
                    "total": swap.total,
                    "used": swap.used,
                    "free": swap.free,
                    "percentage": swap.percent
                }
            }

        if "disk" in input.resources:
            disk_usage = {}
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_usage[partition.mountpoint] = {
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percentage": (usage.used / usage.total) * 100
                    }
                except PermissionError:
                    continue

            current_data["disk"] = disk_usage

        if "network" in input.resources:
            network = psutil.net_io_counters()
            current_data["network"] = {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv,
                "errin": network.errin,
                "errout": network.errout,
                "dropin": network.dropin,
                "dropout": network.dropout
            }

        return {
            "success": True,
            "action": "get_current",
            "current": current_data,
            "timestamp": time.time()
        }

    except ImportError:
        return {
            "success": False,
            "error": "psutil library not available. Install with: pip install psutil",
            "error_code": "MISSING_DEPENDENCY",
            "action": "get_current"
        }


async def _get_history(input: ResourceMonitorInput) -> dict[str, Any]:
    """Get historical resource data."""
    history_data = {}

    for resource in input.resources:
        if resource in _monitoring_state["history"]:
            history_data[resource] = _monitoring_state["history"][resource][-_monitoring_state["history_size"]:]

    return {
        "success": True,
        "action": "get_history",
        "history": history_data,
        "alerts": _monitoring_state["alerts"],
        "summary": _calculate_summary(history_data)
    }


async def _monitor_loop(resources: list[str], duration: int, interval: int):
    """Main monitoring loop."""
    start_time = time.time()

    while _monitoring_state["active"] and (time.time() - start_time) < duration:
        try:
            import psutil
            current_time = time.time()

            for resource in resources:
                if resource == "cpu":
                    cpu_percent = psutil.cpu_percent()
                    _add_to_history("cpu", cpu_percent, current_time)

                    # Check alert
                    if cpu_percent > _monitoring_state["thresholds"]["cpu"]:
                        await _trigger_alert("cpu", cpu_percent, current_time)

                elif resource == "memory":
                    memory = psutil.virtual_memory()
                    _add_to_history("memory", memory.percent, current_time)

                    # Check alert
                    if memory.percent > _monitoring_state["thresholds"]["memory"]:
                        await _trigger_alert("memory", memory.percent, current_time)

            await asyncio.sleep(interval)

        except Exception as e:
            _logger.error(f"Monitoring loop error: {e}")
            await asyncio.sleep(interval)


def _add_to_history(resource: str, value: float, timestamp: float):
    """Add data point to history."""
    _monitoring_state["history"][resource].append({
        "value": value,
        "timestamp": timestamp
    })

    # Keep only recent history
    if len(_monitoring_state["history"][resource]) > _monitoring_state["history_size"]:
        _monitoring_state["history"][resource] = _monitoring_state["history"][resource][-_monitoring_state["history_size"]:]


async def _trigger_alert(resource: str, value: float, timestamp: float):
    """Trigger an alert for resource threshold."""
    alert = {
        "resource": resource,
        "value": value,
        "threshold": _monitoring_state["thresholds"][resource],
        "timestamp": timestamp,
        "message": f"{resource.upper()} usage ({value}%) exceeds threshold ({_monitoring_state['thresholds'][resource]}%)"
    }

    _monitoring_state["alerts"].append(alert)
    _logger.warning(f"Resource alert: {alert['message']}")


def _calculate_summary(history_data: dict[str, list]) -> dict[str, Any]:
    """Calculate summary statistics from history."""
    summary = {}

    for resource, data in history_data.items():
        if not data:
            continue

        values = [point["value"] for point in data]
        summary[resource] = {
            "count": len(values),
            "average": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "latest": values[-1] if values else None
        }

    return summary


# ---------------------------------------------------------------------------
# Build Tool
# ---------------------------------------------------------------------------


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
    is_concurrency_safe=False,  # Uses global state
    is_destructive=False,
)
