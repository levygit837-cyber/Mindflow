"""
Resource monitoring tool for system operations. Provides tools for monitoring CPU, memory, 
disk, and network usage with alerting capabilities.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Union

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.schemas.tools.system_schemas import RESOURCE_MONITOR_SCHEMA

_logger = get_logger(__name__)


class ResourceMonitorTool(AsyncToolInterface):
    """
    Resource monitoring tool for system operations. Provides comprehensive monitoring 
    of system resources including CPU, memory, disk, and network usage with alerting.
    """

    def __init__(self):
        super().__init__()
        self.name = "resource_monitor"
        self.description = "System resource monitoring with alerting"
        
        # Monitoring settings
        self.monitoring_interval = 5  # seconds
        self.history_size = 100  # number of data points to keep
        self.alert_thresholds = {
            "cpu": 80.0,  # percentage
            "memory": 85.0,  # percentage
            "disk": 90.0,  # percentage
            "network": 1000000  # bytes per second
        }

        self._schema = RESOURCE_MONITOR_SCHEMA

        # Internal state
        self._monitoring = False
        self._monitoring_task = None
        self._history = {
            "cpu": [],
            "memory": [],
            "disk": [],
            "network": []
        }
        self._alerts = []

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute resource monitoring operation.
        Args:
            action: Action to perform
            resources: Resources to monitor
            duration: Monitoring duration
            interval: Monitoring interval
            alert_conditions: Alert conditions
        Returns:
            Dictionary with monitoring result
        """
        try:
            action = kwargs["action"].lower()
            
            if action == "start":
                return await self._start_monitoring(**kwargs)
            elif action == "stop":
                return await self._stop_monitoring()
            elif action == "get_current":
                return await self._get_current_resources(**kwargs)
            elif action == "get_history":
                return await self._get_history(**kwargs)
            else:
                return self._format_result(
                    success=False,
                    error=f"Unknown action: {action}"
                )

        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Resource monitoring error: {str(e)}"
            )

    async def _start_monitoring(self, **kwargs) -> Dict[str, Any]:
        """
        Start resource monitoring.
        Args:
            resources: Resources to monitor
            duration: Monitoring duration
            interval: Monitoring interval
            alert_conditions: Alert conditions
        Returns:
            Dictionary with start result
        """
        if self._monitoring:
            return self._format_result(
                success=False,
                error="Monitoring already started"
            )

        resources = kwargs.get("resources", ["cpu", "memory"])
        duration = kwargs.get("duration", 60)
        interval = kwargs.get("interval", self.monitoring_interval)
        alert_conditions = kwargs.get("alert_conditions", {})

        # Update alert thresholds
        self.alert_thresholds.update(alert_conditions)

        # Start monitoring task
        self._monitoring = True
        self._monitoring_task = asyncio.create_task(
            self._monitor_loop(resources, duration, interval)
        )

        return self._format_result(
            success=True,
            result={
                "monitoring": True,
                "resources": resources,
                "duration": duration,
                "interval": interval,
                "start_time": time.time()
            }
        )

    async def _stop_monitoring(self) -> Dict[str, Any]:
        """
        Stop resource monitoring.
        Returns:
            Dictionary with stop result
        """
        if not self._monitoring:
            return self._format_result(
                success=False,
                error="Monitoring not started"
            )

        self._monitoring = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        return self._format_result(
            success=True,
            result={
                "monitoring": False,
                "stop_time": time.time(),
                "final_history": self._history
            }
        )

    async def _get_current_resources(self, **kwargs) -> Dict[str, Any]:
        """
        Get current resource usage.
        Args:
            resources: Resources to get
        Returns:
            Dictionary with current resource usage
        """
        try:
            import psutil
            
            resources = kwargs.get("resources", ["cpu", "memory"])
            current_data = {}

            if "cpu" in resources:
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

            if "memory" in resources:
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

            if "disk" in resources:
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

            if "network" in resources:
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

            return self._format_result(
                success=True,
                result={
                    "current": current_data,
                    "timestamp": time.time()
                }
            )

        except ImportError:
            return self._format_result(
                success=False,
                error="psutil library not available. Install with: pip install psutil"
            )

    async def _get_history(self, **kwargs) -> Dict[str, Any]:
        """
        Get historical resource data.
        Args:
            resources: Resources to get history for
        Returns:
            Dictionary with historical data
        """
        resources = kwargs.get("resources", list(self._history.keys()))
        history_data = {}

        for resource in resources:
            if resource in self._history:
                history_data[resource] = self._history[resource][-self.history_size:]

        return self._format_result(
            success=True,
            result={
                "history": history_data,
                "alerts": self._alerts,
                "summary": self._calculate_summary(history_data)
            }
        )

    async def _monitor_loop(self, resources: List[str], duration: int, interval: int):
        """
        Main monitoring loop.
        Args:
            resources: Resources to monitor
            duration: Total monitoring duration
            interval: Monitoring interval
        """
        start_time = time.time()
        
        while self._monitoring and (time.time() - start_time) < duration:
            try:
                import psutil
                current_time = time.time()
                
                for resource in resources:
                    if resource == "cpu":
                        cpu_percent = psutil.cpu_percent()
                        self._add_to_history("cpu", cpu_percent, current_time)
                        
                        # Check alert
                        if cpu_percent > self.alert_thresholds["cpu"]:
                            await self._trigger_alert("cpu", cpu_percent, current_time)
                    
                    elif resource == "memory":
                        memory = psutil.virtual_memory()
                        self._add_to_history("memory", memory.percent, current_time)
                        
                        # Check alert
                        if memory.percent > self.alert_thresholds["memory"]:
                            await self._trigger_alert("memory", memory.percent, current_time)
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                _logger.error(f"Monitoring loop error: {str(e)}")
                await asyncio.sleep(interval)

    def _add_to_history(self, resource: str, value: float, timestamp: float):
        """
        Add data point to history.
        Args:
            resource: Resource name
            value: Resource value
            timestamp: Timestamp
        """
        self._history[resource].append({
            "value": value,
            "timestamp": timestamp
        })
        
        # Keep only recent history
        if len(self._history[resource]) > self.history_size:
            self._history[resource] = self._history[resource][-self.history_size:]

    async def _trigger_alert(self, resource: str, value: float, timestamp: float):
        """
        Trigger an alert for resource threshold.
        Args:
            resource: Resource name
            value: Current value
            timestamp: Alert timestamp
        """
        alert = {
            "resource": resource,
            "value": value,
            "threshold": self.alert_thresholds[resource],
            "timestamp": timestamp,
            "message": f"{resource.upper()} usage ({value}%) exceeds threshold ({self.alert_thresholds[resource]}%)"
        }
        
        self._alerts.append(alert)
        _logger.warning(f"Resource alert: {alert['message']}")

    def _calculate_summary(self, history_data: Dict[str, List]) -> Dict[str, Any]:
        """
        Calculate summary statistics from history.
        Args:
            history_data: Historical data
        Returns:
            Summary statistics
        """
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

    def get_schema(self) -> Dict[str, Any]:
        """
        Get tool schema.
        """
        return self._schema.dict()
