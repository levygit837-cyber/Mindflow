"""Database health monitoring and diagnostics.

Provides comprehensive health checking, performance monitoring,
and diagnostic capabilities for the database layer.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from mindflow_backend.infra.database.connection import get_db_manager
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


@dataclass
class HealthCheckResult:
    """Result of a database health check."""
    status: str  # "healthy", "degraded", "unhealthy"
    latency_ms: float
    error: str | None = None
    timestamp: datetime = None
    details: dict[str, Any] | None = None
    
    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now(UTC)


@dataclass
class DatabaseMetrics:
    """Comprehensive database performance metrics."""
    connection_pool_utilization: float
    active_connections: int
    idle_connections: int
    total_connections: int
    connection_errors: int
    avg_query_time_ms: float
    slow_queries_count: int
    last_error_time: datetime | None
    uptime_seconds: float


class DatabaseHealthChecker:
    """Advanced database health monitoring and diagnostics.
    
    Provides:
    - Real-time health status monitoring
    - Performance metrics collection
    - Automated health checks
    - Diagnostic information
    - Alerting capabilities
    """
    
    def __init__(self) -> None:
        """Initialize health checker with default thresholds."""
        self._health_thresholds = {
            "max_latency_ms": 100.0,  # Maximum acceptable latency
            "max_pool_utilization": 0.8,  # 80% max pool utilization
            "max_error_rate": 0.05,  # 5% max error rate
            "health_check_interval": 30,  # seconds
        }
        self._health_history: list[HealthCheckResult] = []
        self._last_metrics: DatabaseMetrics | None = None
        self._monitoring_task: asyncio.Task | None = None
        self._is_monitoring = False
        
    async def check_health(self) -> HealthCheckResult:
        """Perform comprehensive database health check.
        
        Returns:
            HealthCheckResult with detailed health status.
        """
        start_time = datetime.now(UTC)
        
        try:
            db_manager = get_db_manager()
            
            # Test basic connectivity
            health_data = await db_manager.health_check()
            
            # Calculate latency
            latency = (datetime.now(UTC) - start_time).total_seconds() * 1000
            
            # Determine overall health status
            status = self._determine_health_status(health_data, latency)
            
            # Collect detailed metrics
            metrics = await self._collect_metrics()
            
            result = HealthCheckResult(
                status=status,
                latency_ms=latency,
                details={
                    **health_data,
                    "metrics": metrics.__dict__ if metrics else {},
                }
            )
            
            # Store in history
            self._health_history.append(result)
            if len(self._health_history) > 100:  # Keep last 100 checks
                self._health_history.pop(0)
                
            _logger.info(
                "database_health_check_completed",
                status=status,
                latency_ms=latency,
                details=result.details,
            )
            
            return result
            
        except Exception as e:
            result = HealthCheckResult(
                status="unhealthy",
                latency_ms=(datetime.now(UTC) - start_time).total_seconds() * 1000,
                error=str(e),
            )
            
            _logger.error(
                "database_health_check_error",
                error=str(e),
                latency_ms=result.latency_ms,
            )
            
            return result
            
    def _determine_health_status(self, health_data: dict[str, Any], latency_ms: float) -> str:
        """Determine overall health status from metrics.
        
        Args:
            health_data: Health check data from database manager
            latency_ms: Query latency in milliseconds
            
        Returns:
            Health status: "healthy", "degraded", or "unhealthy"
        """
        status = "healthy"
        
        # Check latency
        if latency_ms > self._health_thresholds["max_latency_ms"]:
            status = "degraded" if status == "healthy" else "unhealthy"
            
        # Check pool utilization
        pool_utilization = health_data.get("pool_utilization", 0)
        if pool_utilization > self._health_thresholds["max_pool_utilization"]:
            status = "degraded" if status == "healthy" else "unhealthy"
            
        # Check for connection errors
        if health_data.get("status") != "healthy":
            status = "unhealthy"
            
        return status
        
    async def _collect_metrics(self) -> DatabaseMetrics:
        """Collect comprehensive database performance metrics.
        
        Returns:
            DatabaseMetrics with current performance data.
        """
        try:
            db_manager = get_db_manager()
            metrics_data = db_manager.metrics
            
            # Calculate average query time from recent history
            recent_checks = self._health_history[-10:] if self._health_history else []
            avg_query_time = sum(check.latency_ms for check in recent_checks) / len(recent_checks) if recent_checks else 0.0
            
            # Count slow queries
            slow_queries = sum(1 for check in recent_checks if check.latency_ms > 500)
            
            metrics = DatabaseMetrics(
                connection_pool_utilization=metrics_data.pool_utilization,
                active_connections=metrics_data.active_connections,
                idle_connections=metrics_data.idle_connections,
                total_connections=metrics_data.total_connections,
                connection_errors=metrics_data.connection_errors,
                avg_query_time_ms=avg_query_time,
                slow_queries_count=slow_queries,
                last_error_time=metrics_data.last_error,
                uptime_seconds=0.0,  # TODO: Implement uptime tracking
            )
            
            self._last_metrics = metrics
            return metrics
            
        except Exception as e:
            _logger.error("database_metrics_collection_failed", error=str(e))
            raise
            
    async def get_diagnostics(self) -> dict[str, Any]:
        """Get comprehensive diagnostic information.
        
        Returns:
            Dict containing detailed diagnostic data.
        """
        try:
            current_health = await self.check_health()
            metrics = await self._collect_metrics()
            
            # Calculate health trends
            recent_health = self._health_history[-20:] if self._health_history else []
            health_trend = {
                "healthy_count": sum(1 for h in recent_health if h.status == "healthy"),
                "degraded_count": sum(1 for h in recent_health if h.status == "degraded"),
                "unhealthy_count": sum(1 for h in recent_health if h.status == "unhealthy"),
                "avg_latency_ms": sum(h.latency_ms for h in recent_health) / len(recent_health) if recent_health else 0,
            }
            
            diagnostics = {
                "current_health": {
                    "status": current_health.status,
                    "latency_ms": current_health.latency_ms,
                    "error": current_health.error,
                    "timestamp": current_health.timestamp.isoformat(),
                },
                "metrics": metrics.__dict__,
                "health_trend": health_trend,
                "thresholds": self._health_thresholds,
                "monitoring_active": self._is_monitoring,
                "history_size": len(self._health_history),
            }
            
            return diagnostics
            
        except Exception as e:
            _logger.error("database_diagnostics_failed", error=str(e))
            return {
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }
            
    async def start_monitoring(self) -> None:
        """Start continuous health monitoring."""
        if self._is_monitoring:
            return
            
        self._is_monitoring = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        _logger.info(
            "database_health_monitoring_started",
            interval=self._health_thresholds["health_check_interval"],
        )
        
    async def stop_monitoring(self) -> None:
        """Stop continuous health monitoring."""
        if not self._is_monitoring:
            return
            
        self._is_monitoring = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
                
        _logger.info("database_health_monitoring_stopped")
        
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop for continuous health checks."""
        while self._is_monitoring:
            try:
                await self.check_health()
                await asyncio.sleep(self._health_thresholds["health_check_interval"])
            except asyncio.CancelledError:
                break
            except Exception as e:
                _logger.error("database_monitoring_loop_error", error=str(e))
                await asyncio.sleep(5)  # Brief pause before retry
                
    def set_threshold(self, key: str, value: float) -> None:
        """Update health check threshold.
        
        Args:
            key: Threshold key to update
            value: New threshold value
        """
        if key in self._health_thresholds:
            old_value = self._health_thresholds[key]
            self._health_thresholds[key] = value
            _logger.info(
                "database_health_threshold_updated",
                key=key,
                old_value=old_value,
                new_value=value,
            )
        else:
            _logger.warning("database_health_threshold_unknown", key=key)
            
    def get_health_summary(self) -> dict[str, Any]:
        """Get summary of recent health checks.
        
        Returns:
            Dict containing health summary statistics.
        """
        if not self._health_history:
            return {
                "status": "unknown",
                "message": "No health checks performed yet",
                "total_checks": 0,
            }
            
        recent_checks = self._health_history[-10:]
        latest_check = self._health_history[-1]
        
        summary = {
            "status": latest_check.status,
            "latest_latency_ms": latest_check.latency_ms,
            "latest_error": latest_check.error,
            "total_checks": len(self._health_history),
            "recent_summary": {
                "healthy": sum(1 for h in recent_checks if h.status == "healthy"),
                "degraded": sum(1 for h in recent_checks if h.status == "degraded"),
                "unhealthy": sum(1 for h in recent_checks if h.status == "unhealthy"),
                "avg_latency_ms": sum(h.latency_ms for h in recent_checks) / len(recent_checks),
            },
            "monitoring_active": self._is_monitoring,
        }
        
        return summary


# Global health checker instance
_health_checker: DatabaseHealthChecker | None = None


def get_health_checker() -> DatabaseHealthChecker:
    """Get global database health checker instance."""
    global _health_checker
    if _health_checker is None:
        _health_checker = DatabaseHealthChecker()
    return _health_checker
