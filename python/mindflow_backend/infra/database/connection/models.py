"""Database connection models and metrics.

Provides connection status enums, pool states, and metrics tracking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import Optional, datetime
from enum import Enum
from typing import Any


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
    connection_time_samples: list[float] = field(default_factory=list)
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

    def get_utilization_stats(self) -> dict[str, Any]:
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