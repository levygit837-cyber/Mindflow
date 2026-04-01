"""ProcessManagerTool v3 - New Tool System Implementation.

Manage system processes with security controls including listing, termination, and monitoring.
"""

from __future__ import annotations

import os
import signal
import time
from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.schemas.tools import build_tool
from mindflow_backend.schemas.tools.context import ToolContext


# ---------------------------------------------------------------------------
# Input Schema
# ---------------------------------------------------------------------------


class ProcessManagerInput(BaseModel):
    """Input schema for ProcessManagerTool v3."""

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


# ---------------------------------------------------------------------------
# Execute Function
# ---------------------------------------------------------------------------


async def process_manager_execute(input: ProcessManagerInput, context: ToolContext) -> dict[str, Any]:
    """Execute process management operation.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context

    Returns:
        Dictionary with operation result or error
    """
    # Security settings
    RESTRICTED_COMMANDS = {
        'rm -rf /', 'dd if=', 'mkfs', 'fdisk', 'format',
        'shutdown', 'reboot', 'halt', 'poweroff'
    }
    ALLOWED_USERS = {'root', 'admin', 'mindflow', os.getenv('USER', 'unknown')}

    try:
        action = input.action.lower()

        # Security check - verify user is authorized
        current_user = os.getenv('USER', 'unknown')
        if current_user not in ALLOWED_USERS:
            return {
                "success": False,
                "error": f"User {current_user} not authorized for process management",
                "error_code": "UNAUTHORIZED_USER",
                "action": action
            }

        if action == "list":
            return await _list_processes(input)
        elif action == "kill":
            return await _kill_process(input)
        elif action == "monitor":
            return await _monitor_process(input)
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}",
                "error_code": "UNKNOWN_ACTION",
                "action": action
            }

    except PermissionError as e:
        return {
            "success": False,
            "error": f"Permission denied: {e}",
            "error_code": "PERMISSION_DENIED",
            "action": input.action
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Process management error: {e}",
            "error_code": "OPERATION_ERROR",
            "action": input.action
        }


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


async def _list_processes(input: ProcessManagerInput) -> dict[str, Any]:
    """List system processes with optional filtering."""
    try:
        import psutil

        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status']):
            try:
                proc_info = proc.info

                # Apply filters
                if input.filter_name and input.filter_name.lower() not in proc_info.get('name', '').lower():
                    continue

                if input.filter_user and input.filter_user != proc_info.get('username'):
                    continue

                processes.append({
                    'pid': proc_info.get('pid'),
                    'name': proc_info.get('name'),
                    'user': proc_info.get('username'),
                    'cpu_percent': proc_info.get('cpu_percent', 0),
                    'memory_percent': proc_info.get('memory_percent', 0),
                    'status': proc_info.get('status')
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return {
            "success": True,
            "action": "list",
            "processes": processes,
            "count": len(processes),
            "timestamp": time.time()
        }

    except ImportError:
        return {
            "success": False,
            "error": "psutil library not available. Install with: pip install psutil",
            "error_code": "MISSING_DEPENDENCY",
            "action": "list"
        }


async def _kill_process(input: ProcessManagerInput) -> dict[str, Any]:
    """Kill a process by PID."""
    if not input.pid:
        return {
            "success": False,
            "error": "PID is required for kill action",
            "error_code": "MISSING_PID",
            "action": "kill"
        }

    try:
        import psutil

        # Convert signal name to signal number
        if hasattr(signal, input.signal_name):
            sig = getattr(signal, input.signal_name)
        else:
            return {
                "success": False,
                "error": f"Unknown signal: {input.signal_name}",
                "error_code": "UNKNOWN_SIGNAL",
                "action": "kill",
                "pid": input.pid
            }

        # Find and kill process
        try:
            proc = psutil.Process(input.pid)

            # Security check - don't allow killing critical system processes
            CRITICAL_PROCESSES = ['init', 'kthreadd', 'ksoftirqd', 'systemd']
            if proc.name() in CRITICAL_PROCESSES:
                return {
                    "success": False,
                    "error": f"Cannot kill critical system process: {proc.name()}",
                    "error_code": "CRITICAL_PROCESS_BLOCKED",
                    "action": "kill",
                    "pid": input.pid
                }

            process_name = proc.name()
            proc.send_signal(sig)

            # Wait for process to terminate
            time.sleep(1)

            if proc.is_running():
                if sig != signal.SIGKILL:
                    # Try with SIGKILL if SIGTERM didn't work
                    proc.send_signal(signal.SIGKILL)
                    time.sleep(1)

            success = not proc.is_running()

            return {
                "success": success,
                "action": "kill",
                "pid": input.pid,
                "signal": input.signal_name,
                "killed": success,
                "process_name": process_name,
                "timestamp": time.time()
            }

        except psutil.NoSuchProcess:
            return {
                "success": False,
                "error": f"Process not found: PID {input.pid}",
                "error_code": "PROCESS_NOT_FOUND",
                "action": "kill",
                "pid": input.pid
            }
        except psutil.AccessDenied:
            return {
                "success": False,
                "error": f"Access denied to process PID {input.pid}",
                "error_code": "ACCESS_DENIED",
                "action": "kill",
                "pid": input.pid
            }

    except ImportError:
        return {
            "success": False,
            "error": "psutil library not available. Install with: pip install psutil",
            "error_code": "MISSING_DEPENDENCY",
            "action": "kill"
        }


async def _monitor_process(input: ProcessManagerInput) -> dict[str, Any]:
    """Monitor a process for resource usage."""
    if not input.pid:
        return {
            "success": False,
            "error": "PID is required for monitor action",
            "error_code": "MISSING_PID",
            "action": "monitor"
        }

    try:
        import psutil

        try:
            proc = psutil.Process(input.pid)

            # Get process information
            with proc.oneshot():
                cpu_percent = proc.cpu_percent()
                memory_info = proc.memory_info()
                memory_percent = proc.memory_percent()
                create_time = proc.create_time()
                status = proc.status()

            return {
                "success": True,
                "action": "monitor",
                "pid": input.pid,
                "name": proc.name(),
                "status": status,
                "cpu_percent": cpu_percent,
                "memory_rss": memory_info.rss,
                "memory_vms": memory_info.vms,
                "memory_percent": memory_percent,
                "create_time": create_time,
                "uptime": time.time() - create_time,
                "timestamp": time.time()
            }

        except psutil.NoSuchProcess:
            return {
                "success": False,
                "error": f"Process not found: PID {input.pid}",
                "error_code": "PROCESS_NOT_FOUND",
                "action": "monitor",
                "pid": input.pid
            }
        except psutil.AccessDenied:
            return {
                "success": False,
                "error": f"Access denied to process PID {input.pid}",
                "error_code": "ACCESS_DENIED",
                "action": "monitor",
                "pid": input.pid
            }

    except ImportError:
        return {
            "success": False,
            "error": "psutil library not available. Install with: pip install psutil",
            "error_code": "MISSING_DEPENDENCY",
            "action": "monitor"
        }


# ---------------------------------------------------------------------------
# Build Tool
# ---------------------------------------------------------------------------


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
    is_destructive=True,  # Can kill processes
    is_concurrency_safe=False,
)
