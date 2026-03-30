"""Database connection manager.

Provides advanced connection pooling, health monitoring,
and connection lifecycle management for PostgreSQL.
"""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from datetime import datetime, UTC
from typing import AsyncGenerator, Dict, Any, List, Optional

import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import event, text

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.infra.resilience import with_retry, RetryConfig

from .models import ConnectionMetrics, ConnectionStatus, PoolState
from .pool_monitor import ConnectionPoolMonitor

_logger = get_logger(__name__)


class DatabaseManager:
    """Advanced database connection manager with robust pooling.

    Features:
    - Enhanced connection pooling with health monitoring
    - Automatic failover and recovery
    - Connection lifecycle management with recycling
    - Advanced performance metrics collection
    - Retry logic with exponential backoff
    - Pool monitoring and alerting
    - Connection state tracking
    """

    def __init__(self) -> None:
        """Initialize database manager with default settings."""
        self._engine = None
        self._session_factory = None
        self._async_session_factory = None
        self._metrics = ConnectionMetrics()
        self._health_status = ConnectionStatus.HEALTHY
        self._pool_state = PoolState.NORMAL
        self._last_health_check = None
        self._connection_lock = asyncio.Lock()
        self._pool_monitor = ConnectionPoolMonitor(self)
        self._connection_times: List[float] = []
        self._recovery_task: Optional[asyncio.Task] = None
        self._is_initialized = False

    @property
    def metrics(self) -> ConnectionMetrics:
        """Get current connection metrics."""
        return self._metrics

    @property
    def is_healthy(self) -> bool:
        """Check if database is healthy."""
        return self._health_status == ConnectionStatus.HEALTHY

    @property
    def pool_state(self) -> PoolState:
        """Get current pool state."""
        return self._pool_state

    @staticmethod
    def _safe_invalid_count(pool) -> int:
        """Return invalid connection count when exposed by the active pool implementation."""
        invalid = getattr(pool, "invalid", None)
        if callable(invalid):
            try:
                return int(invalid())
            except Exception:
                return 0
        if isinstance(invalid, int):
            return invalid
        return 0

    async def initialize(self) -> None:
        """Initialize database connections and pooling.

        Creates both sync and async engines with optimized pooling
        configuration for production workloads.
        """
        if self._is_initialized:
            return

        settings = get_settings()
        database_config = settings.database

        async def _init_engines():
            # Async engine for async operations
            self._engine = create_async_engine(
                database_config.get_connection_string(),
                pool_size=database_config.pool_size,
                max_overflow=database_config.max_overflow,
                pool_pre_ping=database_config.pool_pre_ping,
                pool_recycle=database_config.pool_recycle,
                pool_timeout=database_config.pool_timeout,
                echo=settings.app_env == "development",
                connect_args={
                    "options": "-c jit=off",
                },
            )

            # Create session factories
            self._async_session_factory = async_sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
                autocommit=False,
            )

            # Add event listeners for metrics
            event.listen(self._engine.sync_engine, "connect", self._on_connect)
            event.listen(self._engine.sync_engine, "checkout", self._on_checkout)
            event.listen(self._engine.sync_engine, "checkin", self._on_checkin)

            # Start pool monitoring
            await self._pool_monitor.start_monitoring()

            self._is_initialized = True

            _logger.info(
                "database_initialized",
                pool_size=database_config.pool_size,
                max_overflow=database_config.max_overflow,
                pool_recycle=database_config.pool_recycle,
                pool_timeout=database_config.pool_timeout,
            )

        await with_retry(RetryConfig(max_retries=database_config.retry_attempts))(_init_engines)()

    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive database health check.

        Returns:
            Dict containing health status and detailed metrics.
        """
        try:
            start_time = datetime.now(UTC)

            # Test basic connectivity
            async with self._engine.begin() as conn:
                await conn.execute(text("SELECT 1"))

            # Get pool statistics
            pool = self._engine.pool
            connection_time = (datetime.now(UTC) - start_time).total_seconds()

            # Update metrics
            self._metrics.update_connection_time(connection_time * 1000)

            # Determine health status
            self._update_health_status(pool)

            health_data = {
                "status": self._health_status.value,
                "pool_state": self._pool_state.value,
                "connection_time_ms": connection_time * 1000,
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalid": self._safe_invalid_count(pool),
                "timestamp": datetime.now(UTC).isoformat(),
                "metrics": self._metrics.get_utilization_stats(),
            }

            self._last_health_check = datetime.now(UTC)

            _logger.info("database_health_check_success", **health_data)
            return health_data

        except Exception as e:
            self._health_status = ConnectionStatus.UNHEALTHY
            self._metrics.last_error = datetime.now(UTC)
            self._metrics.connection_errors += 1

            error_data = {
                "status": self._health_status.value,
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
                "metrics": self._metrics.get_utilization_stats(),
            }

            _logger.error("database_health_check_failed", **error_data)
            return error_data

    def _update_health_status(self, pool) -> None:
        """Update health status based on pool state.

        Args:
            pool: Connection pool
        """
        utilization = pool.checkedout() / max(pool.size(), 1)

        if utilization > 0.9:
            self._pool_state = PoolState.UNDER_PRESSURE
            if self._health_status == ConnectionStatus.HEALTHY:
                self._health_status = ConnectionStatus.DEGRADED
        elif pool.overflow() > 0:
            self._pool_state = PoolState.EXHAUSTED
            self._health_status = ConnectionStatus.DEGRADED
        else:
            self._pool_state = PoolState.NORMAL
            if self._health_status != ConnectionStatus.UNHEALTHY:
                self._health_status = ConnectionStatus.HEALTHY

    async def close(self) -> None:
        """Close database connections."""
        if self._pool_monitor:
            await self._pool_monitor.stop_monitoring()

        if self._engine:
            await self._engine.dispose()

        self._is_initialized = False
        _logger.info("database_closed")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session with connection tracking.

        Yields:
            AsyncSession: Database session
        """
        if not self._engine:
            raise RuntimeError("Database not initialized")

        start_time = time.time()

        try:
            async with self._async_session_factory() as session:
                connection_time = (time.time() - start_time) * 1000
                self._metrics.update_connection_time(connection_time)

                yield session

        except Exception as e:
            self._metrics.connection_errors += 1
            self._metrics.last_error = datetime.now(UTC)
            raise

    async def recycle_connections(self) -> Dict[str, Any]:
        """Recycle old connections in the pool.

        Returns:
            Recycling results
        """
        if not self._engine:
            return {"status": "not_initialized"}

        start_time = time.time()
        recycled = 0
        failed = 0

        try:
            pool = self._engine.pool

            # Force connection recycling
            for connection in pool._pool.queue:
                try:
                    # Close and remove connection
                    connection.close()
                    recycled += 1
                except Exception:
                    failed += 1

            self._metrics.recycle_count += recycled
            self._metrics.failed_recycles += failed
            self._metrics.last_recycle = datetime.now(UTC)

            duration = (time.time() - start_time) * 1000

            result = {
                "status": "success",
                "recycled": recycled,
                "failed": failed,
                "duration_ms": duration,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            _logger.info("connections_recycled", **result)
            return result

        except Exception as e:
            error_result = {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }

            _logger.error("connection_recycling_failed", **error_result)
            return error_result

    async def optimize_pool(self) -> Dict[str, Any]:
        """Optimize connection pool configuration.

        Returns:
            Optimization results
        """
        if not self._engine:
            return {"status": "not_initialized"}

        start_time = time.time()

        try:
            # Get current pool metrics
            pool = self._engine.pool
            current_utilization = pool.checkedout() / max(pool.size(), 1)

            optimizations = []

            # Adjust pool size based on utilization
            if current_utilization > 0.8 and pool.size() < 50:
                # Consider increasing pool size
                optimizations.append({
                    "type": "increase_pool_size",
                    "current_size": pool.size(),
                    "recommended_size": min(pool.size() + 10, 50),
                    "reason": "High utilization detected",
                })
            elif current_utilization < 0.3 and pool.size() > 20:
                # Consider decreasing pool size
                optimizations.append({
                    "type": "decrease_pool_size",
                    "current_size": pool.size(),
                    "recommended_size": max(pool.size() - 5, 20),
                    "reason": "Low utilization detected",
                })

            # Check connection times
            if self._metrics.avg_connection_time_ms > 500:
                optimizations.append({
                    "type": "optimize_connection_time",
                    "current_avg_ms": self._metrics.avg_connection_time_ms,
                    "recommendation": "Check network latency or database performance",
                })

            duration = (time.time() - start_time) * 1000

            result = {
                "status": "success",
                "current_utilization": current_utilization,
                "optimizations": optimizations,
                "duration_ms": duration,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            _logger.info("pool_optimization_completed", **result)
            return result

        except Exception as e:
            error_result = {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }

            _logger.error("pool_optimization_failed", **error_result)
            return error_result

    def _on_connect(self, dbapi_connection, connection_record):
        """Handle new connection event."""
        self._metrics.total_connections += 1
        _logger.debug("database_connection_established")

    def _on_checkout(self, dbapi_connection, connection_record, connection_proxy):
        """Handle connection checkout event."""
        self._metrics.active_connections += 1
        self._metrics.idle_connections = max(0, self._metrics.idle_connections - 1)
        _logger.debug("database_connection_checked_out")

    def _on_checkin(self, dbapi_connection, connection_record):
        """Handle connection checkin event."""
        self._metrics.active_connections = max(0, self._metrics.active_connections - 1)
        self._metrics.idle_connections += 1
        _logger.debug("database_connection_checked_in")

    async def get_detailed_metrics(self) -> Dict[str, Any]:
        """Get detailed database metrics.

        Returns:
            Comprehensive metrics dictionary
        """
        if not self._engine:
            return {"status": "not_initialized"}

        pool = self._engine.pool

        return {
            "status": "active",
            "health_status": self._health_status.value,
            "pool_state": self._pool_state.value,
            "pool_info": {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalid": self._safe_invalid_count(pool),
                "utilization": pool.checkedout() / max(pool.size(), 1),
            },
            "metrics": self._metrics.get_utilization_stats(),
            "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None,
            "is_initialized": self._is_initialized,
        }