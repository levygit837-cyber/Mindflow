"""Health checker for gRPC connection pools.

Provides comprehensive health monitoring and automatic
recovery for connection pools.
"""

from __future__ import annotations

import asyncio
import time
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

from .pool import GrpcConnectionPool, PoolStatistics
from omnimind_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of health check."""
    pool_id: str
    status: HealthStatus
    timestamp: float
    issues: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class PoolHealthMetrics:
    """Health metrics for a connection pool."""
    pool_id: str
    success_rate: float
    error_rate: float
    utilization_rate: float
    average_response_time: float
    connection_creation_time: float
    unhealthy_connections: int
    total_connections: int
    last_health_check: float
    
    def get_health_score(self) -> float:
        """Calculate overall health score (0-100)."""
        score = 100.0
        
        # Success rate impact (40% weight)
        score -= (1.0 - self.success_rate) * 40
        
        # Error rate impact (30% weight)
        score -= self.error_rate * 30
        
        # Utilization rate impact (15% weight)
        if self.utilization_rate > 0.8:  # High utilization
            score -= (self.utilization_rate - 0.8) * 75  # Up to 15 points
        
        # Response time impact (10% weight)
        if self.average_response_time > 1.0:  # High response time
            score -= min((self.average_response_time - 1.0) * 10, 10)
        
        # Unhealthy connections impact (5% weight)
        if self.total_connections > 0:
            unhealthy_ratio = self.unhealthy_connections / self.total_connections
            score -= unhealthy_ratio * 5
        
        return max(score, 0.0)


class PoolHealthChecker:
    """Health checker for gRPC connection pools."""
    
    def __init__(self, check_interval: float = 60.0):
        self.check_interval = check_interval
        self._pools: Dict[str, GrpcConnectionPool] = {}
        self._health_history: Dict[str, List[HealthCheckResult]] = {}
        self._lock = asyncio.Lock()
        self._running = False
        self._check_task: Optional[asyncio.Task] = None
        
        # Health thresholds
        self.thresholds = {
            "min_success_rate": 0.8,      # 80%
            "max_error_rate": 0.2,        # 20%
            "max_utilization_rate": 0.9,  # 90%
            "max_response_time": 2.0,      # 2 seconds
            "max_unhealthy_ratio": 0.3,    # 30%
            "max_creation_time": 5.0,      # 5 seconds
        }
        
        _logger.info("pool_health_checker_created", check_interval=check_interval)
    
    async def start(self) -> bool:
        """Start the health checker."""
        if self._running:
            return False
        
        try:
            self._running = True
            self._check_task = asyncio.create_task(self._health_check_loop())
            
            _logger.info("pool_health_checker_started")
            return True
            
        except Exception as exc:
            _logger.error("health_checker_start_failed", error=str(exc))
            self._running = False
            return False
    
    async def stop(self) -> bool:
        """Stop the health checker."""
        if not self._running:
            return False
        
        try:
            self._running = False
            
            if self._check_task:
                self._check_task.cancel()
                try:
                    await self._check_task
                except asyncio.CancelledError:
                    pass
                self._check_task = None
            
            _logger.info("pool_health_checker_stopped")
            return True
            
        except Exception as exc:
            _logger.error("health_checker_stop_failed", error=str(exc))
            return False
    
    async def register_pool(self, pool_id: str, pool: GrpcConnectionPool):
        """Register a pool for health checking."""
        async with self._lock:
            self._pools[pool_id] = pool
            if pool_id not in self._health_history:
                self._health_history[pool_id] = []
        
        _logger.debug("pool_registered_for_health_check", pool_id=pool_id)
    
    async def unregister_pool(self, pool_id: str):
        """Unregister a pool from health checking."""
        async with self._lock:
            self._pools.pop(pool_id, None)
            self._health_history.pop(pool_id, None)
        
        _logger.debug("pool_unregistered_from_health_check", pool_id=pool_id)
    
    async def check_pool_health(self, pool_id: str) -> Optional[HealthCheckResult]:
        """Check health of a specific pool."""
        pool = self._pools.get(pool_id)
        if not pool:
            return None
        
        try:
            # Get pool statistics
            stats = await pool.get_statistics()
            
            # Calculate health metrics
            metrics = self._calculate_health_metrics(pool_id, stats)
            
            # Determine health status
            status, issues, recommendations = self._evaluate_health(metrics)
            
            # Create health check result
            result = HealthCheckResult(
                pool_id=pool_id,
                status=status,
                timestamp=time.time(),
                issues=issues,
                metrics={
                    "success_rate": metrics.success_rate,
                    "error_rate": metrics.error_rate,
                    "utilization_rate": metrics.utilization_rate,
                    "average_response_time": metrics.average_response_time,
                    "connection_creation_time": metrics.connection_creation_time,
                    "unhealthy_connections": metrics.unhealthy_connections,
                    "total_connections": metrics.total_connections,
                    "health_score": metrics.get_health_score(),
                },
                recommendations=recommendations
            )
            
            # Store in history
            async with self._lock:
                self._health_history[pool_id].append(result)
                # Keep only recent history (last 100 checks)
                if len(self._health_history[pool_id]) > 100:
                    self._health_history[pool_id] = self._health_history[pool_id][-100:]
            
            return result
            
        except Exception as exc:
            _logger.error("pool_health_check_failed", pool_id=pool_id, error=str(exc))
            
            return HealthCheckResult(
                pool_id=pool_id,
                status=HealthStatus.UNKNOWN,
                timestamp=time.time(),
                issues=[f"Health check failed: {str(exc)}"]
            )
    
    async def check_all_pools(self) -> Dict[str, HealthCheckResult]:
        """Check health of all registered pools."""
        results = {}
        
        async with self._lock:
            pool_ids = list(self._pools.keys())
        
        # Check all pools concurrently
        tasks = [self.check_pool_health(pool_id) for pool_id in pool_ids]
        health_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for pool_id, result in zip(pool_ids, health_results):
            if isinstance(result, Exception):
                _logger.error("pool_health_check_exception", pool_id=pool_id, error=str(result))
                results[pool_id] = HealthCheckResult(
                    pool_id=pool_id,
                    status=HealthStatus.UNKNOWN,
                    timestamp=time.time(),
                    issues=[f"Health check exception: {str(result)}"]
                )
            else:
                results[pool_id] = result
        
        return results
    
    async def get_pool_health_history(self, pool_id: str, limit: int = 10) -> List[HealthCheckResult]:
        """Get health history for a pool."""
        async with self._lock:
            history = self._health_history.get(pool_id, [])
            return history[-limit:] if limit > 0 else history
    
    async def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary."""
        results = await self.check_all_pools()
        
        summary = {
            "total_pools": len(results),
            "healthy_pools": 0,
            "degraded_pools": 0,
            "unhealthy_pools": 0,
            "unknown_pools": 0,
            "pools": {}
        }
        
        for pool_id, result in results.items():
            status_counts = {
                HealthStatus.HEALTHY: "healthy_pools",
                HealthStatus.DEGRADED: "degraded_pools",
                HealthStatus.UNHEALTHY: "unhealthy_pools",
                HealthStatus.UNKNOWN: "unknown_pools",
            }
            
            summary[status_counts[result.status]] += 1
            summary["pools"][pool_id] = {
                "status": result.status.value,
                "health_score": result.metrics.get("health_score", 0.0),
                "issues": len(result.issues),
                "last_check": result.timestamp,
            }
        
        return summary
    
    def _calculate_health_metrics(self, pool_id: str, stats: PoolStatistics) -> PoolHealthMetrics:
        """Calculate health metrics from pool statistics."""
        total_requests = stats.total_requests
        successful_requests = stats.successful_requests
        failed_requests = stats.failed_requests
        
        success_rate = successful_requests / max(total_requests, 1)
        error_rate = failed_requests / max(total_requests, 1)
        utilization_rate = stats.get_utilization_rate()
        
        return PoolHealthMetrics(
            pool_id=pool_id,
            success_rate=success_rate,
            error_rate=error_rate,
            utilization_rate=utilization_rate,
            average_response_time=stats.average_response_time,
            connection_creation_time=stats.connection_creation_time,
            unhealthy_connections=stats.unhealthy_connections,
            total_connections=stats.total_connections,
            last_health_check=stats.last_health_check
        )
    
    def _evaluate_health(self, metrics: PoolHealthMetrics) -> tuple[HealthStatus, List[str], List[str]]:
        """Evaluate health based on metrics."""
        issues = []
        recommendations = []
        
        # Check success rate
        if metrics.success_rate < self.thresholds["min_success_rate"]:
            issues.append(f"Low success rate: {metrics.success_rate:.1%}")
            recommendations.append("Investigate error patterns and consider circuit breaker")
        
        # Check error rate
        if metrics.error_rate > self.thresholds["max_error_rate"]:
            issues.append(f"High error rate: {metrics.error_rate:.1%}")
            recommendations.append("Review network connectivity and server health")
        
        # Check utilization rate
        if metrics.utilization_rate > self.thresholds["max_utilization_rate"]:
            issues.append(f"High utilization: {metrics.utilization_rate:.1%}")
            recommendations.append("Consider increasing pool size or optimizing connection usage")
        
        # Check response time
        if metrics.average_response_time > self.thresholds["max_response_time"]:
            issues.append(f"High response time: {metrics.average_response_time:.2f}s")
            recommendations.append("Consider enabling compression or optimizing server performance")
        
        # Check unhealthy connections
        if metrics.total_connections > 0:
            unhealthy_ratio = metrics.unhealthy_connections / metrics.total_connections
            if unhealthy_ratio > self.thresholds["max_unhealthy_ratio"]:
                issues.append(f"High unhealthy connection ratio: {unhealthy_ratio:.1%}")
                recommendations.append("Review connection health and network stability")
        
        # Check connection creation time
        if metrics.connection_creation_time > self.thresholds["max_creation_time"]:
            issues.append(f"Slow connection creation: {metrics.connection_creation_time:.2f}s")
            recommendations.append("Optimize network configuration or server response time")
        
        # Determine overall health status
        if not issues:
            status = HealthStatus.HEALTHY
        elif len(issues) <= 2:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.UNHEALTHY
        
        return status, issues, recommendations
    
    async def _health_check_loop(self):
        """Background health checking loop."""
        while self._running:
            try:
                await self.check_all_pools()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                _logger.error("health_check_loop_error", error=str(exc))
                await asyncio.sleep(self.check_interval)
    
    def update_thresholds(self, **thresholds):
        """Update health check thresholds."""
        for key, value in thresholds.items():
            if key in self.thresholds:
                self.thresholds[key] = value
                _logger.info("health_threshold_updated", threshold=key, value=value)
            else:
                _logger.warning("unknown_health_threshold", threshold=key)
    
    def get_thresholds(self) -> Dict[str, float]:
        """Get current health check thresholds."""
        return self.thresholds.copy()
