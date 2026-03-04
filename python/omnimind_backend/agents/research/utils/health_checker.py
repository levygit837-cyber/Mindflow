"""Process health checker for PitchTab instances.

Monitors process vitality, resource usage, and provides
automatic recovery capabilities.
"""

from __future__ import annotations

import asyncio
import psutil
import time
from datetime import UTC, datetime, timedelta
from typing import Dict, List, Optional

from omnimind_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class ProcessHealth:
    """Health status of a single process."""
    
    def __init__(
        self,
        process_id: str,
        port: int,
        pid: Optional[int] = None,
    ) -> None:
        """Initialize process health tracking.
        
        Args:
            process_id: Unique identifier for the process
            port: Port number the process is using
            pid: System process ID if available
        """
        self.process_id = process_id
        self.port = port
        self.pid = pid
        self.status = "starting"
        self.last_check = datetime.now(UTC)
        self.created_at = datetime.now(UTC)
        self.error_count = 0
        self.cpu_percent = 0.0
        self.memory_mb = 0.0
        self.response_time_ms = 0.0
        self.consecutive_failures = 0
        
    def update_status(
        self,
        status: str,
        cpu_percent: float = 0.0,
        memory_mb: float = 0.0,
        response_time_ms: float = 0.0,
        is_error: bool = False,
    ) -> None:
        """Update health status with new metrics.
        
        Args:
            status: Current status string
            cpu_percent: CPU usage percentage
            memory_mb: Memory usage in MB
            response_time_ms: Response time in milliseconds
            is_error: Whether this update represents an error
        """
        self.status = status
        self.last_check = datetime.now(UTC)
        self.cpu_percent = cpu_percent
        self.memory_mb = memory_mb
        self.response_time_ms = response_time_ms
        
        if is_error:
            self.error_count += 1
            self.consecutive_failures += 1
        else:
            self.consecutive_failures = 0
            
    def is_healthy(self) -> bool:
        """Check if process is considered healthy.
        
        Returns:
            True if process is healthy, False otherwise
        """
        # Status-based checks
        if self.status in ["failed", "stopped", "error"]:
            return False
            
        # Consecutive failure check
        if self.consecutive_failures >= 3:
            return False
            
        # Resource usage checks
        if self.cpu_percent > 90.0:  # High CPU usage
            return False
            
        if self.memory_mb > 1024.0:  # High memory usage (>1GB)
            return False
            
        # Response time check
        if self.response_time_ms > 30000.0:  # > 30 seconds
            return False
            
        # Stale check (no updates for 5 minutes)
        if datetime.now(UTC) - self.last_check > timedelta(minutes=5):
            return False
            
        return True
        
    def get_uptime_seconds(self) -> float:
        """Get process uptime in seconds.
        
        Returns:
            Uptime in seconds
        """
        return (datetime.now(UTC) - self.created_at).total_seconds()
        
    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary representation.
        
        Returns:
            Dictionary with all health metrics
        """
        return {
            "process_id": self.process_id,
            "port": self.port,
            "pid": self.pid,
            "status": self.status,
            "uptime_seconds": self.get_uptime_seconds(),
            "last_check": self.last_check.isoformat(),
            "created_at": self.created_at.isoformat(),
            "error_count": self.error_count,
            "consecutive_failures": self.consecutive_failures,
            "cpu_percent": self.cpu_percent,
            "memory_mb": self.memory_mb,
            "response_time_ms": self.response_time_ms,
            "is_healthy": self.is_healthy(),
        }


class HealthChecker:
    """Monitors health of PitchTab processes."""
    
    def __init__(self, check_interval: int = 30) -> None:
        """Initialize health checker.
        
        Args:
            check_interval: Seconds between health checks
        """
        self.check_interval = check_interval
        self._processes: Dict[str, ProcessHealth] = {}
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
        
    async def register_process(
        self,
        process_id: str,
        port: int,
        pid: Optional[int] = None,
    ) -> None:
        """Register a new process for monitoring.
        
        Args:
            process_id: Unique process identifier
            port: Port number process is using
            pid: System process ID
        """
        health = ProcessHealth(process_id, port, pid)
        self._processes[process_id] = health
        
        _logger.info(
            "process_registered",
            process_id=process_id,
            port=port,
            pid=pid,
            total_processes=len(self._processes),
        )
        
    async def unregister_process(self, process_id: str) -> None:
        """Unregister a process from monitoring.
        
        Args:
            process_id: Process identifier to remove
        """
        if process_id in self._processes:
            del self._processes[process_id]
            
            _logger.info(
                "process_unregistered",
                process_id=process_id,
                total_processes=len(self._processes),
            )
            
    async def update_process_health(
        self,
        process_id: str,
        status: str,
        cpu_percent: float = 0.0,
        memory_mb: float = 0.0,
        response_time_ms: float = 0.0,
        is_error: bool = False,
    ) -> None:
        """Update health metrics for a process.
        
        Args:
            process_id: Process identifier
            status: Current status
            cpu_percent: CPU usage percentage
            memory_mb: Memory usage in MB
            response_time_ms: Response time in milliseconds
            is_error: Whether this represents an error
        """
        if process_id not in self._processes:
            await self.register_process(process_id, 0)  # Default port, will be updated
            
        self._processes[process_id].update_status(
            status, cpu_percent, memory_mb, response_time_ms, is_error
        )
        
    async def is_healthy(self, process_id: str) -> bool:
        """Check if a specific process is healthy.
        
        Args:
            process_id: Process identifier
            
        Returns:
            True if process is healthy, False otherwise
        """
        if process_id not in self._processes:
            return False
            
        return self._processes[process_id].is_healthy()
        
    async def get_unhealthy_processes(self) -> List[str]:
        """Get list of unhealthy process IDs.
        
        Returns:
            List of unhealthy process IDs
        """
        unhealthy = []
        for process_id, health in self._processes.items():
            if not health.is_healthy():
                unhealthy.append(process_id)
                
        return unhealthy
        
    async def start_monitoring(self) -> None:
        """Start continuous health monitoring."""
        if self._running:
            return
            
        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitor_loop())
        
        _logger.info("health_monitoring_started", check_interval=self.check_interval)
        
    async def stop_monitoring(self) -> None:
        """Stop continuous health monitoring."""
        if not self._running:
            return
            
        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
                
        _logger.info("health_monitoring_stopped")
        
    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                _logger.error("health_monitor_loop_error", error=str(exc))
                await asyncio.sleep(5)  # Brief pause on error
                
    async def _perform_health_checks(self) -> None:
        """Perform health checks on all registered processes."""
        for process_id, health in self._processes.items():
            try:
                # Check if process is still running
                if health.pid:
                    process = psutil.Process(health.pid)
                    if not process.is_running():
                        health.update_status("stopped", is_error=True)
                        continue
                        
                    # Update resource usage
                    health.cpu_percent = process.cpu_percent()
                    health.memory_mb = process.memory_info().rss / 1024 / 1024
                    
                # Update last check time
                health.last_check = datetime.now(UTC)
                
            except psutil.NoSuchProcess:
                health.update_status("stopped", is_error=True)
            except Exception as exc:
                _logger.warning(
                    "process_health_check_failed",
                    process_id=process_id,
                    error=str(exc),
                )
                health.update_status("error", is_error=True)
                
    def get_status_summary(self) -> Dict[str, any]:
        """Get overall health checker status.
        
        Returns:
            Dictionary with status summary
        """
        total_processes = len(self._processes)
        healthy_count = sum(1 for h in self._processes.values() if h.is_healthy())
        unhealthy_count = total_processes - healthy_count
        
        return {
            "monitoring_active": self._running,
            "total_processes": total_processes,
            "healthy_processes": healthy_count,
            "unhealthy_processes": unhealthy_count,
            "health_percentage": (healthy_count / total_processes * 100) if total_processes > 0 else 0,
            "check_interval": self.check_interval,
            "processes": [h.to_dict() for h in self._processes.values()],
        }


# Global health checker instance
_health_checker: HealthChecker | None = None


def get_health_checker() -> HealthChecker:
    """Get or create global health checker instance.
    
    Returns:
        HealthChecker singleton instance
    """
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker
