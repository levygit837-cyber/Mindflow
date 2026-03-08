"""System tool interfaces for MindFlow backend.

Provides contracts for system-level operations including process management,
sandboxed execution, and system monitoring with proper security controls.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Any, Dict, List, Optional, Union
from pathlib import Path


@runtime_checkable
class SystemToolInterface(Protocol):
    """Interface for system-level operations."""
    
    async def execute_command(
        self,
        command: str,
        args: List[str],
        working_dir: Optional[str] = None,
        timeout: int = 60,
        env: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Execute system command with safety controls.
        
        Args:
            command: Command to execute
            args: Command arguments
            working_dir: Working directory
            timeout: Execution timeout in seconds
            env: Environment variables
            
        Returns:
            Dictionary with execution result
        """
        ...


@runtime_checkable
class ProcessManagerTool(Protocol):
    """Interface for process management operations."""
    
    async def start_process(
        self,
        command: str,
        args: List[str],
        pid_file: Optional[str] = None,
        working_dir: Optional[str] = None,
        env: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Start a background process.
        
        Args:
            command: Command to execute
            args: Command arguments
            pid_file: File to store process ID
            working_dir: Working directory
            env: Environment variables
            
        Returns:
            Dictionary with process information
        """
        ...
    
    async def stop_process(
        self,
        pid: int,
        signal: str = "TERM",
        timeout: int = 10
    ) -> Dict[str, Any]:
        """Stop a running process.
        
        Args:
            pid: Process ID
            signal: Signal to send (TERM, KILL, etc.)
            timeout: Wait time for graceful shutdown
            
        Returns:
            Dictionary with stop result
        """
        ...
    
    async def get_process_status(self, pid: int) -> Dict[str, Any]:
        """Get status of a process.
        
        Args:
            pid: Process ID
            
        Returns:
            Dictionary with process status
        """
        ...
    
    async def list_processes(
        self,
        filter_name: Optional[str] = None,
        filter_user: Optional[str] = None
    ) -> Dict[str, Any]:
        """List running processes with optional filtering.
        
        Args:
            filter_name: Filter by process name
            filter_user: Filter by process user
            
        Returns:
            Dictionary with process list
        """
        ...


@runtime_checkable
class SandboxTool(Protocol):
    """Interface for sandboxed command execution."""
    
    async def execute_in_sandbox(
        self,
        command: str,
        args: List[str],
        sandbox_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute command in isolated sandbox environment.
        
        Args:
            command: Command to execute
            args: Command arguments
            sandbox_config: Sandbox configuration
            
        Returns:
            Dictionary with execution result
        """
        ...
    
    async def create_sandbox(
        self,
        root_dir: str,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create sandbox environment.
        
        Args:
            root_dir: Sandbox root directory
            config: Sandbox configuration
            
        Returns:
            Dictionary with sandbox information
        """
        ...
    
    async def cleanup_sandbox(self, sandbox_id: str) -> Dict[str, Any]:
        """Clean up sandbox environment.
        
        Args:
            sandbox_id: Sandbox identifier
            
        Returns:
            Dictionary with cleanup result
        """
        ...


@runtime_checkable
class SystemMonitorTool(Protocol):
    """Interface for system monitoring operations."""
    
    async def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information.
        
        Returns:
            Dictionary with system details
        """
        ...
    
    async def get_resource_usage(self, pid: Optional[int] = None) -> Dict[str, Any]:
        """Get resource usage information.
        
        Args:
            pid: Specific process ID, None for system-wide
            
        Returns:
            Dictionary with resource usage
        """
        ...
    
    async def get_disk_usage(self, path: str = "/") -> Dict[str, Any]:
        """Get disk usage information.
        
        Args:
            path: Path to check
            
        Returns:
            Dictionary with disk usage
        """
        ...
    
    async def get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage information.
        
        Returns:
            Dictionary with memory usage
        """
        ...
    
    async def get_network_info(self) -> Dict[str, Any]:
        """Get network information.
        
        Returns:
            Dictionary with network details
        """
        ...


@runtime_checkable
class EnvironmentTool(Protocol):
    """Interface for environment management."""
    
    async def get_environment_variables(self) -> Dict[str, Any]:
        """Get all environment variables.
        
        Returns:
            Dictionary with environment variables
        """
        ...
    
    async def set_environment_variable(
        self,
        name: str,
        value: str,
        scope: str = "session"
    ) -> Dict[str, Any]:
        """Set environment variable.
        
        Args:
            name: Variable name
            value: Variable value
            scope: Variable scope (session, process, system)
            
        Returns:
            Dictionary with operation result
        """
        ...
    
    async def get_path_info(self) -> Dict[str, Any]:
        """Get PATH environment variable information.
        
        Returns:
            Dictionary with PATH details
        """
        ...


@runtime_checkable
class PermissionTool(Protocol):
    """Interface for file permission management."""
    
    async def get_permissions(self, path: str) -> Dict[str, Any]:
        """Get file/directory permissions.
        
        Args:
            path: Path to check
            
        Returns:
            Dictionary with permission information
        """
        ...
    
    async def set_permissions(
        self,
        path: str,
        mode: str,
        recursive: bool = False
    ) -> Dict[str, Any]:
        """Set file/directory permissions.
        
        Args:
            path: Path to modify
            mode: Permission mode (octal)
            recursive: Apply recursively to directories
            
        Returns:
            Dictionary with operation result
        """
        ...
    
    async def get_ownership(self, path: str) -> Dict[str, Any]:
        """Get file/directory ownership.
        
        Args:
            path: Path to check
            
        Returns:
            Dictionary with ownership information
        """
        ...


@runtime_checkable
class SystemInfoCollector(Protocol):
    """Interface for comprehensive system information collection."""
    
    async def collect_system_info(
        self,
        include_detailed: bool = False,
        include_performance: bool = False
    ) -> Dict[str, Any]:
        """Collect comprehensive system information.
        
        Args:
            include_detailed: Include detailed hardware information
            include_performance: Include performance benchmarks
            
        Returns:
            Dictionary with system information
        """
        ...
    
    async def get_cpu_info(self, detailed: bool = False) -> Dict[str, Any]:
        """Get CPU information.
        
        Args:
            detailed: Include detailed CPU information
            
        Returns:
            CPU information dictionary
        """
        ...
    
    async def get_memory_info(self) -> Dict[str, Any]:
        """Get memory information.
        
        Returns:
            Memory information dictionary
        """
        ...
    
    async def get_gpu_info(self, detailed: bool = False) -> List[Dict[str, Any]]:
        """Get GPU information.
        
        Args:
            detailed: Include detailed GPU information
            
        Returns:
            List of GPU information dictionaries
        """
        ...
    
    async def generate_recommendations(
        self,
        system_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate system recommendations.
        
        Args:
            system_info: Collected system information
            
        Returns:
            System recommendations
        """
        ...


@runtime_checkable
class ResourceMonitor(Protocol):
    """Interface for real-time resource monitoring."""
    
    async def monitor_resources(
        self,
        duration_seconds: int,
        interval_seconds: int = 1,
        include_history: bool = True,
        check_alerts: bool = True
    ) -> Dict[str, Any]:
        """Monitor system resources.
        
        Args:
            duration_seconds: Monitoring duration
            interval_seconds: Sampling interval
            include_history: Include historical data
            check_alerts: Check for alert conditions
            
        Returns:
            Monitoring results
        """
        ...
    
    async def get_current_metrics(self) -> Dict[str, Any]:
        """Get current resource metrics.
        
        Returns:
            Current metrics dictionary
        """
        ...
    
    async def get_alert_thresholds(self) -> Dict[str, float]:
        """Get current alert thresholds.
        
        Returns:
            Alert thresholds dictionary
        """
        ...
    
    async def set_alert_thresholds(self, thresholds: Dict[str, float]) -> None:
        """Set alert thresholds.
        
        Args:
            thresholds: Threshold values
        """
        ...
    
    async def check_alerts(self) -> List[Dict[str, Any]]:
        """Check for alert conditions.
        
        Returns:
            List of alerts
        """
        ...


@runtime_checkable
class NetworkTool(Protocol):
    """Interface for network operations and monitoring."""
    
    async def check_connectivity(self, host: str = "8.8.8.8", port: int = 53) -> bool:
        """Check network connectivity.
        
        Args:
            host: Host to check
            port: Port to check
            
        Returns:
            True if connected
        """
        ...
    
    async def get_network_interfaces(self) -> List[Dict[str, Any]]:
        """Get network interface information.
        
        Returns:
            List of network interface information
        """
        ...
    
    async def scan_ports(self, host: str, ports: List[int]) -> Dict[int, bool]:
        """Scan ports on a host.
        
        Args:
            host: Target host
            ports: Ports to scan
            
        Returns:
            Dictionary of port status
        """
        ...
    
    async def get_bandwidth_usage(self) -> Dict[str, Any]:
        """Get current bandwidth usage.
        
        Returns:
            Bandwidth usage information
        """
        ...
