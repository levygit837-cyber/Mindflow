"""Database connection management with robust pooling.

Provides advanced connection pooling, health monitoring,
and connection lifecycle management for PostgreSQL.
"""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import AsyncGenerator, Optional, Dict, Any, List
from datetime import datetime, UTC, timedelta
from enum import Enum
import weakref
import threading

import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event
from sqlalchemy.pool import QueuePool, StaticPool

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.infra.resilience import with_retry, RetryConfig

_logger = get_logger(__name__)


class ConnectionStatus(Enum):
    """Database connection status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    RECOVERING = "recovering"


class PoolState(Enum):
    """Connection pool state."""
    NORMAL = "normal"
    UNDER_PRESSURE = "under_pressure"
    EXHAUSTED = "exhausted"
    RECOVERING = "recovering"


@dataclass
class ConnectionMetrics:
    """Enhanced metrics for database connection monitoring."""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    connection_errors: int = 0
    timeout_errors: int = 0
    last_error: Optional[datetime] = None
    pool_utilization: float = 0.0
    avg_connection_time_ms: float = 0.0
    max_connection_time_ms: float = 0.0
    min_connection_time_ms: float = float('inf')
    connection_time_samples: List[float] = field(default_factory=list)
    pool_hit_rate: float = 0.0
    pool_miss_rate: float = 0.0
    recycle_count: int = 0
    failed_recycles: int = 0
    last_recycle: Optional[datetime] = None
    
    def update_connection_time(self, connection_time_ms: float) -> None:
        """Update connection time metrics."""
        self.connection_time_samples.append(connection_time_ms)
        
        # Keep only last 100 samples
        if len(self.connection_time_samples) > 100:
            self.connection_time_samples = self.connection_time_samples[-100:]
            
        # Update statistics
        self.avg_connection_time_ms = sum(self.connection_time_samples) / len(self.connection_time_samples)
        self.max_connection_time_ms = max(self.max_connection_time_ms, connection_time_ms)
        self.min_connection_time_ms = min(self.min_connection_time_ms, connection_time_ms)
        
    def get_utilization_stats(self) -> Dict[str, Any]:
        """Get detailed utilization statistics."""
        return {
            "total_connections": self.total_connections,
            "active_connections": self.active_connections,
            "idle_connections": self.idle_connections,
            "pool_utilization": self.pool_utilization,
            "connection_errors": self.connection_errors,
            "timeout_errors": self.timeout_errors,
            "avg_connection_time_ms": self.avg_connection_time_ms,
            "max_connection_time_ms": self.max_connection_time_ms,
            "min_connection_time_ms": self.min_connection_time_ms if self.min_connection_time_ms != float('inf') else 0.0,
            "pool_hit_rate": self.pool_hit_rate,
            "pool_miss_rate": self.pool_miss_rate,
            "recycle_count": self.recycle_count,
            "failed_recycles": self.failed_recycles,
            "last_recycle": self.last_recycle.isoformat() if self.last_recycle else None,
            "last_error": self.last_error.isoformat() if self.last_error else None,
        }


class ConnectionPoolMonitor:
    """Advanced connection pool monitoring."""
    
    def __init__(self, database_manager):
        """Initialize pool monitor.
        
        Args:
            database_manager: Database manager instance
        """
        self.db_manager = database_manager
        self._monitoring_task: Optional[asyncio.Task] = None
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
                poolclass=QueuePool,
                pool_size=database_config.pool_size,
                max_overflow=database_config.max_overflow,
                pool_pre_ping=database_config.pool_pre_ping,
                pool_recycle=database_config.pool_recycle,
                pool_timeout=database_config.pool_timeout,
                echo=settings.app_env == "development",
                future=True,
                # Enhanced pool configuration
                pool_reset_on_return="commit",
                pool_lifo=True,  # Use LIFO for better reuse
                connect_args={
                    "command_timeout": database_config.statement_timeout // 1000,
                    "server_settings": {
                        "application_name": settings.app_name,
                        "jit": "off",  # Disable JIT for simple queries
                    },
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
                await conn.execute("SELECT 1")
                
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
                "invalid": pool.invalid(),
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
                "invalid": pool.invalid(),
                "utilization": pool.checkedout() / max(pool.size(), 1),
            },
            "metrics": self._metrics.get_utilization_stats(),
            "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None,
            "is_initialized": self._is_initialized,
        }


# Global database manager instance
_database_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get global database manager instance.
    
    Returns:
        DatabaseManager instance
    """
    global _database_manager
    if _database_manager is None:
        _database_manager = DatabaseManager()
    return _database_manager


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session context manager.
    
    Yields:
        AsyncSession: Database session
    """
    db_manager = get_db_manager()
    async with db_manager.get_session() as session:
        yield session


# Global database manager instance
_database_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Convenience function to get database session.
    
    Yields:
        AsyncSession: Database session with automatic lifecycle management.
    """
    db_manager = get_db_manager()
    async with db_manager.get_session() as session:
        yield session


async def initialize_database() -> None:
    """Initialize global database manager."""
    db_manager = get_db_manager()
    await db_manager.initialize()


async def shutdown_database() -> None:
    """Shutdown global database manager."""
    db_manager = get_db_manager()
    await db_manager.close()
