"""
Resource monitoring tools 
for MindFlow backend. Provides real-time system resource monitoring and performance tracking 
for optimization and alerting. 
"""
 
from __future__ 
import annotations 
import time 
import asyncio 
from typing 
import Any, Dict, List, Optional 
from collections 
import deque 
import psutil 
from mindflow_backend.infra.logging 
import get_logger 
from mindflow_backend.interfaces.tools.base 
import AsyncToolInterface 
from mindflow_backend.schemas.tools.tool_config 
import create_tool_schema 
from mindflow_backend.schemas.orchestration.orchestrator 
import AgentType _logger = get_logger(__name__) 
class ResourceMonitor(AsyncToolInterface): 
"""
Tool 
for monitoring system resources in real-time. Tracks CPU, memory, disk, and network usage 
with historical data and alerting capabilities. 
"""
 
def __init__(self, backend: Optional[Any] = None): 
"""
Initialize the resource monitor. Args: backend: Optional backend 
for compatibility 
"""
 super().__init__() self.backend = backend self.name = "resource_monitor" self.description = "Monitor system resources in real-time" 
# Historical data storage self._history_size = 300 
# 5 minutes at 1-second intervals self._cpu_history = deque(maxlen=self._history_size) self._memory_history = deque(maxlen=self._history_size) self._disk_history = deque(maxlen=self._history_size) self._network_history = deque(maxlen=self._history_size) 
# Alert thresholds self._alert_thresholds = { "cpu_percent": 80.0, "memory_percent": 85.0, "disk_percent": 90.0, "temperature_celsius": 80.0 } self._schema = create_tool_schema( name=self.name, description=self.description, category="system", parameters=[ { "name": "duration_seconds", "type": "integer", "description": "Monitoring duration in seconds", "required": False, "default": 10 }, { "name": "interval_seconds", "type": "integer", "description": "Sampling interval in seconds", "required": False, "default": 1 }, { "name": "include_history", "type": "boolean", "description": "Include historical data", "required": False, "default": True }, { "name": "check_alerts", "type": "boolean", "description": "Check 
for alert conditions", "required": False, "default": True } ], returns={ "type": "object", "description": "Resource monitoring results", "properties": { "current": {"type": "object", "description": "Current resource usage"}, "averages": {"type": "object", "description": "Average resource usage"}, "peaks": {"type": "object", "description": "Peak resource usage"}, "history": {"type": "object", "description": "Historical data"}, "alerts": {"type": "array", "description": "Alert conditions"} } } ) async 
def execute(self, **kwargs) -> Dict[str, Any]: 
"""
Monitor system resources 
for specified duration. Args: duration_seconds: Monitoring duration in seconds interval_seconds: Sampling interval in seconds include_history: Include historical data check_alerts: Check 
for alert conditions Returns: Dictionary 
with monitoring results 
"""
 try: duration_seconds = kwargs.get("duration_seconds", 10) interval_seconds = kwargs.get("interval_seconds", 1) include_history = kwargs.get("include_history", True) check_alerts = kwargs.get("check_alerts", True) monitoring_data = { "current": {}, "averages": {}, "peaks": {}, "history": {}, "alerts": [] } 
# Clear history 
for new monitoring session 
if not include_history: self._clear_history() 
# Monitor 
for specified duration end_time = time.time() + duration_seconds 
while time.time() < end_time: 
# Collect current metrics current_metrics = await self._collect_current_metrics() 
# Store in history self._cpu_history.append(current_metrics["cpu"]) self._memory_history.append(current_metrics["memory"]) self._disk_history.append(current_metrics["disk"]) self._network_history.append(current_metrics["network"]) 
# Sleep 
for interval await asyncio.sleep(interval_seconds) 
# Calculate statistics 
if self._cpu_history: monitoring_data["current"] = current_metrics monitoring_data["averages"] = self._calculate_averages() monitoring_data["peaks"] = self._calculate_peaks() 
if include_history: monitoring_data["history"] = self._get_history_data() 
if check_alerts: monitoring_data["alerts"] = self._check_alerts() 
return self._format_result( success=True, result=monitoring_data ) 
except Exception as e: 
return self._format_result( success=False, error=f"Resource monitoring failed: {str(e)}" ) async 
def _collect_current_metrics(self) -> Dict[str, Any]: 
"""
Collect current system metrics. Returns: Dictionary 
with current metrics 
"""
 metrics = {} 
# CPU metrics cpu_percent = psutil.cpu_percent(interval=None) cpu_freq = psutil.cpu_freq() metrics["cpu"] = { "percent": cpu_percent, "frequency_mhz": cpu_freq.current 
if cpu_freq else None, "per_cpu": psutil.cpu_percent(percpu=True), "load_average": self._get_load_average() } 
# Memory metrics memory = psutil.virtual_memory() swap = psutil.swap_memory() metrics["memory"] = { "virtual": { "total_gb": memory.total / (1024**3), "available_gb": memory.available / (1024**3), "used_gb": memory.used / (1024**3), "free_gb": memory.free / (1024**3), "percent": memory.percent }, "swap": { "total_gb": swap.total / (1024**3), "used_gb": swap.used / (1024**3), "free_gb": swap.free / (1024**3), "percent": swap.percent } } 
# Disk metrics disk = psutil.disk_usage('/') disk_io = psutil.disk_io_counters() metrics["disk"] = { "usage": { "total_gb": disk.total / (1024**3), "used_gb": disk.used / (1024**3), "free_gb": disk.free / (1024**3), "percent": (disk.used / disk.total) * 100 }, "io": { "read_bytes": disk_io.read_bytes 
if disk_io else 0, "write_bytes": disk_io.write_bytes 
if disk_io else 0, "read_count": disk_io.read_count 
if disk_io else 0, "write_count": disk_io.write_count 
if disk_io else 0 } } 
# Network metrics network = psutil.net_io_counters() metrics["network"] = { "bytes_sent": network.bytes_sent 
if network else 0, "bytes_recv": network.bytes_recv 
if network else 0, "packets_sent": network.packets_sent 
if network else 0, "packets_recv": network.packets_recv 
if network else 0, "errin": network.errin 
if network else 0, "errout": network.errout 
if network else 0, "dropin": network.dropin 
if network else 0, "dropout": network.dropout 
if network else 0 } 
# GPU metrics (
if available) metrics["gpu"] = await self._get_gpu_metrics() 
# Temperature metrics (
if available) metrics["temperature"] = await self._get_temperature_metrics() 
return metrics 
def _get_load_average(self) -> Optional[Dict[str, float]]: 
"""
Get system load average. Returns: Load average dictionary or None 
if not available 
"""
 try: load_avg = psutil.getloadavg() 
return { "1min": load_avg[0], "5min": load_avg[1], "15min": load_avg[2] } 
except (AttributeError, OSError): 
return None async 
def _get_gpu_metrics(self) -> List[Dict[str, Any]]: 
"""
Get GPU metrics. Returns: List of GPU metric dictionaries 
"""
 gpu_metrics = [] try: 
import pynvml pynvml.nvmlInit() device_count = pynvml.nvmlDeviceGetCount() 
for i in range(device_count): handle = pynvml.nvmlDeviceGetHandleByIndex(i) gpu_data = { "index": i, "name": pynvml.nvmlDeviceGetName(handle).decode('utf-8'), "utilization": {}, "memory": {}, "temperature": None, "power": None } 
# Utilization try: utilization = pynvml.nvmlDeviceGetUtilizationRates(handle) gpu_data["utilization"] = { "gpu_percent": utilization.gpu, "memory_percent": utilization.memory } except: pass 
# Memory try: memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle) gpu_data["memory"] = { "total_gb": memory_info.total / (1024**3), "used_gb": memory_info.used / (1024**3), "free_gb": memory_info.free / (1024**3), "percent": (memory_info.used / memory_info.total) * 100 } except: pass 
# Temperature try: temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU) gpu_data["temperature"] = temp except: pass 
# Power try: power = pynvml.nvmlDeviceGetPowerUsage(handle) gpu_data["power"] = power / 1000.0 
# Convert mW to W except: pass gpu_metrics.append(gpu_data) pynvml.nvmlShutdown() 
except ImportError: pass 
# nvidia-ml-py3 not available 
except Exception as e: _logger.warning("failed_to_get_gpu_metrics", error=str(e)) 
return gpu_metrics async 
def _get_temperature_metrics(self) -> Dict[str, Any]: 
"""
Get temperature metrics. Returns: Temperature metrics dictionary 
"""
 temps = {} try: temp_sensors = psutil.sensors_temperatures() 
for name, entries in temp_sensors.items(): temps[name] = [] 
for entry in entries: temps[name].append({ "label": entry.label or "Unknown", "current": entry.current, "high": entry.high, "critical": entry.critical }) except: pass 
# Temperature sensors not available 
return temps 
def _calculate_averages(self) -> Dict[str, Any]: 
"""
Calculate average values 
from historical data. Returns: Dictionary 
with average values 
"""
 averages = {} 
if self._cpu_history: cpu_values = [cpu["percent"] 
for cpu in self._cpu_history] averages["cpu"] = { "percent": sum(cpu_values) / len(cpu_values), "frequency_mhz": sum(cpu["frequency_mhz"] 
for cpu in self._cpu_history 
if cpu["frequency_mhz"]) / len([cpu 
for cpu in self._cpu_history 
if cpu["frequency_mhz"]]) } 
if self._memory_history: memory_values = [mem["virtual"]["percent"] 
for mem in self._memory_history] averages["memory"] = { "virtual_percent": sum(memory_values) / len(memory_values) } 
if self._disk_history: disk_values = [disk["usage"]["percent"] 
for disk in self._disk_history] averages["disk"] = { "usage_percent": sum(disk_values) / len(disk_values) } 
return averages 
def _calculate_peaks(self) -> Dict[str, Any]: 
"""
Calculate peak values 
from historical data. Returns: Dictionary 
with peak values 
"""
 peaks = {} 
if self._cpu_history: cpu_values = [cpu["percent"] 
for cpu in self._cpu_history] peaks["cpu"] = { "percent": max(cpu_values) } 
if self._memory_history: memory_values = [mem["virtual"]["percent"] 
for mem in self._memory_history] peaks["memory"] = { "virtual_percent": max(memory_values) } 
if self._disk_history: disk_values = [disk["usage"]["percent"] 
for disk in self._disk_history] peaks["disk"] = { "usage_percent": max(disk_values) } 
return peaks 
def _get_history_data(self) -> Dict[str, Any]: 
"""
Get historical data as lists. Returns: Dictionary 
with historical data 
"""
 
return { "cpu": list(self._cpu_history), "memory": list(self._memory_history), "disk": list(self._disk_history), "network": list(self._network_history) } 
def _check_alerts(self) -> List[Dict[str, Any]]: 
"""
Check 
for alert conditions. Returns: List of alert dictionaries 
"""
 alerts = [] 
if not self._cpu_history: 
return alerts 
# Check CPU alerts current_cpu = self._cpu_history[-1]["percent"] 
if current_cpu > self._alert_thresholds["cpu_percent"]: alerts.append({ "type": "cpu_high", "severity": "warning", "message": f"High CPU usage: {current_cpu:.1f}%", "threshold": self._alert_thresholds["cpu_percent"], "timestamp": time.time() }) 
# Check memory alerts current_memory = self._memory_history[-1]["virtual"]["percent"] 
if current_memory > self._alert_thresholds["memory_percent"]: alerts.append({ "type": "memory_high", "severity": "warning", "message": f"High memory usage: {current_memory:.1f}%", "threshold": self._alert_thresholds["memory_percent"], "timestamp": time.time() }) 
# Check disk alerts current_disk = self._disk_history[-1]["usage"]["percent"] 
if current_disk > self._alert_thresholds["disk_percent"]: alerts.append({ "type": "disk_high", "severity": "critical", "message": f"High disk usage: {current_disk:.1f}%", "threshold": self._alert_thresholds["disk_percent"], "timestamp": time.time() }) 
# Check temperature alerts 
if hasattr(self, '_last_temperature_metrics'): 
for sensor_name, sensor_data in self._last_temperature_metrics.items(): 
for entry in sensor_data: 
if entry["current"] > self._alert_thresholds["temperature_celsius"]: alerts.append({ "type": "temperature_high", "severity": "warning", "message": f"High temperature: {sensor_name} - {entry['label']} {entry['current']}°C", "threshold": self._alert_thresholds["temperature_celsius"], "timestamp": time.time() }) 
return alerts 
def _clear_history(self) -> None: 
"""
Clear historical data.
"""
 self._cpu_history.clear() self._memory_history.clear() self._disk_history.clear() self._network_history.clear() 
def set_alert_thresholds(self, thresholds: Dict[str, float]) -> None: 
"""
Set alert thresholds. Args: thresholds: Dictionary of threshold values 
"""
 self._alert_thresholds.update(thresholds) 
def get_alert_thresholds(self) -> Dict[str, float]: 
"""
Get current alert thresholds. Returns: Dictionary of threshold values 
"""
 
return self._alert_thresholds.copy() 
def get_schema(self) -> Dict[str, Any]: 
"""
Get tool schema.
"""
 
return self._schema.dict()