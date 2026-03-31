"""Connection pool monitoring.

Provides advanced monitoring and alerting for database connection pools.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from mindflow_backend.infra.logging import get_logger

if TYPE_CHECKING:
    from .database_manager import DatabaseManager

_logger = get_logger(__name__)


class ConnectionPoolMonitor:
    """Advanced connection pool monitoring.

    Monitors pool utilization, connection times, and error rates
    with configurable alert thresholds.
    """

    def __init__(self, database_manager: DatabaseManager):
        """Initialize pool monitor.

        Args:
            database_manager: Database manager instance
        """
        self.db_manager = database_manager
        self._monitoring_task: asyncio.Task | None = None
        self._is_monitoring = False
        self._monitoring_interval = 30  # seconds
        self._alert_thresholds = {
            "pool_utilization": 0.8,
            "connection_time_ms": 1000.0,
            "error_rate": 0.1,
        }

    async def start_monitoring(self) -> None:
        """Start pool monitoring."""
        if self._is_monitoring:
            return

        self._is_monitoring = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        _logger.info("pool_monitoring_started")

    async def stop_monitoring(self) -> None:
        """Stop pool monitoring."""
        if not self._is_monitoring:
            return

        self._is_monitoring = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        _logger.info("pool_monitoring_stopped")

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self._is_monitoring:
            try:
                await self._collect_pool_metrics()
                await self._check_alerts()
                await asyncio.sleep(self._monitoring_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                _logger.error("pool_monitoring_error", error=str(e))
                await asyncio.sleep(5)

    async def _collect_pool_metrics(self) -> None:
        """Collect pool metrics."""
        if not self.db_manager._engine:
            return

        pool = self.db_manager._engine.pool
        metrics = self.db_manager._metrics

        # Update basic metrics
        metrics.total_connections = pool.size()
        metrics.active_connections = pool.checkedout()
        metrics.idle_connections = pool.checkedin()
        metrics.pool_utilization = metrics.active_connections / max(pool.size(), 1)

        # Calculate hit/miss rates
        total_requests = metrics.active_connections + metrics.idle_connections
        if total_requests > 0:
            metrics.pool_hit_rate = metrics.idle_connections / total_requests
            metrics.pool_miss_rate = metrics.active_connections / total_requests

        _logger.debug("pool_metrics_collected", **metrics.get_utilization_stats())

    async def _check_alerts(self) -> None:
        """Check for alert conditions."""
        metrics = self.db_manager._metrics

        # Check pool utilization
        if metrics.pool_utilization > self._alert_thresholds["pool_utilization"]:
            _logger.warning(
                "pool_utilization_high",
                utilization=metrics.pool_utilization,
                threshold=self._alert_thresholds["pool_utilization"],
            )

        # Check connection time
        if metrics.avg_connection_time_ms > self._alert_thresholds["connection_time_ms"]:
            _logger.warning(
                "connection_time_high",
                avg_time_ms=metrics.avg_connection_time_ms,
                threshold=self._alert_thresholds["connection_time_ms"],
            )

        # Check error rate
        total_operations = metrics.total_connections + metrics.connection_errors
        if total_operations > 0:
            error_rate = metrics.connection_errors / total_operations
            if error_rate > self._alert_thresholds["error_rate"]:
                _logger.warning(
                    "connection_error_rate_high",
                    error_rate=error_rate,
                    threshold=self._alert_thresholds["error_rate"],
                )