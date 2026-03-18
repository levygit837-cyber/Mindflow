"""Worker monitoring and metrics collection."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.infra.logging.structured import get_correlation_id
from mindflow_backend.workers.base.worker import BaseWorker, WorkerStatus
from mindflow_backend.workers.contracts.schemas.health import (
    QueueHealthSnapshot,
    RabbitConnectionSnapshot,
    WorkerHealthSnapshot,
    WorkerSystemHealthReport,
)

_logger = get_logger(__name__)


@dataclass
class WorkerMetrics:
    """Metrics for a single worker."""
    
    worker_name: str
    worker_type: str
    queue_name: str
    status: WorkerStatus
    tasks_processed: int = 0
    tasks_successful: int = 0
    tasks_failed: int = 0
    average_processing_time: float = 0.0
    last_activity: Optional[float] = None
    uptime: float = 0.0
    error_rate: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage: float = 0.0
    retry_count: int = 0
    last_correlation_id: str | None = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.tasks_processed == 0:
            return 0.0
        return self.tasks_successful / self.tasks_processed
    
    @property
    def is_healthy(self) -> bool:
        """Determine if worker is healthy."""
        return (
            self.status != WorkerStatus.ERROR
            and self.error_rate < 0.1  # Less than 10% error rate
            and (self.tasks_processed == 0 or self.success_rate > 0.9)
        )

    @property
    def retry_rate(self) -> float:
        """Calculate retry rate relative to processed messages."""
        if self.tasks_processed == 0:
            return 0.0
        return self.retry_count / self.tasks_processed


@dataclass
class SystemMetrics:
    """System-wide worker metrics."""
    
    timestamp: float = field(default_factory=time.time)
    total_workers: int = 0
    active_workers: int = 0
    idle_workers: int = 0
    processing_workers: int = 0
    error_workers: int = 0
    stopped_workers: int = 0
    total_tasks_processed: int = 0
    total_tasks_successful: int = 0
    total_tasks_failed: int = 0
    system_success_rate: float = 0.0
    system_error_rate: float = 0.0
    average_processing_time: float = 0.0
    worker_metrics: Dict[str, WorkerMetrics] = field(default_factory=dict)
    queue_metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    @property
    def system_health_score(self) -> float:
        """Calculate overall system health score."""
        if self.total_workers == 0:
            return 0.0
        
        health_factors = [
            self.system_success_rate,
            1.0 - self.system_error_rate,
            self.active_workers / self.total_workers,
        ]
        
        return sum(health_factors) / len(health_factors)


class WorkerMonitor:
    """Monitor worker performance and health."""
    
    def __init__(self, monitoring_interval: int = 30) -> None:
        """Initialize the worker monitor.
        
        Args:
            monitoring_interval: Interval in seconds between monitoring cycles
        """
        self.monitoring_interval = monitoring_interval
        self._workers: Dict[str, BaseWorker] = {}
        self._metrics: SystemMetrics = SystemMetrics()
        self._monitoring_task: Optional[asyncio.Task] = None
        self._is_monitoring = False
        self._start_time = time.time()
        
        # Historical data for trends
        self._historical_metrics: List[SystemMetrics] = []
        self._max_history_size = 1000
    
    def add_worker(self, worker: BaseWorker) -> None:
        """Add a worker to monitor.
        
        Args:
            worker: Worker instance to monitor
        """
        worker_key = f"{worker.worker_name}_{worker.queue_config.name}"
        self._workers[worker_key] = worker
        
        # Initialize metrics for this worker
        if worker_key not in self._metrics.worker_metrics:
            self._metrics.worker_metrics[worker_key] = WorkerMetrics(
                worker_name=worker.worker_name,
                worker_type=worker.queue_config.worker_type,
                queue_name=worker.queue_config.get_full_queue_name(),
                status=worker.get_status(),
            )
        
        _logger.info(f"Added worker {worker_key} to monitoring")
    
    def remove_worker(self, worker: BaseWorker) -> None:
        """Remove a worker from monitoring.
        
        Args:
            worker: Worker instance to remove
        """
        worker_key = f"{worker.worker_name}_{worker.queue_config.name}"
        
        if worker_key in self._workers:
            del self._workers[worker_key]
        
        if worker_key in self._metrics.worker_metrics:
            del self._metrics.worker_metrics[worker_key]
        
        _logger.info(f"Removed worker {worker_key} from monitoring")
    
    async def start_monitoring(self) -> None:
        """Start monitoring workers."""
        if self._is_monitoring:
            return
        
        self._is_monitoring = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        _logger.info("Worker monitoring started")

    async def collect_once(self) -> None:
        """Collect a single health/metrics snapshot on demand."""
        await self._collect_metrics()
    
    async def stop_monitoring(self) -> None:
        """Stop monitoring workers."""
        self._is_monitoring = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        _logger.info("Worker monitoring stopped")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self._is_monitoring:
            try:
                await self._collect_metrics()
                await asyncio.sleep(self.monitoring_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                _logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.monitoring_interval)
    
    async def _collect_metrics(self) -> None:
        """Collect metrics from all workers."""
        current_time = time.time()
        
        # Reset system metrics
        self._metrics = SystemMetrics()
        self._metrics.total_workers = len(self._workers)
        
        # Collect metrics from each worker
        for worker_key, worker in self._workers.items():
            try:
                worker_metrics = self._metrics.worker_metrics.get(worker_key)
                if worker_metrics is None:
                    worker_metrics = WorkerMetrics(
                        worker_name=worker.worker_name,
                        worker_type=worker.queue_config.worker_type,
                        queue_name=worker.queue_config.get_full_queue_name(),
                        status=worker.get_status(),
                    )
                    self._metrics.worker_metrics[worker_key] = worker_metrics
                
                # Update worker status
                worker_metrics.status = worker.get_status()
                worker_metrics.uptime = current_time - self._start_time
                worker_runtime_metrics = self._get_worker_runtime_metrics(worker)
                worker_metrics.tasks_processed = int(worker_runtime_metrics.get("tasks_processed", 0))
                worker_metrics.tasks_successful = int(worker_runtime_metrics.get("tasks_successful", 0))
                worker_metrics.tasks_failed = int(worker_runtime_metrics.get("tasks_failed", 0))
                worker_metrics.average_processing_time = float(
                    worker_runtime_metrics.get("average_processing_time", 0.0)
                )
                worker_metrics.last_activity = worker_runtime_metrics.get("last_activity", current_time)
                worker_metrics.memory_usage_mb = float(worker_runtime_metrics.get("memory_usage_mb", 0.0))
                worker_metrics.cpu_usage = float(worker_runtime_metrics.get("cpu_usage", 0.0))
                worker_metrics.retry_count = int(worker_runtime_metrics.get("retry_count", 0))
                worker_metrics.last_correlation_id = worker_runtime_metrics.get("last_correlation_id")
                if worker_metrics.tasks_processed > 0:
                    worker_metrics.error_rate = (
                        worker_metrics.tasks_failed / worker_metrics.tasks_processed
                    )
                
                # Update status counts
                if worker_metrics.status == WorkerStatus.IDLE:
                    self._metrics.idle_workers += 1
                    self._metrics.active_workers += 1
                elif worker_metrics.status == WorkerStatus.PROCESSING:
                    self._metrics.processing_workers += 1
                    self._metrics.active_workers += 1
                elif worker_metrics.status == WorkerStatus.ERROR:
                    self._metrics.error_workers += 1
                elif worker_metrics.status == WorkerStatus.STOPPED:
                    self._metrics.stopped_workers += 1
                
                queue_name = worker.queue_config.get_full_queue_name()
                declaration = getattr(getattr(worker, "_queue", None), "declaration_result", None)
                self._metrics.queue_metrics[queue_name] = {
                    "queue_name": queue_name,
                    "domain": worker.queue_config.domain.value,
                    "worker_type": worker.queue_config.worker_type,
                    "priority": worker.queue_config.priority.value,
                    "message_count": getattr(declaration, "message_count", None),
                    "consumer_count": getattr(declaration, "consumer_count", None),
                    "retry_count": worker_metrics.retry_count,
                    "retry_rate": worker_metrics.retry_rate,
                    "dead_letter_queue": worker.queue_config.get_dead_letter_queue_name(),
                    "connection_status": self._resolve_connection_status(worker),
                }

            except Exception as e:
                _logger.error(f"Error collecting metrics for worker {worker_key}: {e}")
        
        # Calculate system-wide metrics
        self._calculate_system_metrics()
        
        # Store historical data
        self._store_historical_metrics()
    
    def _calculate_system_metrics(self) -> None:
        """Calculate system-wide metrics from worker metrics."""
        total_processed = sum(w.tasks_processed for w in self._metrics.worker_metrics.values())
        total_successful = sum(w.tasks_successful for w in self._metrics.worker_metrics.values())
        total_failed = sum(w.tasks_failed for w in self._metrics.worker_metrics.values())
        
        self._metrics.total_tasks_processed = total_processed
        self._metrics.total_tasks_successful = total_successful
        self._metrics.total_tasks_failed = total_failed
        
        if total_processed > 0:
            self._metrics.system_success_rate = total_successful / total_processed
            self._metrics.system_error_rate = total_failed / total_processed
        
        # Calculate average processing time
        processing_times = [
            w.average_processing_time 
            for w in self._metrics.worker_metrics.values()
            if w.average_processing_time > 0
        ]
        
        if processing_times:
            self._metrics.average_processing_time = sum(processing_times) / len(processing_times)
    
    def _store_historical_metrics(self) -> None:
        """Store current metrics in historical data."""
        # Create a copy of current metrics
        historical_copy = SystemMetrics(
            timestamp=self._metrics.timestamp,
            total_workers=self._metrics.total_workers,
            active_workers=self._metrics.active_workers,
            idle_workers=self._metrics.idle_workers,
            processing_workers=self._metrics.processing_workers,
            error_workers=self._metrics.error_workers,
            stopped_workers=self._metrics.stopped_workers,
            total_tasks_processed=self._metrics.total_tasks_processed,
            total_tasks_successful=self._metrics.total_tasks_successful,
            total_tasks_failed=self._metrics.total_tasks_failed,
            system_success_rate=self._metrics.system_success_rate,
            system_error_rate=self._metrics.system_error_rate,
            average_processing_time=self._metrics.average_processing_time,
            queue_metrics=self._metrics.queue_metrics.copy(),
        )
        
        self._historical_metrics.append(historical_copy)
        
        # Limit history size
        if len(self._historical_metrics) > self._max_history_size:
            self._historical_metrics.pop(0)
    
    def get_current_metrics(self) -> SystemMetrics:
        """Get current system metrics."""
        return self._metrics
    
    def get_worker_metrics(self, worker_key: str) -> Optional[WorkerMetrics]:
        """Get metrics for a specific worker."""
        return self._metrics.worker_metrics.get(worker_key)
    
    def get_historical_metrics(
        self,
        limit: Optional[int] = None,
    ) -> List[SystemMetrics]:
        """Get historical metrics.
        
        Args:
            limit: Maximum number of historical records to return
            
        Returns:
            List of historical metrics
        """
        if limit is None:
            return self._historical_metrics.copy()
        
        return self._historical_metrics[-limit:]
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get a health summary of the worker system."""
        return self.get_health_report().model_dump(mode="json")

    def get_health_report(self) -> WorkerSystemHealthReport:
        """Build a typed health report for logs, runbooks and startup checks."""
        worker_snapshots = [
            WorkerHealthSnapshot(
                worker_name=metrics.worker_name,
                worker_type=metrics.worker_type,
                queue_name=metrics.queue_name,
                status=metrics.status.value,
                tasks_processed=metrics.tasks_processed,
                tasks_successful=metrics.tasks_successful,
                tasks_failed=metrics.tasks_failed,
                retry_count=metrics.retry_count,
                retry_rate=metrics.retry_rate,
                average_processing_time=metrics.average_processing_time,
                uptime=metrics.uptime,
                last_activity=metrics.last_activity,
                error_rate=metrics.error_rate,
                success_rate=metrics.success_rate,
                memory_usage_mb=metrics.memory_usage_mb,
                cpu_usage=metrics.cpu_usage,
                last_correlation_id=metrics.last_correlation_id,
                is_healthy=metrics.is_healthy,
            )
            for metrics in self._metrics.worker_metrics.values()
        ]
        queue_snapshots = {
            queue_name: QueueHealthSnapshot(**queue_metrics)
            for queue_name, queue_metrics in self._metrics.queue_metrics.items()
        }
        unhealthy_workers = [
            snapshot.queue_name
            for snapshot in worker_snapshots
            if not snapshot.is_healthy
        ]
        connected_workers = sum(
            1 for worker in self._workers.values()
            if self._resolve_connection_status(worker) == "connected"
        )
        disconnected_workers = max(0, len(self._workers) - connected_workers)

        return WorkerSystemHealthReport(
            correlation_id=get_correlation_id(),
            overall_health_score=self._metrics.system_health_score,
            total_workers=self._metrics.total_workers,
            active_workers=self._metrics.active_workers,
            error_workers=self._metrics.error_workers,
            system_success_rate=self._metrics.system_success_rate,
            system_error_rate=self._metrics.system_error_rate,
            average_processing_time=self._metrics.average_processing_time,
            rabbitmq=RabbitConnectionSnapshot(
                connection_status=self._aggregate_connection_status(),
                channel_status=self._aggregate_channel_status(),
                total_queues=len(queue_snapshots),
                connected_workers=connected_workers,
                disconnected_workers=disconnected_workers,
            ),
            workers=worker_snapshots,
            queues=queue_snapshots,
            unhealthy_workers=unhealthy_workers,
            recommendations=self._generate_recommendations(),
        )
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on metrics."""
        recommendations = []
        
        # Check for high error rates
        if self._metrics.system_error_rate > 0.1:
            recommendations.append("System error rate is high. Check worker configurations and error handling.")
        
        # Check for inactive workers
        if self._metrics.active_workers < self._metrics.total_workers * 0.8:
            recommendations.append("Many workers are inactive. Check worker health and restart if needed.")
        
        # Check for slow processing
        if self._metrics.average_processing_time > 5.0:
            recommendations.append("Average processing time is high. Consider optimizing worker performance or adding more workers.")
        
        # Check specific worker issues
        for worker_key, metrics in self._metrics.worker_metrics.items():
            if metrics.error_rate > 0.2:
                recommendations.append(f"Worker {worker_key} has high error rate. Check logs and configuration.")
            
            if metrics.memory_usage_mb > 500:
                recommendations.append(f"Worker {worker_key} has high memory usage. Consider memory optimization.")
        
        return recommendations
    
    def get_performance_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance trends over time.
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Performance trend analysis
        """
        # Filter historical data for the specified time period
        cutoff_time = time.time() - (hours * 3600)
        recent_metrics = [
            m for m in self._historical_metrics
            if hasattr(m, 'timestamp') and m.timestamp > cutoff_time
        ]
        
        if len(recent_metrics) < 2:
            return {"message": "Insufficient historical data for trend analysis"}
        
        # Calculate trends
        first_metrics = recent_metrics[0]
        last_metrics = recent_metrics[-1]
        
        return {
            "time_period_hours": hours,
            "data_points": len(recent_metrics),
            "trends": {
                "success_rate_trend": (
                    (last_metrics.system_success_rate - first_metrics.system_success_rate)
                    / first_metrics.system_success_rate
                    if first_metrics.system_success_rate > 0 else 0
                ),
                "processing_time_trend": (
                    (last_metrics.average_processing_time - first_metrics.average_processing_time)
                    / first_metrics.average_processing_time
                    if first_metrics.average_processing_time > 0 else 0
                ),
                "worker_count_trend": (
                    (last_metrics.active_workers - first_metrics.active_workers)
                    / first_metrics.active_workers
                    if first_metrics.active_workers > 0 else 0
                ),
            },
            "recommendations": self._generate_trend_recommendations(recent_metrics),
        }
    
    def _generate_trend_recommendations(self, metrics: List[SystemMetrics]) -> List[str]:
        """Generate recommendations based on trends."""
        recommendations = []
        
        if len(metrics) < 10:
            return recommendations
        
        # Analyze recent trends
        recent_success_rates = [m.system_success_rate for m in metrics[-10:]]
        recent_processing_times = [m.average_processing_time for m in metrics[-10:]]
        
        # Check for declining success rate
        if recent_success_rates[-1] < recent_success_rates[0] - 0.1:
            recommendations.append("Success rate is declining. Investigate recent changes and errors.")
        
        # Check for increasing processing time
        if recent_processing_times[-1] > recent_processing_times[0] * 1.5:
            recommendations.append("Processing time is increasing. Consider performance optimization.")
        
        return recommendations

    def _get_worker_runtime_metrics(self, worker: BaseWorker) -> Dict[str, Any]:
        """Fetch runtime metrics exposed by a worker with safe fallbacks."""
        if hasattr(worker, "get_metrics_snapshot"):
            try:
                metrics = worker.get_metrics_snapshot()
                if isinstance(metrics, dict):
                    return metrics
            except Exception as exc:
                _logger.warning("Failed to read worker metrics snapshot", error=str(exc))

        return {
            "tasks_processed": 0,
            "tasks_successful": 0,
            "tasks_failed": 0,
            "average_processing_time": worker.get_processing_time()
            if hasattr(worker, "get_processing_time")
            else 0.0,
            "last_activity": None,
            "retry_count": 0,
            "memory_usage_mb": 0.0,
            "cpu_usage": 0.0,
            "last_correlation_id": None,
        }

    def _resolve_connection_status(self, worker: BaseWorker) -> str:
        """Resolve RabbitMQ connection status for a worker."""
        connection = getattr(worker, "_connection", None)
        if connection is None:
            return "unknown"
        return "connected" if not getattr(connection, "is_closed", True) else "disconnected"

    def _resolve_channel_status(self, worker: BaseWorker) -> str:
        """Resolve RabbitMQ channel status for a worker."""
        channel = getattr(worker, "_channel", None)
        if channel is None:
            return "unknown"
        return "open" if not getattr(channel, "is_closed", True) else "closed"

    def _aggregate_connection_status(self) -> str:
        """Aggregate connection status across all monitored workers."""
        statuses = {
            self._resolve_connection_status(worker)
            for worker in self._workers.values()
        }
        if not statuses:
            return "unknown"
        if statuses == {"connected"}:
            return "connected"
        if "connected" in statuses:
            return "degraded"
        if statuses == {"disconnected"}:
            return "disconnected"
        return "unknown"

    def _aggregate_channel_status(self) -> str:
        """Aggregate channel status across all monitored workers."""
        statuses = {
            self._resolve_channel_status(worker)
            for worker in self._workers.values()
        }
        if not statuses:
            return "unknown"
        if statuses == {"open"}:
            return "open"
        if "open" in statuses:
            return "degraded"
        if statuses == {"closed"}:
            return "closed"
        return "unknown"


# Global worker monitor instance
_worker_monitor: Optional[WorkerMonitor] = None


def get_worker_monitor() -> WorkerMonitor:
    """Get the global worker monitor instance."""
    global _worker_monitor
    if _worker_monitor is None:
        _worker_monitor = WorkerMonitor()
    return _worker_monitor
