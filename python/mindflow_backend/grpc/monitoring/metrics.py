"""gRPC metrics collection and aggregation.

Collects and aggregates metrics for gRPC services including request latency,
throughput, error rates, connection metrics, and business-specific metrics.
"""

from __future__ import annotations

import time
import threading
from collections import defaultdict, deque
from typing import Any, Dict, List
from dataclasses import dataclass, field
from enum import Enum

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class MetricType(Enum):
    """Types of metrics supported."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricValue:
    """Single metric value with timestamp."""
    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class HistogramBucket:
    """Histogram bucket for latency metrics."""
    upper_bound: float
    count: int = 0


class GrpcMetricsCollector:
    """Comprehensive metrics collector for gRPC services."""
    
    def __init__(self, max_history_size: int = 1000):
        self.max_history_size = max_history_size
        self._lock = threading.RLock()
        
        # Request metrics
        self.request_count: Dict[str, float] = defaultdict(float)
        self.request_duration: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history_size))
        self.request_errors: Dict[str, float] = defaultdict(float)
        
        # Connection metrics
        self.active_connections: Dict[str, float] = defaultdict(float)
        self.connection_errors: Dict[str, float] = defaultdict(float)
        self.connection_duration: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history_size))
        
        # System metrics
        self.cpu_usage: deque = deque(maxlen=max_history_size)
        self.memory_usage: deque = deque(maxlen=max_history_size)
        self.network_io: deque = deque(maxlen=max_history_size)
        
        # Business metrics
        self.chat_requests_per_second: deque = deque(maxlen=60)  # Last 60 seconds
        self.session_duration: deque = deque(maxlen=max_history_size)
        self.agent_performance: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history_size))
        
        # Histogram buckets for latency (in seconds)
        self.latency_buckets = [
            HistogramBucket(0.001),   # < 1ms
            HistogramBucket(0.005),   # < 5ms
            HistogramBucket(0.01),    # < 10ms
            HistogramBucket(0.025),   # < 25ms
            HistogramBucket(0.05),    # < 50ms
            HistogramBucket(0.1),     # < 100ms
            HistogramBucket(0.25),    # < 250ms
            HistogramBucket(0.5),     # < 500ms
            HistogramBucket(1.0),     # < 1s
            HistogramBucket(2.5),     # < 2.5s
            HistogramBucket(5.0),     # < 5s
            HistogramBucket(float('inf')),  # >= 5s
        ]
        
        # Start background collection thread
        self._collection_thread = threading.Thread(target=self._collect_system_metrics, daemon=True)
        self._collection_thread.start()
    
    def record_request_start(self, method: str, request_id: str) -> float:
        """Record the start of a gRPC request."""
        start_time = time.time()
        with self._lock:
            self.active_connections[method] += 1
        return start_time
    
    def record_request_complete(self, method: str, request_id: str, start_time: float, status: str = 'OK'):
        """Record the completion of a gRPC request."""
        duration = time.time() - start_time
        
        with self._lock:
            # Update request count
            self.request_count[method] += 1
            
            # Update request duration histogram
            self.request_duration[method].append(duration)
            
            # Update error count if not successful
            if status != 'OK':
                self.request_errors[method] += 1
            
            # Update latency buckets
            self._update_latency_buckets(duration)
            
            # Decrease active connections
            self.active_connections[method] = max(0, self.active_connections[method] - 1)
        
        _logger.debug("grpc_request_completed", method=method, duration=duration, status=status)
    
    def record_connection_error(self, host: str, port: int, error: str):
        """Record a connection error."""
        with self._lock:
            key = f"{host}:{port}"
            self.connection_errors[key] += 1
    
    def record_connection_established(self, host: str, port: int, duration: float):
        """Record successful connection establishment."""
        with self._lock:
            key = f"{host}:{port}"
            self.connection_duration[key].append(duration)
    
    def record_chat_request(self):
        """Record a chat request for business metrics."""
        current_time = time.time()
        with self._lock:
            self.chat_requests_per_second.append(current_time)
    
    def record_session_duration(self, duration: float):
        """Record session duration for business metrics."""
        with self._lock:
            self.session_duration.append(duration)
    
    def record_agent_performance(self, agent_type: str, duration: float, success: bool = True):
        """Record agent-specific performance metrics."""
        with self._lock:
            self.agent_performance[agent_type].append(duration)
    
    def get_request_metrics(self, method: str = None) -> Dict[str, Any]:
        """Get request metrics for a specific method or all methods."""
        with self._lock:
            if method:
                return self._get_method_metrics(method)
            else:
                return {m: self._get_method_metrics(m) for m in self.request_count.keys()}
    
    def get_connection_metrics(self) -> Dict[str, Any]:
        """Get connection-related metrics."""
        with self._lock:
            total_active = sum(self.active_connections.values())
            total_errors = sum(self.connection_errors.values())
            
            avg_connection_duration = {}
            for key, durations in self.connection_duration.items():
                if durations:
                    avg_connection_duration[key] = sum(durations) / len(durations)
            
            return {
                'active_connections': dict(self.active_connections),
                'total_active_connections': total_active,
                'connection_errors': dict(self.connection_errors),
                'total_connection_errors': total_errors,
                'average_connection_duration': avg_connection_duration,
            }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system-level metrics."""
        with self._lock:
            cpu_avg = sum(self.cpu_usage) / len(self.cpu_usage) if self.cpu_usage else 0
            memory_avg = sum(self.memory_usage) / len(self.memory_usage) if self.memory_usage else 0
            
            return {
                'cpu_usage_percent': cpu_avg,
                'memory_usage_mb': memory_avg,
                'network_io_bytes': list(self.network_io)[-10:] if self.network_io else [],  # Last 10 samples
            }
    
    def get_business_metrics(self) -> Dict[str, Any]:
        """Get business-specific metrics."""
        with self._lock:
            # Calculate requests per second (last 60 seconds)
            now = time.time()
            recent_requests = [t for t in self.chat_requests_per_second if now - t <= 60]
            requests_per_second = len(recent_requests) / 60.0
            
            # Calculate average session duration
            avg_session_duration = sum(self.session_duration) / len(self.session_duration) if self.session_duration else 0
            
            # Agent performance summary
            agent_summary = {}
            for agent_type, durations in self.agent_performance.items():
                if durations:
                    agent_summary[agent_type] = {
                        'count': len(durations),
                        'average_duration': sum(durations) / len(durations),
                        'min_duration': min(durations),
                        'max_duration': max(durations),
                    }
            
            return {
                'chat_requests_per_second': requests_per_second,
                'average_session_duration_seconds': avg_session_duration,
                'agent_performance': agent_summary,
            }
    
    def get_latency_summary(self, method: str = None) -> Dict[str, Any]:
        """Get latency summary with percentiles and bucket counts."""
        with self._lock:
            if method:
                durations = list(self.request_duration.get(method, []))
            else:
                # Combine all methods
                durations = []
                for method_durations in self.request_duration.values():
                    durations.extend(method_durations)
            
            if not durations:
                return {}
            
            durations.sort()
            count = len(durations)
            
            # Calculate percentiles
            percentiles = {
                'p50': durations[int(count * 0.5)],
                'p90': durations[int(count * 0.9)],
                'p95': durations[int(count * 0.95)],
                'p99': durations[int(count * 0.99)],
            }
            
            # Calculate bucket counts
            bucket_counts = {}
            for bucket in self.latency_buckets:
                if bucket.upper_bound == float('inf'):
                    bucket_counts[f'le_{bucket.upper_bound}'] = count
                else:
                    bucket_count = sum(1 for d in durations if d <= bucket.upper_bound)
                    bucket_counts[f'le_{bucket.upper_bound}'] = bucket_count
            
            return {
                'count': count,
                'average': sum(durations) / count,
                'min': min(durations),
                'max': max(durations),
                'percentiles': percentiles,
                'buckets': bucket_counts,
            }
    
    def _get_method_metrics(self, method: str) -> Dict[str, Any]:
        """Get metrics for a specific method."""
        durations = list(self.request_duration.get(method, []))
        
        return {
            'request_count': self.request_count[method],
            'error_count': self.request_errors[method],
            'success_rate': (self.request_count[method] - self.request_errors[method]) / max(self.request_count[method], 1),
            'average_duration': sum(durations) / len(durations) if durations else 0,
            'active_connections': self.active_connections[method],
        }
    
    def _update_latency_buckets(self, duration: float):
        """Update latency histogram buckets."""
        for bucket in self.latency_buckets:
            if duration <= bucket.upper_bound:
                bucket.count += 1
    
    def _collect_system_metrics(self):
        """Background thread to collect system metrics."""
        try:
            import psutil
            
            while True:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                with self._lock:
                    self.cpu_usage.append(cpu_percent)
                
                # Memory usage
                memory = psutil.virtual_memory()
                memory_mb = memory.used / (1024 * 1024)
                with self._lock:
                    self.memory_usage.append(memory_mb)
                
                # Network I/O
                network = psutil.net_io_counters()
                network_bytes = network.bytes_sent + network.bytes_recv
                with self._lock:
                    self.network_io.append(network_bytes)
                
                # Sleep before next collection
                time.sleep(5)
                
        except ImportError:
            _logger.warning("psutil not available, system metrics disabled")
        except Exception as exc:
            _logger.error("system_metrics_collection_error", error=str(exc))
    
    def reset_metrics(self):
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self.request_count.clear()
            self.request_duration.clear()
            self.request_errors.clear()
            self.active_connections.clear()
            self.connection_errors.clear()
            self.connection_duration.clear()
            self.cpu_usage.clear()
            self.memory_usage.clear()
            self.network_io.clear()
            self.chat_requests_per_second.clear()
            self.session_duration.clear()
            self.agent_performance.clear()
            
            for bucket in self.latency_buckets:
                bucket.count = 0
