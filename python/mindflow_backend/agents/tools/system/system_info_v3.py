"""SystemInfoTool v3 - New Tool System Implementation.

Collect comprehensive system information including hardware, software, network, and environment.
"""

from __future__ import annotations

import os
import platform
import socket
import time
from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.schemas.tools import build_tool
from mindflow_backend.schemas.tools.context import ToolContext


# ---------------------------------------------------------------------------
# Input Schema
# ---------------------------------------------------------------------------


class SystemInfoInput(BaseModel):
    """Input schema for SystemInfoTool v3."""

    info_type: str = Field(
        default="all",
        description="Type of information to collect: 'all', 'hardware', 'software', 'network', 'environment'"
    )
    include_sensitive: bool = Field(
        default=False,
        description="Include sensitive environment variables (masked)"
    )


# ---------------------------------------------------------------------------
# Execute Function
# ---------------------------------------------------------------------------


async def system_info_execute(input: SystemInfoInput, context: ToolContext) -> dict[str, Any]:
    """Collect system information.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context

    Returns:
        Dictionary with system information or error
    """
    try:
        result = {"timestamp": time.time()}

        if input.info_type in ["all", "hardware"]:
            result["hardware"] = await _get_hardware_info()

        if input.info_type in ["all", "software"]:
            result["software"] = await _get_software_info()

        if input.info_type in ["all", "network"]:
            result["network"] = await _get_network_info()

        if input.info_type in ["all", "environment"]:
            result["environment"] = await _get_environment_info(input.include_sensitive)

        return {
            "success": True,
            "info_type": input.info_type,
            **result
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"System information collection error: {e}",
            "error_code": "COLLECTION_ERROR",
            "info_type": input.info_type
        }


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


async def _get_hardware_info() -> dict[str, Any]:
    """Get hardware information."""
    hardware_info = {}

    # Basic system info
    hardware_info["system"] = {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "hostname": socket.gethostname()
    }

    # CPU information
    try:
        import psutil
        cpu_info = {
            "count": psutil.cpu_count(logical=True),
            "physical_count": psutil.cpu_count(logical=False),
            "frequency": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {},
            "usage_percent": psutil.cpu_percent(interval=1)
        }

        # CPU architecture details
        if hasattr(psutil, 'cpu_percent'):
            cpu_info["usage_per_cpu"] = psutil.cpu_percent(percpu=True)

        hardware_info["cpu"] = cpu_info
    except ImportError:
        hardware_info["cpu"] = {"error": "psutil not available"}

    # Memory information
    try:
        import psutil
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()

        hardware_info["memory"] = {
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
    except ImportError:
        hardware_info["memory"] = {"error": "psutil not available"}

    # Disk information
    try:
        import psutil
        disk_info = {}

        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_info[partition.mountpoint] = {
                    "device": partition.device,
                    "fstype": partition.fstype,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percentage": (usage.used / usage.total) * 100
                }
            except PermissionError:
                continue

        hardware_info["disk"] = disk_info
    except ImportError:
        hardware_info["disk"] = {"error": "psutil not available"}

    return hardware_info


async def _get_software_info() -> dict[str, Any]:
    """Get software information."""
    software_info = {}

    # Python information
    software_info["python"] = {
        "version": platform.python_version(),
        "implementation": platform.python_implementation(),
        "compiler": platform.python_compiler(),
        "build": platform.python_build()
    }

    # OS information
    software_info["os"] = {
        "name": platform.system(),
        "version": platform.release(),
        "codename": platform.version(),
        "machine": platform.machine()
    }

    # Environment variables (filtered)
    software_info["environment"] = {}
    important_vars = [
        "PATH", "HOME", "USER", "SHELL", "LANG", "LC_ALL",
        "PYTHONPATH", "VIRTUAL_ENV", "CONDA_DEFAULT_ENV"
    ]

    for var in important_vars:
        value = os.environ.get(var)
        if value:
            software_info["environment"][var] = value

    return software_info


async def _get_network_info() -> dict[str, Any]:
    """Get network information."""
    network_info = {}

    try:
        import psutil

        # Network interfaces
        interfaces = {}

        for interface, addrs in psutil.net_if_addrs().items():
            interfaces[interface] = {
                "addresses": []
            }

            for addr in addrs:
                addr_info = {
                    "family": str(addr.family),
                    "address": addr.address
                }

                if hasattr(addr, 'netmask'):
                    addr_info["netmask"] = addr.netmask

                if hasattr(addr, 'broadcast'):
                    addr_info["broadcast"] = addr.broadcast

                interfaces[interface]["addresses"].append(addr_info)

        network_info["interfaces"] = interfaces

        # Network I/O stats
        io_stats = psutil.net_io_counters()
        network_info["io_stats"] = {
            "bytes_sent": io_stats.bytes_sent,
            "bytes_recv": io_stats.bytes_recv,
            "packets_sent": io_stats.packets_sent,
            "packets_recv": io_stats.packets_recv,
            "errin": io_stats.errin,
            "errout": io_stats.errout,
            "dropin": io_stats.dropin,
            "dropout": io_stats.dropout
        }

        # Network connections (limited to avoid too much data)
        connections = []
        for conn in psutil.net_connections()[:50]:  # Limit to 50 connections
            conn_info = {
                "local_address": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                "remote_address": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                "status": conn.status,
                "type": str(conn.type)
            }
            connections.append(conn_info)

        network_info["connections"] = connections
        network_info["connections_count"] = len(connections)

    except ImportError:
        network_info["error"] = "psutil not available"
    except Exception as e:
        network_info["error"] = f"Network info collection failed: {e}"

    return network_info


async def _get_environment_info(include_sensitive: bool) -> dict[str, Any]:
    """Get environment information."""
    env_info = {}

    # System environment
    env_info["user"] = {
        "name": os.getenv("USER", "unknown"),
        "home": os.getenv("HOME", "unknown"),
        "shell": os.getenv("SHELL", "unknown")
    }

    # Current working directory
    env_info["working_directory"] = os.getcwd()

    # Environment variables (filtered)
    env_info["variables"] = {}

    # Safe variables to include
    safe_patterns = [
        "PATH", "HOME", "USER", "SHELL", "LANG", "LC_ALL",
        "PYTHONPATH", "VIRTUAL_ENV", "CONDA_DEFAULT_ENV",
        "TERM", "EDITOR", "BROWSER", "DISPLAY"
    ]

    for pattern in safe_patterns:
        value = os.environ.get(pattern)
        if value:
            env_info["variables"][pattern] = value

    # Include sensitive variables if requested (masked)
    if include_sensitive:
        sensitive_patterns = [
            "PASSWORD", "TOKEN", "KEY", "SECRET", "CREDENTIAL",
            "API_KEY", "AUTH", "PRIVATE"
        ]

        for pattern in sensitive_patterns:
            for var_name in os.environ:
                if pattern in var_name.upper():
                    env_info["variables"][var_name] = "***HIDDEN***"

    return env_info


# ---------------------------------------------------------------------------
# Build Tool
# ---------------------------------------------------------------------------


SystemInfoToolV3 = build_tool(
    name="system_info",
    description=(
        "Collect comprehensive system information including hardware (CPU, memory, disk), "
        "software (Python, OS), network (interfaces, connections), and environment variables. "
        "Supports filtering by info type and optional sensitive data masking."
    ),
    input_schema=SystemInfoInput,
    execute=system_info_execute,
    is_read_only=True,
    is_concurrency_safe=True,
    is_destructive=False,
)
