"""gRPC performance profiler with detailed metrics collection.

Provides comprehensive profiling of gRPC operations including
latency analysis, resource usage, and performance bottlenecks.
"""

from __future__ import annotations

import time
import threading
import psutil
import traceback
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import statistics

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class ProfileLevel(Enum):
    """Profiling detail levels."""
    BASIC = "basic"
    DETAILED = "detailed"
    COMPREHENSIVE = "comprehensive"


@dataclass
class ProfileConfig:
    """Configuration for performance profiling."""
    
    # Profiling settings
    enabled: bool = True
    level: ProfileLevel = ProfileLevel.BASIC
    max_profiles: int = 10000
    sampling_rate: float = 1.0  # 0.0 to 1.0
    
    # Resource monitoring
    monitor_cpu: bool = True
    monitor_memory: bool = True
    monitor_io: bool = False
    monitor_network: bool = False
    
    # Performance thresholds
    slow_request_threshold_ms: float = 100.0
    error_request_threshold_ms: float = 500.0
    
    # Data retention
    retention_seconds: int = 3600  # 1 hour
    cleanup_interval_seconds: int = 300  # 5 minutes
    
    # System monitoring
    system_metrics_interval_seconds: float = 1.0
    max_system_metrics_samples: int = 3600  # 1 hour at 1s interval
    
    # Profiling overhead limits
    max_profiling_overhead_ms: float = 5.0
    max_memory_overhead_mb: int = 50
    
    # Stack trace settings
    collect_stack_traces: bool = False
    max_stack_depth: int = 10
    
    def should_profile(self) -> bool:
        """Determine if profiling should be performed."""
        if not self.enabled:
            return False
        
        # Random sampling based on rate
        import random
        return random.random() < self.sampling_rate
    
    def is_slow_request(self, duration_ms: float) -> bool:
        """Check if request is considered slow."""
        return duration_ms >= self.slow_request_threshold_ms


@dataclass
class PerformanceProfile:
    """Performance profile for a single operation."""
    
    # Basic metrics
    operation_id: str
    operation_type: str
    method: str
    start_time: float
    end_time: float
    duration_ms: float
    
    # Status and error information
    success: bool
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    
    # Request/Response information
    request_size_bytes: int = 0
    response_size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Resource usage
    cpu_percent: Optional[float] = None
    memory_mb: Optional[float] = None
    io_read_mb: Optional[float] = None
    io_write_mb: Optional[float] = None
    
    # Performance analysis
    is_slow: bool = False
    performance_score: float = 0.0  # 0-100, higher is better
    
    @property
    def timestamp(self) -> float:
        """Get profile timestamp."""
        return self.start_time
    
    @property
    def throughput_bps(self) -> float:
        """Calculate throughput in bytes per second."""
        if self.duration_ms == 0:
            return 0.0
        total_bytes = self.request_size_bytes + self.response_size_bytes
        return (total_bytes / self.duration_ms) * 1000


@dataclass
class SystemMetrics:
    """System resource metrics."""
    
    timestamp: float
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    disk_io_read_mb: Optional[float] = None
    disk_io_write_mb: Optional[float] = None
    network_io_recv_mb: Optional[float] = None
    network_io_sent_mb: Optional[float] = None
    active_connections: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp,
            'cpu_percent': self.cpu_percent,
            'memory_mb': self.memory_mb,
            'memory_percent': self.memory_percent,
            'disk_io_read_mb': self.disk_io_read_mb,
            'disk_io_write_mb': self.disk_io_write_mb,
            'network_io_recv_mb': self.network_io_recv_mb,
            'network_io_sent_mb': self.network_io_sent_mb,
            'active_connections': self.active_connections,
        }


class GrpcProfiler:
    """Main gRPC performance profiler."""
    
    def __init__(self, config: Optional[ProfileConfig] = None):
        self.config = config or ProfileConfig()
        self._profiles: deque[PerformanceProfile] = deque(maxlen=self.config.max_profiles)
        self._system_metrics: deque[SystemMetrics] = deque(maxlen=self.config.max_system_metrics_samples)
        self._active_profiles: Dict[str, PerformanceProfile] = {}
        
        # Statistics tracking
        self._stats = {
            'total_profiles': 0,
            'slow_requests': 0,
            'error_requests': 0,
            'profiling_overhead_ms': 0.0,
            'memory_overhead_mb': 0.0,
        }
        
        # Background monitoring
        self._monitoring_thread = None
        self._running = False
        self._lock = threading.RLock()
        
        # Performance analysis cache
        self._performance_analysis: Dict[str, Any] = {}
        self._last_analysis_time = 0.0
        
        _logger.info(
            "grpc_profiler_initialized",
            enabled=self.config.enabled,
            level=self.config.level.value,
            sampling_rate=self.config.sampling_rate
        )
    
    def start_profile(self, operation_id: str, operation_type: str, method: str,
                     request_size_bytes: int = 0, metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Start profiling an operation."""
        if not self.config.should_profile():
            return None
        
        profile_start_time = time.time()
        
        try:
            # Collect system metrics at start
            cpu_percent = psutil.cpu_percent() if self.config.monitor_cpu else None
            memory_info = psutil.virtual_memory() if self.config.monitor_memory else None
            memory_mb = memory_info.used / (1024 * 1024) if memory_info else None
            
            # Create profile
            profile = PerformanceProfile(
                operation_id=operation_id,
                operation_type=operation_type,
                method=method,
                start_time=profile_start_time,
                end_time=0.0,
                duration_ms=0.0,
                success=False,
                request_size_bytes=request_size_bytes,
                metadata=metadata or {},
                cpu_percent=cpu_percent,
                memory_mb=memory_mb
            )
            
            # Store active profile
            with self._lock:
                self._active_profiles[operation_id] = profile
            
            return operation_id
            
        except Exception as e:
            _logger.error("profile_start_failed", error=str(e))
            return None
    
    def end_profile(self, operation_id: str, success: bool = True,
                   response_size_bytes: int = 0, error_type: Optional[str] = None,
                   error_message: Optional[str] = None) -> Optional[PerformanceProfile]:
        """End profiling an operation."""
        profile_end_time = time.time()
        
        try:
            with self._lock:
                if operation_id not in self._active_profiles:
                    return None
                
                profile = self._active_profiles.pop(operation_id)
            
            # Update profile with completion data
            profile.end_time = profile_end_time
            profile.duration_ms = (profile_end_time - profile.start_time) * 1000
            profile.success = success
            profile.response_size_bytes = response_size_bytes
            profile.error_type = error_type
            profile.error_message = error_message
            
            # Collect final system metrics
            if self.config.monitor_cpu:
                profile.cpu_percent = psutil.cpu_percent()
            
            if self.config.monitor_memory:
                memory_info = psutil.virtual_memory()
                profile.memory_mb = memory_info.used / (1024 * 1024)
            
            # Determine if slow request
            profile.is_slow = self.config.is_slow_request(profile.duration_ms)
            
            # Calculate performance score
            profile.performance_score = self._calculate_performance_score(profile)
            
            # Collect stack trace for errors
            if not success and self.config.collect_stack_traces:
                profile.stack_trace = traceback.format_exc()
            
            # Store profile
            with self._lock:
                self._profiles.append(profile)
                self._stats['total_profiles'] += 1
                
                if profile.is_slow:
                    self._stats['slow_requests'] += 1
                
                if not success:
                    self._stats['error_requests'] += 1
            
            return profile
            
        except Exception as e:
            _logger.error("profile_end_failed", error=str(e))
            return None
    
    def get_profile(self, operation_id: str) -> Optional[PerformanceProfile]:
        """Get specific profile by ID."""
        with self._lock:
            # Check active profiles first
            if operation_id in self._active_profiles:
                return self._active_profiles[operation_id]
            
            # Check completed profiles
            for profile in reversed(self._profiles):
                if profile.operation_id == operation_id:
                    return profile
        
        return None
    
    def get_recent_profiles(self, limit: int = 100, 
                           operation_type: Optional[str] = None,
                           success_only: bool = False) -> List[PerformanceProfile]:
        """Get recent profiles with optional filtering."""
        with self._lock:
            profiles = list(self._profiles)
        
        # Apply filters
        if operation_type:
            profiles = [p for p in profiles if p.operation_type == operation_type]
        
        if success_only:
            profiles = [p for p in profiles if p.success]
        
        # Sort by timestamp and limit
        profiles.sort(key=lambda p: p.timestamp, reverse=True)
        return profiles[:limit]
    
    def get_performance_summary(self, time_window_seconds: float = 300.0) -> Dict[str, Any]:
        """Get performance summary for time window."""
        current_time = time.time()
        cutoff_time = current_time - time_window_seconds
        
        with self._lock:
            recent_profiles = [
                p for p in self._profiles 
                if p.timestamp >= cutoff_time
            ]
        
        if not recent_profiles:
            return {
                'time_window_seconds': time_window_seconds,
                'total_requests': 0,
                'avg_duration_ms': 0.0,
                'success_rate': 0.0,
                'slow_request_rate': 0.0,
            }
        
        # Calculate statistics
        durations = [p.duration_ms for p in recent_profiles]
        successful = [p for p in recent_profiles if p.success]
        slow_requests = [p for p in recent_profiles if p.is_slow]
        
        summary = {
            'time_window_seconds': time_window_seconds,
            'total_requests': len(recent_profiles),
            'successful_requests': len(successful),
            'slow_requests': len(slow_requests),
            'avg_duration_ms': statistics.mean(durations),
            'median_duration_ms': statistics.median(durations),
            'p95_duration_ms': self._percentile(durations, 95),
            'p99_duration_ms': self._percentile(durations, 99),
            'success_rate': (len(successful) / len(recent_profiles)) * 100,
            'slow_request_rate': (len(slow_requests) / len(recent_profiles)) * 100,
            'throughput_rps': len(recent_profiles) / time_window_seconds,
        }
        
        # Add operation type breakdown
        operation_stats = defaultdict(list)
        for profile in recent_profiles:
            operation_stats[profile.operation_type].append(profile.duration_ms)
        
        summary['operation_breakdown'] = {}
        for op_type, op_durations in operation_stats.items():
            summary['operation_breakdown'][op_type] = {
                'count': len(op_durations),
                'avg_duration_ms': statistics.mean(op_durations),
                'median_duration_ms': statistics.median(op_durations),
            }
        
        return summary
    
    def get_system_metrics(self, limit: int = 1000) -> List[SystemMetrics]:
        """Get recent system metrics."""
        with self._lock:
            return list(self._system_metrics)[-limit:]
    
    def get_profiling_stats(self) -> Dict[str, Any]:
        """Get profiling statistics."""
        with self._lock:
            total_requests = self._stats['total_profiles']
            
            stats = {
                'enabled': self.config.enabled,
                'level': self.config.level.value,
                'sampling_rate': self.config.sampling_rate,
                'total_profiles': self._stats['total_profiles'],
                'active_profiles': len(self._active_profiles),
                'stored_profiles': len(self._profiles),
                'slow_requests': self._stats['slow_requests'],
                'error_requests': self._stats['error_requests'],
                'profiling_overhead_ms': self._stats['profiling_overhead_ms'],
                'memory_overhead_mb': self._stats['memory_overhead_mb'],
            }
            
            if total_requests > 0:
                stats['slow_request_rate'] = (self._stats['slow_requests'] / total_requests) * 100
                stats['error_rate'] = (self._stats['error_requests'] / total_requests) * 100
            
            return stats
    
    def start_background_monitoring(self) -> None:
        """Start background system monitoring."""
        if self._running or not self.config.enabled:
            return
        
        import threading
        
        def monitoring_worker():
            self._running = True
            _logger.info("grpc_profiler_monitoring_started")
            
            while self._running:
                try:
                    self._collect_system_metrics()
                    time.sleep(self.config.system_metrics_interval_seconds)
                    
                except Exception as e:
                    _logger.error("profiler_monitoring_error", error=str(e))
                    time.sleep(self.config.system_metrics_interval_seconds)
        
        self._monitoring_thread = threading.Thread(target=monitoring_worker, daemon=True)
        self._monitoring_thread.start()
    
    def stop_background_monitoring(self) -> None:
        """Stop background system monitoring."""
        self._running = False
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5.0)
            _logger.info("grpc_profiler_monitoring_stopped")
    
    def cleanup_old_profiles(self) -> int:
        """Clean up old profiles beyond retention period."""
        current_time = time.time()
        cutoff_time = current_time - self.config.retention_seconds
        
        with self._lock:
            original_size = len(self._profiles)
            
            # Remove old profiles
            self._profiles = deque(
                (p for p in self._profiles if p.timestamp >= cutoff_time),
                maxlen=self.config.max_profiles
            )
            
            removed = original_size - len(self._profiles)
            
            if removed > 0:
                _logger.info("profiler_cleanup_completed", removed=removed)
        
        return removed
    
    def identify_performance_issues(self) -> List[Dict[str, Any]]:
        """Identify performance issues and bottlenecks."""
        issues = []
        
        with self._lock:
            profiles = list(self._profiles)
        
        if not profiles:
            return issues
        
        # Analyze slow requests
        slow_profiles = [p for p in profiles if p.is_slow]
        if len(slow_profiles) > len(profiles) * 0.1:  # More than 10% slow
            issues.append({
                'type': 'high_latency',
                'severity': 'high',
                'description': f'{len(slow_profiles)} slow requests detected',
                'slow_rate_percent': (len(slow_profiles) / len(profiles)) * 100,
                'avg_slow_duration_ms': statistics.mean([p.duration_ms for p in slow_profiles]),
            })
        
        # Analyze error rates
        error_profiles = [p for p in profiles if not p.success]
        if len(error_profiles) > len(profiles) * 0.05:  # More than 5% errors
            issues.append({
                'type': 'high_error_rate',
                'severity': 'high',
                'description': f'{len(error_profiles)} failed requests detected',
                'error_rate_percent': (len(error_profiles) / len(profiles)) * 100,
                'common_errors': self._get_common_errors(error_profiles),
            })
        
        # Analyze memory usage
        if self.config.monitor_memory:
            memory_profiles = [p for p in profiles if p.memory_mb is not None]
            if memory_profiles:
                avg_memory = statistics.mean([p.memory_mb for p in memory_profiles])
                max_memory = max([p.memory_mb for p in memory_profiles])
                
                if avg_memory > 1000:  # More than 1GB average
                    issues.append({
                        'type': 'high_memory_usage',
                        'severity': 'medium',
                        'description': f'High memory usage: {avg_memory:.1f}MB average',
                        'avg_memory_mb': avg_memory,
                        'max_memory_mb': max_memory,
                    })
        
        return issues
    
    def update_config(self, new_config: ProfileConfig) -> None:
        """Update profiler configuration."""
        self.config = new_config
        
        # Update deque limits
        self._profiles = deque(self._profiles, maxlen=new_config.max_profiles)
        self._system_metrics = deque(self._system_metrics, maxlen=new_config.max_system_metrics_samples)
        
        _logger.info("profiler_config_updated", enabled=new_config.enabled)
    
    def _calculate_performance_score(self, profile: PerformanceProfile) -> float:
        """Calculate performance score (0-100, higher is better)."""
        score = 100.0
        
        # Penalize slow requests
        if profile.is_slow:
            score -= 50.0
        
        # Penalize errors
        if not profile.success:
            score -= 80.0
        
        # Penalize high latency (beyond threshold)
        latency_penalty = min(profile.duration_ms / self.config.slow_request_threshold_ms - 1.0, 0.5) * 30
        score -= latency_penalty
        
        # Bonus for fast requests
        if profile.duration_ms < self.config.slow_request_threshold_ms * 0.5:
            score += 10.0
        
        return max(0.0, min(100.0, score))
    
    def _collect_system_metrics(self) -> None:
        """Collect system resource metrics."""
        try:
            timestamp = time.time()
            
            # CPU
            cpu_percent = psutil.cpu_percent()
            
            # Memory
            memory_info = psutil.virtual_memory()
            memory_mb = memory_info.used / (1024 * 1024)
            memory_percent = memory_info.percent
            
            # Disk I/O
            disk_io_read_mb = None
            disk_io_write_mb = None
            if self.config.monitor_io:
                disk_io = psutil.disk_io_counters()
                if disk_io:
                    disk_io_read_mb = disk_io.read_bytes / (1024 * 1024)
                    disk_io_write_mb = disk_io.write_bytes / (1024 * 1024)
            
            # Network I/O
            network_io_recv_mb = None
            network_io_sent_mb = None
            if self.config.monitor_network:
                net_io = psutil.net_io_counters()
                if net_io:
                    network_io_recv_mb = net_io.bytes_recv / (1024 * 1024)
                    network_io_sent_mb = net_io.bytes_sent / (1024 * 1024)
            
            metrics = SystemMetrics(
                timestamp=timestamp,
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                memory_percent=memory_percent,
                disk_io_read_mb=disk_io_read_mb,
                disk_io_write_mb=disk_io_write_mb,
                network_io_recv_mb=network_io_recv_mb,
                network_io_sent_mb=network_io_sent_mb,
            )
            
            with self._lock:
                self._system_metrics.append(metrics)
        
        except Exception as e:
            _logger.error("system_metrics_collection_failed", error=str(e))
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of data."""
        if not data:
            return 0.0
        return statistics.quantiles(data, n=100)[int(percentile) - 1] if percentile <= 100 else max(data)
    
    def _get_common_errors(self, error_profiles: List[PerformanceProfile]) -> List[Dict[str, Any]]:
        """Get common error types and messages."""
        error_counts = defaultdict(int)
        message_counts = defaultdict(int)
        
        for profile in error_profiles:
            if profile.error_type:
                error_counts[profile.error_type] += 1
            if profile.error_message:
                # Truncate long messages
                message = profile.error_message[:100]
                message_counts[message] += 1
        
        common_errors = []
        for error_type, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            common_errors.append({
                'error_type': error_type,
                'count': count,
                'percentage': (count / len(error_profiles)) * 100,
            })
        
        return common_errors
    
    def __del__(self):
        """Cleanup on deletion."""
        self.stop_background_monitoring()
