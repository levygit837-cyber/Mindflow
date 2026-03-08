"""
Process management tool 
for system operations. Provides tools 
for managing system processes including monitoring, termination, and resource tracking 
with proper security controls. 
"""
 
from __future__ 
import annotations 
import os 
import signal 
import time 
from typing 
import Any, Dict, List, Optional, Union 
from mindflow_backend.infra.logging 
import get_logger 
from mindflow_backend.schemas.orchestration.orchestrator 
import AgentType 
from ..base.tool_interface 
import ToolInterface 
from ..base.tool_schemas 
import ( ToolSchema, ToolParameter, ParameterType, create_tool_schema, create_parameter ) _logger = get_logger(__name__) 
class ProcessManagerTool(ToolInterface): 
"""
Process management tool 
for system operations. Provides secure process management capabilities including monitoring, termination, and resource tracking 
with proper security controls. 
"""
 
def __init__(self): super().__init__() self.name = "process_manager" self.description = "System process management 
with monitoring and control capabilities" self._allowed_operations = ["list", "info", "terminate", "kill"] 
def get_schema(self) -> Dict[str, Any]: 
"""
Return tool schema 
for validation.
"""
 
return create_tool_schema( name=self.name, description=self.description, category="system", parameters=[ create_parameter( name="operation", param_type=ParameterType.STRING, description="Process operation to perform", required=True, enum=["list", "info", "terminate", "kill"] ), create_parameter( name="pid", param_type=ParameterType.INTEGER, description="Process ID (required 
for info, terminate, kill operations)", required=False, min_value=1 ), create_parameter( name="filter_name", param_type=ParameterType.STRING, description="Filter processes by name (
for list operation)", required=False ), create_parameter( name="filter_user", param_type=ParameterType.STRING, description="Filter processes by user (
for list operation)", required=False ), create_parameter( name="signal", param_type=ParameterType.INTEGER, description="Signal number (
for kill operation)", required=False, default=signal.SIGTERM, min_value=1, max_value=64 ), create_parameter( name="timeout", param_type=ParameterType.INTEGER, description="Operation timeout in seconds", required=False, default=10, min_value=1, max_value=60 ) ], requires_sandbox=True, supported_agents=[AgentType.CODER, AgentType.ORCHESTRATOR], security_level="high" ).dict() 
def execute(self, *args, **kwargs) -> Dict[str, Any]: 
"""
Execute process management operation 
with security controls. Args: operation: Operation to perform (list, info, terminate, kill) pid: Process ID (
for info, terminate, kill) filter_name: Filter processes by name filter_user: Filter processes by user signal: Signal number (
for kill) timeout: Operation timeout Returns: Operation result 
with process information 
"""
 try: operation = kwargs.get("operation") 
if not operation: 
return self._format_result( success=False, error="operation parameter is required" ) 
if operation not in self._allowed_operations: 
return self._format_result( success=False, error=f"Invalid operation: {operation}. Allowed: {self._allowed_operations}" ) 
# Validate operation-specific parameters 
if operation in ["info", "terminate", "kill"]: pid = kwargs.get("pid") 
if not pid: 
return self._format_result( success=False, error=f"pid parameter is required 
for {operation} operation" ) 
# Validate PID existence and permissions 
if not self._validate_pid_access(pid): 
return self._format_result( success=False, error=f"Access denied or invalid PID: {pid}" ) 
# Execute operation 
if operation == "list": result = self._list_processes( name_filter=kwargs.get("filter_name"), user_filter=kwargs.get("filter_user") ) el
if operation == "info": result = self._get_process_info(kwargs.get("pid")) el
if operation == "terminate": result = self._terminate_process(kwargs.get("pid")) el
if operation == "kill": result = self._kill_process( kwargs.get("pid"), kwargs.get("signal", signal.SIGTERM) ) 
else: result = {"error": f"Unknown operation: {operation}"} 
return self._format_result( success=result.get("success", True), result=result, metadata={ "operation": operation, "timestamp": time.time(), "user": os.getuid() 
if hasattr(os, 'getuid') else "unknown" } ) 
except Exception as e: _logger.error( "process_operation_failed", operation=kwargs.get("operation"), pid=kwargs.get("pid"), error=str(e) ) 
return self._format_result( success=False, error=f"Process operation failed: {str(e)}" ) 
def _validate_pid_access(self, pid: int) -> bool: 
"""
Validate 
if PID can be accessed by current user. Args: pid: Process ID to validate Returns: True 
if access is allowed 
"""
 try: 
# Check 
if process exists 
if not self._process_exists(pid): 
return False 
# Check 
if we can access process information try: os.kill(pid, 0) 
# Signal 0 just checks existence 
return True 
except ProcessLookupError: 
return False 
except PermissionError: _logger.warning("process_access_denied", pid=pid) 
return False 
except Exception as e: _logger.error("pid_validation_error", pid=pid, error=str(e)) 
return False 
def _process_exists(self, pid: int) -> bool: 
"""
Check 
if process exists. Args: pid: Process ID to check Returns: True 
if process exists 
"""
 try: os.kill(pid, 0) 
return True 
except ProcessLookupError: 
return False 
except PermissionError: 
# Process exists but we can't signal it 
return True 
except Exception: 
return False 
def _list_processes(self, name_filter: Optional[str], user_filter: Optional[str]) -> Dict[str, Any]: 
"""
List system processes 
with optional filtering. Args: name_filter: Filter by process name user_filter: Filter by user Returns: List of process information 
"""
 try: processes = [] 
# Mock process listing (in real implementation, use psutil) mock_processes = [ {"pid": 1, "name": "init", "user": "root", "cpu": 0.1, "memory": 1024}, {"pid": 100, "name": "python", "user": "user", "cpu": 2.5, "memory": 51200}, {"pid": 200, "name": "nginx", "user": "www-data", "cpu": 0.5, "memory": 2048}, {"pid": 300, "name": "postgres", "user": "postgres", "cpu": 1.2, "memory": 16384}, ] 
for proc in mock_processes: 
# Apply filters 
if name_filter and name_filter.lower() not in proc["name"].lower(): continue 
if user_filter and user_filter != proc["user"]: continue processes.append(proc) _logger.info( "processes_listed", total_processes=len(mock_processes), filtered_processes=len(processes), name_filter=name_filter, user_filter=user_filter ) 
return { "success": True, "processes": processes, "total_count": len(processes), "filters": { "name": name_filter, "user": user_filter } } 
except Exception as e: _logger.error("process_list_failed", error=str(e)) 
return { "success": False, "error": str(e), "processes": [] } 
def _get_process_info(self, pid: int) -> Dict[str, Any]: 
"""
Get detailed information about a specific process. Args: pid: Process ID Returns: Detailed process information 
"""
 try: 
if not self._process_exists(pid): 
return { "success": False, "error": f"Process {pid} does not exist" } 
# Mock process information (in real implementation, use psutil) process_info = { "pid": pid, "name": f"process_{pid}", "status": "running", "user": "user", "cpu_percent": 1.5, "memory_mb": 25600, "memory_percent": 2.5, "create_time": time.time() - 3600, 
# Started 1 hour ago "cmdline": [f"/usr/bin/process_{pid}", "--daemon"], "cwd": "/home/user", "num_threads": 4, "connections": 10 } _logger.info("process_info_retrieved", pid=pid) 
return { "success": True, "process": process_info } 
except Exception as e: _logger.error("process_info_failed", pid=pid, error=str(e)) 
return { "success": False, "error": str(e) } 
def _terminate_process(self, pid: int) -> Dict[str, Any]: 
"""
Terminate a process gracefully. Args: pid: Process ID to terminate Returns: Termination result 
"""
 try: 
if not self._process_exists(pid): 
return { "success": False, "error": f"Process {pid} does not exist" } 
# Check 
if it's a protected process 
if self._is_protected_process(pid): 
return { "success": False, "error": f"Process {pid} is protected and cannot be terminated" } 
# Send SIGTERM signal os.kill(pid, signal.SIGTERM) 
# Wait 
for process to terminate time.sleep(2) 
if self._process_exists(pid): 
# Process still running, force kill os.kill(pid, signal.SIGKILL) time.sleep(1) success = not self._process_exists(pid) _logger.info( "process_termination_completed", pid=pid, success=success, method="graceful" 
if success else "forced" ) 
return { "success": success, "pid": pid, "method": "graceful" 
if success else "forced", "message": f"Process {pid} terminated successfully" 
if success else f"Process {pid} termination failed" } 
except PermissionError: 
return { "success": False, "error": f"Permission denied to terminate process {pid}" } 
except Exception as e: _logger.error("process_termination_failed", pid=pid, error=str(e)) 
return { "success": False, "error": str(e) } 
def _kill_process(self, pid: int, sig: int) -> Dict[str, Any]: 
"""
Send a signal to a process. Args: pid: Process ID sig: Signal number Returns: Signal result 
"""
 try: 
if not self._process_exists(pid): 
return { "success": False, "error": f"Process {pid} does not exist" } 
# Check 
if it's a protected process 
if self._is_protected_process(pid) and sig != signal.SIGTERM: 
return { "success": False, "error": f"Process {pid} is protected and cannot be killed 
with signal {sig}" } 
# Send signal os.kill(pid, sig) signal_name = signal.Signals(sig).name 
if hasattr(signal, 'Signals') else str(sig) _logger.info( "signal_sent_to_process", pid=pid, signal=sig, signal_name=signal_name ) 
return { "success": True, "pid": pid, "signal": sig, "signal_name": signal_name, "message": f"Signal {signal_name} ({sig}) sent to process {pid}" } 
except PermissionError: 
return { "success": False, "error": f"Permission denied to signal process {pid}" } 
except Exception as e: _logger.error("process_signal_failed", pid=pid, signal=sig, error=str(e)) 
return { "success": False, "error": str(e) } 
def _is_protected_process(self, pid: int) -> bool: 
"""
Check 
if process is protected 
from termination. Args: pid: Process ID to check Returns: True 
if process is protected 
"""
 
# Protect critical system processes (mock implementation) protected_pids = [1] 
# init process protected_names = ["init", "kthreadd", "ksoftirqd"] 
# Check PID 
if pid in protected_pids: 
return True 
# Check name (would need real process info) 
# For now, only protect PID 1 
return False