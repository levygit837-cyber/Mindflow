"""System/Shell tools - Callable pattern (Phase 2).

All tools in this module use:
- Pydantic input schemas for type safety
- CallableToolResult return type
- ToolContext for runtime state (root_dir, sandbox_mode, permissions)
- Appropriate factories (build_callable_tool, build_destructive_tool)
"""

from __future__ import annotations

import os
import platform
import signal
import socket
import subprocess
import time
from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.schemas.tools.callable import CallableToolResult, ProgressCallback
from mindflow_backend.schemas.tools.callable_builder import (
    build_callable_tool,
    build_readonly_tool,
)
from mindflow_backend.schemas.tools.context import ToolContext
from mindflow_backend.schemas.tools.permission import PermissionBehavior


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
    """Execute shell command with security controls and resource limits.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context (permissions, abort signal, etc.)
        on_progress: Optional progress callback

    Returns:
        CallableToolResult with command output and execution metadata or error
    """
    # 1. Check sandbox mode for read-only enforcement (shell commands can write)
    if context.sandbox_mode and hasattr(context.sandbox_mode, 'value'):
        if context.sandbox_mode.value == "READ_ONLY":
            return CallableToolResult(
                data=None,
                success=False,
                error="Shell execution blocked in read-only mode",
                metadata={
                    "error_code": "READ_ONLY_MODE",
                    "command": input.command[:100],
                }
            )

    # 2. Security validation: dangerous commands
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
            return CallableToolResult(
                data=None,
                success=False,
                error=f"Dangerous command pattern detected: {pattern}",
                metadata={
                    "error_code": "DANGEROUS_COMMAND",
                    "command": input.command[:100],
                }
            )

    # 3. Check permissions (if manager available)
    if context.permission_manager:
        perm_result = await context.check_permission_async(
            tool_name="shell_execute",
            input=input.dict(),
            tool_content=input.command
        )

        if perm_result.behavior == PermissionBehavior.DENY:
            return CallableToolResult(
                data=None,
                success=False,
                error=perm_result.reason or "Permission denied",
                metadata={
                    "error_code": "PERMISSION_DENIED",
                    "command": input.command[:100],
                }
            )

    # 4. Resolve working directory
    working_dir = input.working_dir
    root_dir = context.root_dir or context.metadata.get("root_dir")

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
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Working directory not found: {working_dir}",
            metadata={
                "error_code": "DIRECTORY_NOT_FOUND",
                "working_dir": working_dir,
            }
        )

    # 5. Prepare environment
    env = os.environ.copy()

    # 6. Execute command
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

        # 7. Check return code if requested
        success = True
        if input.check_return_code and return_code != 0:
            success = False

        # 8. Truncate output if too large (100KB limit)
        max_output = 100_000
        if stdout and len(stdout) > max_output:
            stdout = stdout[:max_output] + "\n...[output truncated]"

        if stderr and len(stderr) > max_output:
            stderr = stderr[:max_output] + "\n...[output truncated]"

        return CallableToolResult(
            data={
                "output": stdout or "",
                "stderr": stderr or "",
                "return_code": return_code,
                "pid": process.pid,
                "working_dir": working_dir,
                "execution_time": round(execution_time, 3),
                "timed_out": timed_out,
                "command": input.command[:200],  # Truncate command in response
            },
            success=success,
            metadata={
                "operation": "shell_execute",
            }
        )

    except PermissionError as e:
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Permission denied: {e}",
            metadata={
                "error_code": "OS_PERMISSION_ERROR",
                "command": input.command[:100],
            }
        )
    except FileNotFoundError as e:
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Command not found: {e}",
            metadata={
                "error_code": "COMMAND_NOT_FOUND",
                "command": input.command[:100],
            }
        )
    except Exception as e:
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Shell execution failed: {e}",
            metadata={
                "error_code": "EXECUTION_ERROR",
                "command": input.command[:100],
            }
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
            interfaces[interface] = {"addresses": []}

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


async def system_info_impl(
    input: SystemInfoInput,
    context: ToolContext,
    on_progress: ProgressCallback | None = None,
) -> CallableToolResult[dict[str, Any]]:
    """Collect system information.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context
        on_progress: Optional progress callback

    Returns:
        CallableToolResult with system information or error
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

        result["info_type"] = input.info_type

        return CallableToolResult(
            data=result,
            success=True,
            metadata={
                "operation": "system_info",
            }
        )

    except Exception as e:
        return CallableToolResult(
            data=None,
            success=False,
            error=f"System information collection error: {e}",
            metadata={
                "error_code": "COLLECTION_ERROR",
                "info_type": input.info_type,
            }
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


async def _list_processes_callable(input: ProcessManagerInput) -> dict[str, Any]:
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
            "action": "list",
            "processes": processes,
            "count": len(processes),
            "timestamp": time.time()
        }

    except ImportError:
        raise ImportError("psutil library not available. Install with: pip install psutil")


async def _kill_process_callable(input: ProcessManagerInput) -> dict[str, Any]:
    """Kill a process by PID."""
    if not input.pid:
        raise ValueError("PID is required for kill action")

    try:
        import psutil

        # Convert signal name to signal number
        if hasattr(signal, input.signal_name):
            sig = getattr(signal, input.signal_name)
        else:
            raise ValueError(f"Unknown signal: {input.signal_name}")

        # Find and kill process
        try:
            proc = psutil.Process(input.pid)

            # Security check - don't allow killing critical system processes
            CRITICAL_PROCESSES = ['init', 'kthreadd', 'ksoftirqd', 'systemd']
            if proc.name() in CRITICAL_PROCESSES:
                raise PermissionError(f"Cannot kill critical system process: {proc.name()}")

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
                "action": "kill",
                "pid": input.pid,
                "signal": input.signal_name,
                "killed": success,
                "process_name": process_name,
                "timestamp": time.time()
            }

        except psutil.NoSuchProcess:
            raise FileNotFoundError(f"Process not found: PID {input.pid}")
        except psutil.AccessDenied:
            raise PermissionError(f"Access denied to process PID {input.pid}")

    except ImportError:
        raise ImportError("psutil library not available. Install with: pip install psutil")


async def _monitor_process_callable(input: ProcessManagerInput) -> dict[str, Any]:
    """Monitor a process for resource usage."""
    if not input.pid:
        raise ValueError("PID is required for monitor action")

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
            raise FileNotFoundError(f"Process not found: PID {input.pid}")
        except psutil.AccessDenied:
            raise PermissionError(f"Access denied to process PID {input.pid}")

    except ImportError:
        raise ImportError("psutil library not available. Install with: pip install psutil")


async def process_manager_impl(
    input: ProcessManagerInput,
    context: ToolContext,
    on_progress: ProgressCallback | None = None,
) -> CallableToolResult[dict[str, Any]]:
    """Execute process management operation.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context
        on_progress: Optional progress callback

    Returns:
        CallableToolResult with operation result or error
    """
    # 1. Check sandbox mode for read-only enforcement (process management can be destructive)
    if context.sandbox_mode and hasattr(context.sandbox_mode, 'value'):
        if context.sandbox_mode.value == "READ_ONLY" and input.action == "kill":
            return CallableToolResult(
                data=None,
                success=False,
                error="Process kill blocked in read-only mode",
                metadata={
                    "error_code": "READ_ONLY_MODE",
                    "action": input.action,
                }
            )

    # 2. Security check - verify user is authorized
    ALLOWED_USERS = {'root', 'admin', 'mindflow', os.getenv('USER', 'unknown')}
    current_user = os.getenv('USER', 'unknown')

    if current_user not in ALLOWED_USERS:
        return CallableToolResult(
            data=None,
            success=False,
            error=f"User {current_user} not authorized for process management",
            metadata={
                "error_code": "UNAUTHORIZED_USER",
                "action": input.action,
            }
        )

    try:
        action = input.action.lower()

        if action == "list":
            result = await _list_processes_callable(input)
        elif action == "kill":
            result = await _kill_process_callable(input)
        elif action == "monitor":
            result = await _monitor_process_callable(input)
        else:
            return CallableToolResult(
                data=None,
                success=False,
                error=f"Unknown action: {action}",
                metadata={
                    "error_code": "UNKNOWN_ACTION",
                    "action": action,
                }
            )

        return CallableToolResult(
            data=result,
            success=True,
            metadata={
                "operation": "process_manager",
            }
        )

    except ImportError as e:
        return CallableToolResult(
            data=None,
            success=False,
            error=str(e),
            metadata={
                "error_code": "MISSING_DEPENDENCY",
                "action": input.action,
            }
        )
    except ValueError as e:
        return CallableToolResult(
            data=None,
            success=False,
            error=str(e),
            metadata={
                "error_code": "INVALID_INPUT",
                "action": input.action,
            }
        )
    except FileNotFoundError as e:
        return CallableToolResult(
            data=None,
            success=False,
            error=str(e),
            metadata={
                "error_code": "PROCESS_NOT_FOUND",
                "action": input.action,
            }
        )
    except PermissionError as e:
        return CallableToolResult(
            data=None,
            success=False,
            error=str(e),
            metadata={
                "error_code": "PERMISSION_DENIED",
                "action": input.action,
            }
        )
    except Exception as e:
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Process management error: {e}",
            metadata={
                "error_code": "OPERATION_ERROR",
                "action": input.action,
            }
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
