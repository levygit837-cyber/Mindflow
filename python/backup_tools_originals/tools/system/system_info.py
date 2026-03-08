"""
System information collection tools 
for MindFlow backend. Provides comprehensive system information gathering 
for local model recommendations and system optimization. 
"""
 
from __future__ 
import annotations 
import os 
import platform 
import psutil 
import asyncio 
from typing 
import Any, Dict, List, Optional, Union 
from pathlib 
import Path 
from mindflow_backend.infra.logging 
import get_logger 
from mindflow_backend.interfaces.tools.base 
import AsyncToolInterface 
from mindflow_backend.schemas.tools.tool_config 
import create_tool_schema 
from mindflow_backend.schemas.orchestration.orchestrator 
import AgentType _logger = get_logger(__name__) 
class SystemInfoCollector(AsyncToolInterface): 
"""
Tool 
for collecting comprehensive system information. Gathers hardware, software, and environment information to support local model recommendations and system optimization. 
"""
 
def __init__(self, backend: Optional[Any] = None): 
"""
Initialize the system info collector. Args: backend: Optional backend 
for compatibility 
"""
 super().__init__() self.backend = backend self.name = "system_info" self.description = "Collect comprehensive system information 
for model recommendations" self._schema = create_tool_schema( name=self.name, description=self.description, category="system", parameters=[ { "name": "include_detailed", "type": "boolean", "description": "Include detailed hardware information", "required": False, "default": False }, { "name": "include_performance", "type": "boolean", "description": "Include performance benchmarks", "required": False, "default": False } ], returns={ "type": "object", "description": "System information", "properties": { "cpu_info": {"type": "object", "description": "CPU information"}, "memory_info": {"type": "object", "description": "Memory information"}, "gpu_info": {"type": "array", "description": "GPU information"}, "disk_info": {"type": "object", "description": "Disk information"}, "os_info": {"type": "object", "description": "Operating system information"}, "python_info": {"type": "object", "description": "Python environment information"}, "recommendations": {"type": "object", "description": "System recommendations"} } } ) async 
def execute(self, **kwargs) -> Dict[str, Any]: 
"""
Collect comprehensive system information. Args: include_detailed: Include detailed hardware information include_performance: Include performance benchmarks Returns: Dictionary 
with system information 
"""
 try: include_detailed = kwargs.get("include_detailed", False) include_performance = kwargs.get("include_performance", False) system_info = {} 
# CPU Information system_info["cpu_info"] = await self._get_cpu_info(include_detailed) 
# Memory Information system_info["memory_info"] = await self._get_memory_info() 
# GPU Information system_info["gpu_info"] = await self._get_gpu_info(include_detailed) 
# Disk Information system_info["disk_info"] = await self._get_disk_info() 
# OS Information system_info["os_info"] = await self._get_os_info() 
# Python Environment Information system_info["python_info"] = await self._get_python_info() 
# Performance Benchmarks (
if requested) 
if include_performance: system_info["performance"] = await self._run_performance_benchmarks() 
# Generate Recommendations system_info["recommendations"] = await self._generate_recommendations(system_info) 
return self._format_result( success=True, result=system_info ) 
except Exception as e: 
return self._format_result( success=False, error=f"Failed to collect system information: {str(e)}" ) async 
def _get_cpu_info(self, detailed: bool = False) -> Dict[str, Any]: 
"""
Get CPU information. Args: detailed: Include detailed CPU information Returns: CPU information dictionary 
"""
 cpu_info = { "brand": platform.processor(), "architecture": platform.architecture()[0], "machine": platform.machine(), "cores_physical": psutil.cpu_count(logical=False), "cores_logical": psutil.cpu_count(logical=True), "frequency_max_mhz": psutil.cpu_freq().max 
if psutil.cpu_freq() else None, "usage_percent": psutil.cpu_percent(interval=1) } 
if detailed: 
# Add more detailed CPU information cpu_freq = psutil.cpu_freq() 
if cpu_freq: cpu_info.update({ "frequency_current_mhz": cpu_freq.current, "frequency_min_mhz": cpu_freq.min }) 
# CPU usage per core cpu_info["usage_per_core"] = psutil.cpu_percent(percpu=True) 
# Load averages (Unix-like systems) try: load_avg = os.getloadavg() cpu_info["load_average"] = { "1min": load_avg[0], "5min": load_avg[1], "15min": load_avg[2] } 
except (AttributeError, OSError): pass 
# Not available on Windows 
return cpu_info async 
def _get_memory_info(self) -> Dict[str, Any]: 
"""
Get memory information. Returns: Memory information dictionary 
"""
 virtual_memory = psutil.virtual_memory() swap_memory = psutil.swap_memory() 
return { "total_gb": virtual_memory.total / (1024**3), "available_gb": virtual_memory.available / (1024**3), "used_gb": virtual_memory.used / (1024**3), "free_gb": virtual_memory.free / (1024**3), "usage_percent": virtual_memory.percent, "swap_total_gb": swap_memory.total / (1024**3), "swap_used_gb": swap_memory.used / (1024**3), "swap_free_gb": swap_memory.free / (1024**3), "swap_usage_percent": swap_memory.percent } async 
def _get_gpu_info(self, detailed: bool = False) -> List[Dict[str, Any]]: 
"""
Get GPU information. Args: detailed: Include detailed GPU information Returns: List of GPU information dictionaries 
"""
 gpu_info = [] try: 
# Try to get GPU information using nvidia-ml-py3 
import pynvml pynvml.nvmlInit() device_count = pynvml.nvmlDeviceGetCount() 
for i in range(device_count): handle = pynvml.nvmlDeviceGetHandleByIndex(i) 
# Basic GPU info gpu_data = { "index": i, "name": pynvml.nvmlDeviceGetName(handle).decode('utf-8'), "driver_version": pynvml.nvmlSystemGetDriverVersion().decode('utf-8') } 
# Memory info try: memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle) gpu_data.update({ "memory_total_gb": memory_info.total / (1024**3), "memory_free_gb": memory_info.free / (1024**3), "memory_used_gb": memory_info.used / (1024**3) }) except: pass 
if detailed: 
# Temperature and utilization try: temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU) gpu_data["temperature_celsius"] = temp except: pass try: utilization = pynvml.nvmlDeviceGetUtilizationRates(handle) gpu_data.update({ "utilization_gpu_percent": utilization.gpu, "utilization_memory_percent": utilization.memory }) except: pass 
# Power usage try: power = pynvml.nvmlDeviceGetPowerUsage(handle) gpu_data["power_usage_watts"] = power / 1000.0 
# Convert mW to W except: pass gpu_info.append(gpu_data) pynvml.nvmlShutdown() 
except ImportError: 
# nvidia-ml-py3 not available, try alternative methods try: 
# Try to get GPU info 
from other sources 
import subprocess result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu', '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=10) 
if result.returncode == 0: lines = result.stdout.strip().split('\n') 
for i, line in enumerate(lines): parts = [part.strip() 
for part in line.split(',')] 
if len(parts) >= 5: gpu_data = { "index": i, "name": parts[0], "memory_total_gb": float(parts[1]) / 1024, "memory_used_gb": float(parts[2]) / 1024, "memory_free_gb": float(parts[3]) / 1024, "utilization_gpu_percent": float(parts[4]), "temperature_celsius": float(parts[5]) 
if len(parts) > 5 else None } gpu_info.append(gpu_data) except: pass 
# GPU info not available 
except Exception as e: _logger.warning("failed_to_get_gpu_info", error=str(e)) 
return gpu_info async 
def _get_disk_info(self) -> Dict[str, Any]: 
"""
Get disk information. Returns: Disk information dictionary 
"""
 disk_usage = psutil.disk_usage('/') 
# Get disk I/O statistics try: disk_io = psutil.disk_io_counters() io_info = { "read_bytes": disk_io.read_bytes, "write_bytes": disk_io.write_bytes, "read_count": disk_io.read_count, "write_count": disk_io.write_count } except: io_info = {} 
return { "total_gb": disk_usage.total / (1024**3), "used_gb": disk_usage.used / (1024**3), "free_gb": disk_usage.free / (1024**3), "usage_percent": (disk_usage.used / disk_usage.total) * 100, "io_stats": io_info } async 
def _get_os_info(self) -> Dict[str, Any]: 
"""
Get operating system information. Returns: OS information dictionary 
"""
 
return { "system": platform.system(), "release": platform.release(), "version": platform.version(), "machine": platform.machine(), "processor": platform.processor(), "hostname": platform.node(), "platform": platform.platform(), "uptime_seconds": int(time.time() - psutil.boot_time()) 
if hasattr(psutil, 'boot_time') else None } async 
def _get_python_info(self) -> Dict[str, Any]: 
"""
Get Python environment information. Returns: Python environment information dictionary 
"""
 
import sys 
import site 
from pathlib 
import Path 
return { "version": sys.version, "version_info": { "major": sys.version_info.major, "minor": sys.version_info.minor, "micro": sys.version_info.micro, "releaselevel": sys.version_info.releaselevel }, "executable": sys.executable, "path": sys.path[:5], 
# First 5 entries "prefix": sys.prefix, "base_prefix": getattr(sys, 'base_prefix', None), "site_packages": site.getsitepackages()[:3] 
if hasattr(site, 'getsitepackages') else [], "virtual_env": os.getenv('VIRTUAL_ENV'), "conda_env": os.getenv('CONDA_DEFAULT_ENV') } async 
def _run_performance_benchmarks(self) -> Dict[str, Any]: 
"""
Run basic performance benchmarks. Returns: Performance benchmark results 
"""
 benchmarks = {} 
# CPU benchmark (simple calculation) 
import time start_time = time.time() 
# Simple CPU-intensive task result = sum(i * i 
for i in range(1000000)) cpu_time = time.time() - start_time benchmarks["cpu_benchmark"] = { "calculation_time_seconds": cpu_time, "result_check": result > 0 
# Basic validation } 
# Memory benchmark (list operations) start_time = time.time() test_list = [] 
for i in range(100000): test_list.append(i) memory_time = time.time() - start_time benchmarks["memory_benchmark"] = { "list_creation_time_seconds": memory_time, "list_length": len(test_list) } 
# I/O benchmark (file operations) 
import tempfile start_time = time.time() 
with tempfile.NamedTemporaryFile(delete=False) as tmp: tmp_path = tmp.name try: 
# Write test 
with open(tmp_path, 'w') as f: f.write("test" * 10000) 
# Read test 
with open(tmp_path, 'r') as f: content = f.read() io_time = time.time() - start_time benchmarks["io_benchmark"] = { "file_operations_time_seconds": io_time, "content_size": len(content) } 
finally: os.unlink(tmp_path) 
return benchmarks async 
def _generate_recommendations(self, system_info: Dict[str, Any]) -> Dict[str, Any]: 
"""
Generate system recommendations based on collected information. Args: system_info: Collected system information Returns: System recommendations dictionary 
"""
 recommendations = { "model_recommendations": [], "system_optimizations": [], "warnings": [] } cpu_info = system_info.get("cpu_info", {}) memory_info = system_info.get("memory_info", {}) gpu_info = system_info.get("gpu_info", []) disk_info = system_info.get("disk_info", {}) 
# Model recommendations based on hardware 
if gpu_info: 
# GPU available - can run larger models 
for gpu in gpu_info: gpu_memory = gpu.get("memory_total_gb", 0) 
if gpu_memory >= 24: recommendations["model_recommendations"].append({ "category": "large_language_models", "models": ["llama-70b", "mixtral-8x7b", "codellama-34b"], "reasoning": f"GPU 
with {gpu_memory:.1f}GB memory can handle large models" }) el
if gpu_memory >= 12: recommendations["model_recommendations"].append({ "category": "medium_language_models", "models": ["llama-13b", "mistral-7b", "codellama-13b"], "reasoning": f"GPU 
with {gpu_memory:.1f}GB memory suitable 
for medium models" }) el
if gpu_memory >= 6: recommendations["model_recommendations"].append({ "category": "small_language_models", "models": ["llama-7b", "phi-2", "gpt-2"], "reasoning": f"GPU 
with {gpu_memory:.1f}GB memory 
for small models" }) 
else: 
# CPU-only inference available_memory = memory_info.get("available_gb", 0) 
if available_memory >= 16: recommendations["model_recommendations"].append({ "category": "cpu_models", "models": ["llama-7b-4bit", "phi-2", "gpt-2-small"], "reasoning": f"{available_memory:.1f}GB available memory 
for CPU inference" }) el
if available_memory >= 8: recommendations["model_recommendations"].append({ "category": "lightweight_models", "models": ["phi-1.5", "gpt-2-xs", "tinyllama"], "reasoning": f"{available_memory:.1f}GB available memory 
for lightweight models" }) 
# System optimizations cpu_cores = cpu_info.get("cores_logical", 0) 
if cpu_cores >= 8: recommendations["system_optimizations"].append({ "category": "parallel_processing", "suggestion": "Enable parallel processing and multi-threading", "reasoning": f"{cpu_cores} CPU cores available" }) 
# Memory usage warnings memory_usage = memory_info.get("usage_percent", 0) 
if memory_usage > 80: recommendations["warnings"].append({ "category": "memory", "message": f"High memory usage: {memory_usage:.1f}%", "suggestion": "Consider closing unnecessary applications" }) 
# Disk space warnings disk_usage = disk_info.get("usage_percent", 0) 
if disk_usage > 85: recommendations["warnings"].append({ "category": "disk", "message": f"Low disk space: {disk_usage:.1f}% used", "suggestion": "Consider cleaning up disk space" }) 
return recommendations 
def get_schema(self) -> Dict[str, Any]: 
"""
Get tool schema.
"""
 
return self._schema.dict()