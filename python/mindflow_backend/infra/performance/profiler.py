"""Advanced performance profiler with detailed analysis.

Provides comprehensive profiling capabilities including
function profiling, memory profiling, and performance analysis.
"""

from __future__ import annotations

import asyncio
import time
import tracemalloc
import cProfile
import pstats
import io
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime, UTC, timedelta
from enum import Enum
import json
import weakref
import threading
from collections import defaultdict

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.infra.tracing.tracer import get_tracer, SpanKind

_logger = get_logger(__name__)


class ProfileType(Enum):
    """Profile types."""
    FUNCTION = "function"
    MEMORY = "memory"
    CPU = "cpu"
    ASYNC = "async"
    DATABASE = "database"
    CACHE = "cache"


@dataclass
class ProfileData:
    """Profile data with metrics."""
    name: str
    type: ProfileType
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    call_count: int = 1
    total_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    min_time_ms: float = float('inf')
    max_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    peak_memory_mb: float = 0.0
    cpu_percent: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def update_metrics(self, duration_ms: float) -> None:
        """Update profile metrics.
        
        Args:
            duration_ms: Duration in milliseconds
        """
        self.call_count += 1
        self.total_time_ms += duration_ms
        self.avg_time_ms = self.total_time_ms / self.call_count
        self.min_time_ms = min(self.min_time_ms, duration_ms)
        self.max_time_ms = max(self.max_time_ms, duration_ms)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.type.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "call_count": self.call_count,
            "total_time_ms": self.total_time_ms,
            "avg_time_ms": self.avg_time_ms,
            "min_time_ms": self.min_time_ms if self.min_time_ms != float('inf') else 0.0,
            "max_time_ms": self.max_time_ms,
            "memory_usage_mb": self.memory_usage_mb,
            "peak_memory_mb": self.peak_memory_mb,
            "cpu_percent": self.cpu_percent,
            "metadata": self.metadata,
        }


class MemoryProfiler:
    """Memory profiling utilities."""
    
    def __init__(self):
        """Initialize memory profiler."""
        self._snapshots: List[Dict[str, Any]] = []
        self._is_profiling = False
        
    def start_profiling(self) -> None:
        """Start memory profiling."""
        if self._is_profiling:
            return
            
        tracemalloc.start()
        self._is_profiling = True
        
        # Take initial snapshot
        snapshot = tracemalloc.take_snapshot()
        self._snapshots.append({
            "timestamp": datetime.now(UTC),
            "snapshot": snapshot,
            "total_objects": snapshot.total,
            "total_size": snapshot.size,
            "type": "initial",
        })
        
        _logger.debug("memory_profiling_started")
        
    def stop_profiling(self) -> Dict[str, Any]:
        """Stop memory profiling and return results.
        
        Returns:
            Memory profiling results
        """
        if not self._is_profiling:
            return {}
            
        # Take final snapshot
        final_snapshot = tracemalloc.take_snapshot()
        self._snapshots.append({
            "timestamp": datetime.now(UTC),
            "snapshot": final_snapshot,
            "total_objects": final_snapshot.total,
            "total_size": final_snapshot.size,
            "type": "final",
        })
        
        # Calculate differences
        if len(self._snapshots) >= 2:
            initial = self._snapshots[0]
            final = self._snapshots[-1]
            
            diff = final["snapshot"].compare_to(initial["snapshot"])
            
            results = {
                "initial_objects": initial["total_objects"],
                "initial_size_mb": initial["total_size"] / (1024 * 1024),
                "final_objects": final["total_objects"],
                "final_size_mb": final["total_size"] / (1024 * 1024),
                "objects_added": len(diff),
                "size_added_mb": sum(stat.size_diff for stat in diff) / (1024 * 1024),
                "top_allocations": [
                    {
                        "object_type": stat.traceback.get_frame(0).name,
                        "size_diff": stat.size_diff / (1024 * 1024),
                        "count_diff": stat.count_diff,
                    }
                    for stat in sorted(diff, key=lambda x: x.size_diff, reverse=True)[:10]
                ],
            }
        else:
            results = {}
            
        tracemalloc.stop()
        self._is_profiling = False
        
        _logger.debug("memory_profiling_stopped", results=results)
        return results
        
    def get_current_usage(self) -> Dict[str, Any]:
        """Get current memory usage.
        
        Returns:
            Current memory usage statistics
        """
        snapshot = tracemalloc.take_snapshot()
        
        return {
            "total_objects": snapshot.total,
            "total_size_mb": snapshot.size / (1024 * 1024),
            "timestamp": datetime.now(UTC).isoformat(),
        }


class CPUProfiler:
    """CPU profiling utilities."""
    
    def __init__(self):
        """Initialize CPU profiler."""
        self._profiles: Dict[str, ProfileData] = {}
        self._current_profile: Optional[cProfile.Profile] = None
        
    @contextmanager
    def profile_function(self, name: str) -> Any:
        """Profile a synchronous function.
        
        Args:
            name: Profile name
            
        Yields:
            Profile context
        """
        profiler = cProfile.Profile()
        
        try:
            profiler.enable()
            yield profiler
        finally:
            profiler.disable()
            
            # Process results
            stats = pstats.Stats(profiler)
            profile_data = self._process_stats(name, stats)
            
            self._profiles[name] = profile_data
            
    def _process_stats(self, name: str, stats: pstats.Stats) -> ProfileData:
        """Process profiling statistics.
        
        Args:
            name: Profile name
            stats: Profiling statistics
            
        Returns:
            Profile data
        """
        # Get total time
        total_time = stats.total_tt
        
        # Get function statistics
        func_stats = {}
        for func_info, func_stat in stats.stats.items():
            func_name = func_info[2] if len(func_info) > 2 else str(func_info)
            func_stats[func_name] = {
                "calls": func_stat[0],
                "total_time": func_stat[2],
                "cumulative_time": func_stat[3],
                "per_call": func_stat[4] if func_stat[0] > 0 else 0,
            }
            
        # Find the main function
        main_func_stats = func_stats.get(name, {"calls": 0, "total_time": 0})
        
        return ProfileData(
            name=name,
            type=ProfileType.CPU,
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC),
            duration_ms=total_time * 1000,
            call_count=main_func_stats["calls"],
            total_time_ms=total_time * 1000,
            avg_time_ms=main_func_stats["per_call"] * 1000,
            min_time_ms=0.0,
            max_time_ms=0.0,
            metadata={
                "function_stats": func_stats,
                "total_cpu_time": total_time,
            }
        )


class AsyncProfiler:
    """Async function profiler."""
    
    def __init__(self):
        """Initialize async profiler."""
        self._profiles: Dict[str, ProfileData] = {}
        
    @asynccontextmanager
    async def profile_async_function(self, name: str) -> Any:
        """Profile an async function.
        
        Args:
            name: Profile name
            
        Yields:
            Profile context
        """
        start_time = time.time()
        
        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            
            # Update or create profile data
            if name in self._profiles:
                self._profiles[name].update_metrics(duration_ms)
                self._profiles[name].end_time = datetime.now(UTC)
                self._profiles[name].duration_ms = duration_ms
            else:
                self._profiles[name] = ProfileData(
                    name=name,
                    type=ProfileType.ASYNC,
                    start_time=datetime.now(UTC),
                    end_time=datetime.now(UTC),
                    duration_ms=duration_ms,
                    call_count=1,
                    total_time_ms=duration_ms,
                    avg_time_ms=duration_ms,
                    min_time_ms=duration_ms,
                    max_time_ms=duration_ms,
                )
                
            _logger.debug("async_function_profiled", name=name, duration_ms=duration_ms)


class PerformanceProfiler:
    """Advanced performance profiler with comprehensive capabilities.
    
    Features:
    - Function profiling (sync and async)
    - Memory profiling
    - CPU profiling
    - Database query profiling
    - Cache performance profiling
    - Performance analysis and recommendations
    """
    
    def __init__(self):
        """Initialize performance profiler."""
        self._profiles: Dict[str, ProfileData] = {}
        self._memory_profiler = MemoryProfiler()
        self._cpu_profiler = CPUProfiler()
        self._async_profiler = AsyncProfiler()
        self._tracer = get_tracer()
        self._is_initialized = False
        
        # Configuration
        self._enabled = True
        self._max_profiles = 1000
        self._profile_retention_hours = 24
        
        # Statistics
        self._stats = {
            "total_profiles": 0,
            "function_profiles": 0,
            "memory_profiles": 0,
            "cpu_profiles": 0,
            "async_profiles": 0,
            "avg_profile_duration_ms": 0.0,
            "slow_functions": [],
        }
        
    async def initialize(self) -> None:
        """Initialize performance profiler."""
        await self._tracer.initialize()
        self._is_initialized = True
        
        _logger.info(
            "performance_profiler_initialized",
            enabled=self._enabled,
            max_profiles=self._max_profiles,
            retention_hours=self._profile_retention_hours,
        )
        
    @contextmanager
    def profile_function(
        self,
        name: str,
        profile_type: ProfileType = ProfileType.FUNCTION,
        include_memory: bool = False,
        include_cpu: bool = False
    ) -> Any:
        """Profile a function with multiple profiling types.
        
        Args:
            name: Profile name
            profile_type: Profile type
            include_memory: Include memory profiling
            include_cpu: Include CPU profiling
            
        Yields:
            Profile context
        """
        if not self._is_initialized or not self._enabled:
            yield
            return
            
        start_time = time.time()
        
        # Start memory profiling if requested
        if include_memory:
            self._memory_profiler.start_profiling()
            
        # Start CPU profiling if requested
        if include_cpu:
            cpu_context = self._cpu_profiler.profile_function(name)
        else:
            cpu_context = None
            
        try:
            if cpu_context:
                with cpu_context:
                    yield
            else:
                yield
        finally:
            # Stop profiling
            if include_memory:
                memory_results = self._memory_profiler.stop_profiling()
                self._store_memory_profile(name, memory_results)
                
            # Update function profile
            duration_ms = (time.time() - start_time) * 1000
            self._update_function_profile(name, duration_ms, profile_type)
            
            self._stats["total_profiles"] += 1
            
    @asynccontextmanager
    async def profile_async_function(
        self,
        name: str,
        include_memory: bool = False
    ) -> Any:
        """Profile an async function.
        
        Args:
            name: Profile name
            include_memory: Include memory profiling
            
        Yields:
            Profile context
        """
        if not self._is_initialized or not self._enabled:
            yield
            return
            
        start_time = time.time()
        
        # Start memory profiling if requested
        if include_memory:
            self._memory_profiler.start_profiling()
            
        try:
            async with self._async_profiler.profile_async_function(name):
                yield
        finally:
            # Stop profiling
            if include_memory:
                memory_results = self._memory_profiler.stop_profiling()
                self._store_memory_profile(name, memory_results)
                
            # Update statistics
            duration_ms = (time.time() - start_time) * 1000
            self._stats["total_profiles"] += 1
            self._stats["async_profiles"] += 1
            
            # Update average duration
            current_avg = self._stats["avg_profile_duration_ms"]
            count = self._stats["total_profiles"]
            self._stats["avg_profile_duration_ms"] = (current_avg * (count - 1) + duration_ms) / count
            
            # Track slow functions
            if duration_ms > 1000:  # > 1 second
                self._stats["slow_functions"].append({
                    "name": name,
                    "duration_ms": duration_ms,
                    "timestamp": datetime.now(UTC).isoformat(),
                })
                
    def _update_function_profile(self, name: str, duration_ms: float, profile_type: ProfileType) -> None:
        """Update function profile data.
        
        Args:
            name: Profile name
            duration_ms: Duration in milliseconds
            profile_type: Profile type
        """
        if name in self._profiles:
            self._profiles[name].update_metrics(duration_ms)
            self._profiles[name].end_time = datetime.now(UTC)
            self._profiles[name].duration_ms = duration_ms
        else:
            self._profiles[name] = ProfileData(
                name=name,
                type=profile_type,
                start_time=datetime.now(UTC),
                end_time=datetime.now(UTC),
                duration_ms=duration_ms,
                call_count=1,
                total_time_ms=duration_ms,
                avg_time_ms=duration_ms,
                min_time_ms=duration_ms,
                max_time_ms=duration_ms,
            )
            
        self._stats["function_profiles"] += 1
        
    def _store_memory_profile(self, name: str, results: Dict[str, Any]) -> None:
        """Store memory profile results.
        
        Args:
            name: Profile name
            results: Memory profiling results
        """
        if name in self._profiles:
            self._profiles[name].memory_usage_mb = results.get("final_size_mb", 0.0)
            self._profiles[name].peak_memory_mb = results.get("final_size_mb", 0.0)
            self._profiles[name].metadata["memory_results"] = results
            
    def get_profile(self, name: str) -> Optional[ProfileData]:
        """Get profile by name.
        
        Args:
            name: Profile name
            
        Returns:
            Profile data or None
        """
        return self._profiles.get(name)
        
    def get_all_profiles(self) -> Dict[str, ProfileData]:
        """Get all profiles.
        
        Returns:
            All profile data
        """
        return self._profiles.copy()
        
    def get_slow_functions(self, threshold_ms: float = 1000.0, limit: int = 10) -> List[Dict[str, Any]]:
        """Get slow functions above threshold.
        
        Args:
            threshold_ms: Duration threshold in milliseconds
            limit: Maximum number of results
            
        Returns:
            List of slow functions
        """
        slow_functions = []
        
        for profile in self._profiles.values():
            if profile.avg_time_ms >= threshold_ms:
                slow_functions.append({
                    "name": profile.name,
                    "type": profile.type.value,
                    "avg_time_ms": profile.avg_time_ms,
                    "max_time_ms": profile.max_time_ms,
                    "call_count": profile.call_count,
                    "total_time_ms": profile.total_time_ms,
                })
                
        # Sort by average time
        slow_functions.sort(key=lambda x: x["avg_time_ms"], reverse=True)
        
        return slow_functions[:limit]
        
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get current memory usage.
        
        Returns:
            Memory usage statistics
        """
        return self._memory_profiler.get_current_usage()
        
    def analyze_performance(self) -> Dict[str, Any]:
        """Analyze performance and provide recommendations.
        
        Returns:
            Performance analysis results
        """
        if not self._profiles:
            return {
                "status": "no_data",
                "recommendations": ["Start profiling to collect performance data"],
            }
            
        # Calculate statistics
        total_profiles = len(self._profiles)
        slow_functions = self.get_slow_functions(500.0)
        
        # Find performance issues
        issues = []
        recommendations = []
        
        # Check for slow functions
        if slow_functions:
            issues.append(f"Found {len(slow_functions)} slow functions (>500ms avg)")
            recommendations.append("Optimize slow functions or add caching")
            
        # Check for high memory usage
        memory_usage = self.get_memory_usage()
        if memory_usage.get("total_size_mb", 0) > 1000:  # > 1GB
            issues.append(f"High memory usage: {memory_usage['total_size_mb']:.1f}MB")
            recommendations.append("Investigate memory leaks or optimize data structures")
            
        # Check for frequently called functions
        high_call_functions = [
            profile for profile in self._profiles.values()
            if profile.call_count > 1000
        ]
        
        if high_call_functions:
            issues.append(f"Found {len(high_call_functions)} frequently called functions")
            recommendations.append("Consider caching or optimizing frequently called functions")
            
        return {
            "status": "analyzed",
            "total_profiles": total_profiles,
            "slow_functions_count": len(slow_functions),
            "memory_usage_mb": memory_usage.get("total_size_mb", 0),
            "issues": issues,
            "recommendations": recommendations,
            "slow_functions": slow_functions[:5],
            "frequent_functions": [
                {"name": f.name, "calls": f.call_count}
                for f in high_call_functions[:5]
            ],
        }
        
    def cleanup_old_profiles(self) -> int:
        """Clean up old profiles.
        
        Returns:
            Number of profiles cleaned up
        """
        cutoff_time = datetime.now(UTC) - timedelta(hours=self._profile_retention_hours)
        
        profiles_to_remove = []
        for name, profile in self._profiles.items():
            if profile.start_time < cutoff_time:
                profiles_to_remove.append(name)
                
        for name in profiles_to_remove:
            del self._profiles[name]
            
        if profiles_to_remove:
            _logger.info("old_profiles_cleaned", count=len(profiles_to_remove))
            
        return len(profiles_to_remove)
        
    def get_stats(self) -> Dict[str, Any]:
        """Get profiler statistics.
        
        Returns:
            Statistics dictionary
        """
        stats = self._stats.copy()
        
        # Add profile counts
        stats["profile_count"] = len(self._profiles)
        stats["profile_types"] = {
            profile_type.value: sum(1 for p in self._profiles.values() if p.type == profile_type)
            for profile_type in ProfileType
        }
        
        return stats
        
    async def health_check(self) -> Dict[str, Any]:
        """Perform profiler health check.
        
        Returns:
            Health check results
        """
        try:
            start_time = time.time()
            
            # Test profiling functionality
            with self.profile_function("health_check", ProfileType.FUNCTION):
                time.sleep(0.001)  # Small delay
                
            duration_ms = (time.time() - start_time) * 1000
            
            health_data = {
                "status": "healthy",
                "profiling_enabled": self._enabled,
                "profile_count": len(self._profiles),
                "test_profile_created": True,
                "duration_ms": duration_ms,
                "memory_usage_mb": self.get_memory_usage().get("total_size_mb", 0),
                "timestamp": datetime.now(UTC).isoformat(),
            }
            
            _logger.info("performance_profiler_health_check_success", **health_data)
            return health_data
            
        except Exception as e:
            error_data = {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }
            
            _logger.error("performance_profiler_health_check_failed", **error_data)
            return error_data


# Global performance profiler instance
_performance_profiler: Optional[PerformanceProfiler] = None


def get_profiler() -> PerformanceProfiler:
    """Get global performance profiler instance.
    
    Returns:
        PerformanceProfiler instance
    """
    global _performance_profiler
    if _performance_profiler is None:
        _performance_profiler = PerformanceProfiler()
    return _performance_profiler


# Convenience decorators
def profile_function(
    name: Optional[str] = None,
    profile_type: ProfileType = ProfileType.FUNCTION,
    include_memory: bool = False,
    include_cpu: bool = False
):
    """Decorator to profile function execution.
    
    Args:
        name: Profile name (function name if None)
        profile_type: Profile type
        include_memory: Include memory profiling
        include_cpu: Include CPU profiling
        
    Returns:
        Decorated function
    """
    def decorator(func):
        def sync_wrapper(*args, **kwargs):
            profiler = get_profiler()
            profile_name = name or f"{func.__module__}.{func.__name__}"
            
            with profiler.profile_function(profile_name, profile_type, include_memory, include_cpu):
                return func(*args, **kwargs)
                
        async def async_wrapper(*args, **kwargs):
            profiler = get_profiler()
            profile_name = name or f"{func.__module__}.{func.__name__}"
            
            async with profiler.profile_async_function(profile_name, include_memory):
                return await func(*args, **kwargs)
                
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator
