"""PitchTab process monitoring and management.

Provides high-level monitoring interface for PitchTab instances
with automatic recovery and resource management.
"""

from __future__ import annotations

import asyncio
import signal
import subprocess
from typing import Dict, List, Optional

from omnimind_backend.agents.research.utils.health_checker import get_health_checker
from omnimind_backend.agents.research.utils.port_manager import get_port_manager
from omnimind_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class PitchTabMonitor:
    """Monitors and manages PitchTab browser instances."""
    
    def __init__(self) -> None:
        """Initialize PitchTab monitor."""
        self.port_manager = get_port_manager()
        self.health_checker = get_health_checker()
        self._instances: Dict[str, Dict[str, any]] = {}
        self._recovery_task: Optional[asyncio.Task] = None
        
    async def start_instance(
        self,
        instance_id: str,
        headless: bool = True,
        stealth: bool = True,
        preferred_port: Optional[int] = None,
    ) -> Dict[str, any]:
        """Start a new PitchTab instance with monitoring.
        
        Args:
            instance_id: Unique identifier for the instance
            headless: Run browser without UI
            stealth: Enable stealth mode
            preferred_port: Preferred port (will find alternative if taken)
            
        Returns:
            Dictionary with instance details
            
        Raises:
            RuntimeError: If instance cannot be started
        """
        # Allocate port
        if preferred_port and await self.port_manager.is_available(preferred_port):
            port = preferred_port
        else:
            port = await self.port_manager.allocate_port()
            
        try:
            # Start PitchTab process
            cmd = [
                "pinchtab",
                "--port", str(port),
                "--headless" if headless else "",
                "--stealth" if stealth else "",
            ]
            cmd = [arg for arg in cmd if arg]  # Remove empty strings
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            # Wait for startup
            await asyncio.sleep(2)
            
            # Check if process started successfully
            if process.returncode is not None:
                await self.port_manager.release_port(port)
                raise RuntimeError(f"PitchTab failed to start: {process.returncode}")
                
            # Register for monitoring
            await self.health_checker.register_process(instance_id, port, process.pid)
            
            instance_info = {
                "instance_id": instance_id,
                "port": port,
                "pid": process.pid,
                "headless": headless,
                "stealth": stealth,
                "status": "running",
                "created_at": asyncio.get_event_loop().time(),
                "process": process,
            }
            
            self._instances[instance_id] = instance_info
            
            _logger.info(
                "pitchtab_instance_started",
                instance_id=instance_id,
                port=port,
                pid=process.pid,
            )
            
            return instance_info
            
        except Exception as exc:
            if 'port' in locals():
                await self.port_manager.release_port(port)
            await self.health_checker.unregister_process(instance_id)
            
            _logger.error(
                "pitchtab_instance_start_failed",
                instance_id=instance_id,
                error=str(exc),
            )
            
            raise RuntimeError(f"Failed to start PitchTab instance: {exc}")
            
    async def stop_instance(self, instance_id: str) -> bool:
        """Stop a PitchTab instance gracefully.
        
        Args:
            instance_id: Instance identifier to stop
            
        Returns:
            True if stopped successfully, False otherwise
        """
        if instance_id not in self._instances:
            _logger.warning("instance_not_found", instance_id=instance_id)
            return False
            
        instance_info = self._instances[instance_id]
        port = instance_info["port"]
        pid = instance_info["pid"]
        process = instance_info["process"]
        
        try:
            # Try graceful shutdown first
            if process and process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=10)
                except asyncio.TimeoutError:
                    # Force kill if graceful shutdown fails
                    process.kill()
                    await process.wait()
                    
            # Cleanup resources
            await self.port_manager.release_port(port)
            await self.health_checker.unregister_process(instance_id)
            
            # Remove from tracking
            del self._instances[instance_id]
            
            _logger.info(
                "pitchtab_instance_stopped",
                instance_id=instance_id,
                port=port,
                pid=pid,
            )
            
            return True
            
        except Exception as exc:
            _logger.error(
                "pitchtab_instance_stop_failed",
                instance_id=instance_id,
                error=str(exc),
            )
            
            return False
            
    async def restart_instance(self, instance_id: str) -> bool:
        """Restart a PitchTab instance.
        
        Args:
            instance_id: Instance identifier to restart
            
        Returns:
            True if restarted successfully, False otherwise
        """
        if instance_id not in self._instances:
            return False
            
        # Get current config
        old_instance = self._instances[instance_id]
        config = {
            "headless": old_instance["headless"],
            "stealth": old_instance["stealth"],
            "preferred_port": old_instance["port"],
        }
        
        # Stop old instance
        stop_success = await self.stop_instance(instance_id)
        if not stop_success:
            return False
            
        # Start new instance with same config
        try:
            await self.start_instance(instance_id, **config)
            return True
        except Exception:
            return False
            
    async def get_instance_health(self, instance_id: str) -> Optional[Dict[str, any]]:
        """Get health status for a specific instance.
        
        Args:
            instance_id: Instance identifier
            
        Returns:
            Health status dictionary or None if not found
        """
        if instance_id not in self._instances:
            return None
            
        is_healthy = await self.health_checker.is_healthy(instance_id)
        instance_info = self._instances[instance_id].copy()
        instance_info["is_healthy"] = is_healthy
        
        return instance_info
        
    async def get_all_instances(self) -> List[Dict[str, any]]:
        """Get status of all PitchTab instances.
        
        Returns:
            List of instance status dictionaries
        """
        instances = []
        for instance_id, instance_info in self._instances.items():
            is_healthy = await self.health_checker.is_healthy(instance_id)
            status = instance_info.copy()
            status["is_healthy"] = is_healthy
            instances.append(status)
            
        return instances
        
    async def cleanup_failed_instances(self) -> int:
        """Clean up failed or orphaned instances.
        
        Returns:
            Number of instances cleaned up
        """
        cleaned = 0
        unhealthy = await self.health_checker.get_unhealthy_processes()
        
        for instance_id in unhealthy:
            if await self.restart_instance(instance_id):
                _logger.info("unhealthy_instance_restarted", instance_id=instance_id)
            else:
                await self.stop_instance(instance_id)
                _logger.warning("unhealthy_instance_stopped", instance_id=instance_id)
                cleaned += 1
                
        return cleaned
        
    async def start_monitoring(self) -> None:
        """Start continuous monitoring and recovery."""
        if self._recovery_task and not self._recovery_task.done():
            return
            
        self._recovery_task = asyncio.create_task(self._monitoring_loop())
        await self.health_checker.start_monitoring()
        
        _logger.info("pitchtab_monitoring_started")
        
    async def stop_monitoring(self) -> None:
        """Stop all monitoring and cleanup instances."""
        if self._recovery_task:
            self._recovery_task.cancel()
            try:
                await self._recovery_task
            except asyncio.CancelledError:
                pass
                
        await self.health_checker.stop_monitoring()
        
        # Stop all instances
        instance_ids = list(self._instances.keys())
        for instance_id in instance_ids:
            await self.stop_instance(instance_id)
            
        _logger.info("pitchtab_monitoring_stopped")
        
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop with automatic recovery."""
        while True:
            try:
                # Cleanup failed instances
                await self.cleanup_failed_instances()
                
                # Check for orphaned processes
                await self._cleanup_orphaned_processes()
                
                # Sleep before next check
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as exc:
                _logger.error("pitchtab_monitor_loop_error", error=str(exc))
                await asyncio.sleep(10)
                
    async def _cleanup_orphaned_processes(self) -> None:
        """Find and cleanup orphaned PinchTab processes."""
        try:
            # Get all PinchTab processes
            result = await asyncio.create_subprocess_exec(
                "pgrep", "-f", "pinchtab",
                stdout=asyncio.subprocess.PIPE,
            )
            stdout, _ = await result.communicate()
            
            if not stdout:
                return
                
            pids = [int(pid.strip()) for pid in stdout.decode().split('\n') if pid.strip()]
            tracked_pids = {
                info["pid"] for info in self._instances.values() if info["pid"]
            }
            
            # Find orphaned PIDs (running but not tracked)
            orphaned_pids = set(pids) - tracked_pids
            
            for pid in orphaned_pids:
                try:
                    # Kill orphaned process
                    process = await asyncio.create_subprocess_exec(
                        "kill", "-9", str(pid),
                    )
                    await process.wait()
                    
                    _logger.warning("orphaned_process_killed", pid=pid)
                except Exception as exc:
                    _logger.error("orphan_cleanup_failed", pid=pid, error=str(exc))
                    
        except Exception as exc:
            _logger.error("orphan_scan_failed", error=str(exc))
            
    def get_monitoring_status(self) -> Dict[str, any]:
        """Get overall monitoring status.
        
        Returns:
            Dictionary with monitoring status
        """
        port_status = self.port_manager.get_status()
        health_status = self.health_checker.get_status_summary()
        
        return {
            "monitoring_active": self._recovery_task and not self._recovery_task.done(),
            "total_instances": len(self._instances),
            "port_management": port_status,
            "health_monitoring": health_status,
            "instances": self._instances.copy(),
        }


# Global monitor instance
_pitchtab_monitor: PitchTabMonitor | None = None


def get_pitchtab_monitor() -> PitchTabMonitor:
    """Get or create global PitchTab monitor instance.
    
    Returns:
        PitchTabMonitor singleton instance
    """
    global _pitchtab_monitor
    if _pitchtab_monitor is None:
        _pitchtab_monitor = PitchTabMonitor()
    return _pitchtab_monitor
