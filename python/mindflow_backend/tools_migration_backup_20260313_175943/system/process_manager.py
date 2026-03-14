"""
Process management tool for system operations. Provides tools for managing system processes 
including monitoring, termination, and resource tracking with proper security controls. 
"""

from __future__ import annotations
import os
import signal
import time
from typing import Any, Dict, List, Optional, Union

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.schemas.tools.system_schemas import PROCESS_MANAGER_SCHEMA

_logger = get_logger(__name__)


class ProcessManagerTool(AsyncToolInterface):
    """
    Process management tool for system operations. Provides secure process management capabilities 
    including monitoring, termination, and resource tracking with proper security controls.
    """

    def __init__(self):
        super().__init__()
        self.name = "process_manager"
        self.description = "System process management with security controls"

        # Security settings
        self.restricted_commands = {
            'rm -rf /', 'dd if=', 'mkfs', 'fdisk', 'format',
            'shutdown', 'reboot', 'halt', 'poweroff'
        }
        self.allowed_users = {'root', 'admin', 'mindflow'}  # Configurable

        self._schema = PROCESS_MANAGER_SCHEMA

    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute process management operation.
        Args:
            action: Action to perform
            pid: Process ID
            signal: Signal to send
            filter_name: Filter by process name
            filter_user: Filter by user
        Returns:
            Dictionary with operation result
        """
        try:
            action = kwargs["action"].lower()
            
            # Security check
            current_user = os.getenv('USER', 'unknown')
            if current_user not in self.allowed_users:
                return self._format_result(
                    success=False,
                    error=f"User {current_user} not authorized for process management"
                )

            if action == "list":
                return self._list_processes(**kwargs)
            elif action == "kill":
                return self._kill_process(**kwargs)
            elif action == "monitor":
                return self._monitor_process(**kwargs)
            else:
                return self._format_result(
                    success=False,
                    error=f"Unknown action: {action}"
                )

        except PermissionError as e:
            return self._format_result(
                success=False,
                error=f"Permission denied: {str(e)}"
            )
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Process management error: {str(e)}"
            )

    def _list_processes(self, **kwargs) -> Dict[str, Any]:
        """
        List system processes with optional filtering.
        Args:
            filter_name: Filter by process name
            filter_user: Filter by user
        Returns:
            Dictionary with process list
        """
        try:
            import psutil
            
            filter_name = kwargs.get("filter_name")
            filter_user = kwargs.get("filter_user")
            
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status']):
                try:
                    proc_info = proc.info
                    
                    # Apply filters
                    if filter_name and filter_name.lower() not in proc_info.get('name', '').lower():
                        continue
                    
                    if filter_user and filter_user != proc_info.get('username'):
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

            return self._format_result(
                success=True,
                result={
                    "processes": processes,
                    "count": len(processes),
                    "timestamp": time.time()
                }
            )

        except ImportError:
            return self._format_result(
                success=False,
                error="psutil library not available. Install with: pip install psutil"
            )

    def _kill_process(self, **kwargs) -> Dict[str, Any]:
        """
        Kill a process by PID.
        Args:
            pid: Process ID
            signal: Signal to send
        Returns:
            Dictionary with kill result
        """
        try:
            pid = kwargs.get("pid")
            signal_name = kwargs.get("signal", "SIGTERM")
            
            if not pid:
                return self._format_result(
                    success=False,
                    error="PID is required for kill action"
                )

            # Convert signal name to signal number
            if hasattr(signal, signal_name):
                sig = getattr(signal, signal_name)
            else:
                return self._format_result(
                    success=False,
                    error=f"Unknown signal: {signal_name}"
                )

            import psutil
            
            # Find and kill process
            try:
                proc = psutil.Process(pid)
                
                # Security check - don't allow killing critical system processes
                if proc.name() in ['init', 'kthreadd', 'ksoftirqd']:
                    return self._format_result(
                        success=False,
                        error=f"Cannot kill critical system process: {proc.name()}"
                    )
                
                proc.send_signal(sig)
                
                # Wait for process to terminate
                time.sleep(1)
                
                if proc.is_running():
                    if sig != signal.SIGKILL:
                        # Try with SIGKILL if SIGTERM didn't work
                        proc.send_signal(signal.SIGKILL)
                        time.sleep(1)
                
                success = not proc.is_running()
                
                return self._format_result(
                    success=success,
                    result={
                        "pid": pid,
                        "signal": signal_name,
                        "killed": success,
                        "process_name": proc.name(),
                        "timestamp": time.time()
                    }
                )
                
            except psutil.NoSuchProcess:
                return self._format_result(
                    success=False,
                    error=f"Process not found: PID {pid}"
                )
            except psutil.AccessDenied:
                return self._format_result(
                    success=False,
                    error=f"Access denied to process PID {pid}"
                )

        except ImportError:
            return self._format_result(
                success=False,
                error="psutil library not available. Install with: pip install psutil"
            )

    def _monitor_process(self, **kwargs) -> Dict[str, Any]:
        """
        Monitor a process for resource usage.
        Args:
            pid: Process ID to monitor
        Returns:
            Dictionary with monitoring data
        """
        try:
            pid = kwargs.get("pid")
            
            if not pid:
                return self._format_result(
                    success=False,
                    error="PID is required for monitor action"
                )

            import psutil
            
            try:
                proc = psutil.Process(pid)
                
                # Get process information
                with proc.oneshot():
                    cpu_percent = proc.cpu_percent()
                    memory_info = proc.memory_info()
                    memory_percent = proc.memory_percent()
                    create_time = proc.create_time()
                    status = proc.status()
                    
                return self._format_result(
                    success=True,
                    result={
                        "pid": pid,
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
                )
                
            except psutil.NoSuchProcess:
                return self._format_result(
                    success=False,
                    error=f"Process not found: PID {pid}"
                )
            except psutil.AccessDenied:
                return self._format_result(
                    success=False,
                    error=f"Access denied to process PID {pid}"
                )

        except ImportError:
            return self._format_result(
                success=False,
                error="psutil library not available. Install with: pip install psutil"
            )

    def get_schema(self) -> Dict[str, Any]:
        """
        Get tool schema.
        """
        return self._schema.dict()
