"""Connection pool manager for managing multiple gRPC connection pools.

Provides centralized management of connection pools with
dynamic optimization and monitoring capabilities.
"""

from __future__ import annotations

import asyncio
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from .pool import GrpcConnectionPool, PoolConfig, PoolStatistics
from .factory import GrpcConnectionFactory
from .health import PoolHealthChecker
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class PoolManagerState(Enum):
    """Pool manager states."""
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass
class PoolManagerConfig:
    """Configuration for pool manager."""
    default_min_pool_size: int = 5
    default_max_pool_size: int = 50
    health_check_interval: float = 60.0
    optimization_interval: float = 300.0  # 5 minutes
    enable_auto_optimization: bool = True
    enable_metrics: bool = True
    max_pools: int = 100


@dataclass
class PoolCreationRequest:
    """Request for creating a new connection pool."""
    pool_id: str
    config: PoolConfig
    auto_initialize: bool = True


@dataclass
class OptimizationResult:
    """Result of pool optimization."""
    pool_id: str
    optimizations_applied: List[str]
    performance_improvement: float
    recommendations: List[str]


class GrpcConnectionPoolManager:
    """Manages multiple gRPC connection pools with optimization."""
    
    def __init__(self, config: PoolManagerConfig):
        self.config = config
        self.state = PoolManagerState.INITIALIZING
        
        # Pool management
        self.pools: Dict[str, GrpcConnectionPool] = {}
        self.pool_configs: Dict[str, PoolConfig] = {}
        self._lock = asyncio.Lock()
        
        # Components
        self.connection_factory = GrpcConnectionFactory()
        self.health_checker = PoolHealthChecker(config.health_check_interval)
        
        # Background tasks
        self._optimization_task: Optional[asyncio.Task] = None
        self._health_check_task: Optional[asyncio.Task] = None
        
        # Statistics
        self._creation_requests: List[PoolCreationRequest] = []
        self._optimization_history: List[OptimizationResult] = []
        
        _logger.info("grpc_connection_pool_manager_created", 
                    max_pools=config.max_pools,
                    auto_optimization=config.enable_auto_optimization)
    
    async def start(self) -> bool:
        """Start the pool manager."""
        try:
            async with self._lock:
                if self.state != PoolManagerState.INITIALIZING:
                    return False
                
                self.state = PoolManagerState.RUNNING
                
                # Start background tasks
                if self.config.enable_auto_optimization:
                    self._optimization_task = asyncio.create_task(self._optimization_loop())
                
                self._health_check_task = asyncio.create_task(self._health_check_loop())
                
                # Process pending creation requests
                await self._process_creation_requests()
                
                _logger.info("grpc_connection_pool_manager_started")
                return True
                
        except Exception as exc:
            _logger.error("pool_manager_start_failed", error=str(exc))
            self.state = PoolManagerState.STOPPED
            return False
    
    async def stop(self) -> bool:
        """Stop the pool manager and cleanup all pools."""
        try:
            self.state = PoolManagerState.STOPPING
            
            # Cancel background tasks
            if self._optimization_task:
                self._optimization_task.cancel()
                try:
                    await self._optimization_task
                except asyncio.CancelledError:
                    pass
            
            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
            
            # Close all pools
            async with self._lock:
                for pool in list(self.pools.values()):
                    await pool.close()
                self.pools.clear()
                self.pool_configs.clear()
            
            self.state = PoolManagerState.STOPPED
            
            _logger.info("grpc_connection_pool_manager_stopped")
            return True
            
        except Exception as exc:
            _logger.error("pool_manager_stop_failed", error=str(exc))
            return False
    
    async def create_pool(self, pool_id: str, config: PoolConfig, auto_initialize: bool = True) -> bool:
        """Create a new connection pool."""
        if self.state != PoolManagerState.RUNNING:
            # Queue request for later processing
            self._creation_requests.append(PoolCreationRequest(pool_id, config, auto_initialize))
            return True
        
        try:
            async with self._lock:
                if pool_id in self.pools:
                    _logger.warning("pool_already_exists", pool_id=pool_id)
                    return False
                
                if len(self.pools) >= self.config.max_pools:
                    _logger.error("max_pools_reached", current=len(self.pools), max=self.config.max_pools)
                    return False
                
                # Create pool
                pool = GrpcConnectionPool(config, pool_id)
                self.pools[pool_id] = pool
                self.pool_configs[pool_id] = config
                
                # Initialize if requested
                if auto_initialize:
                    await pool.initialize()
                
                _logger.info("grpc_connection_pool_created", 
                            pool_id=pool_id,
                            host=config.host,
                            port=config.port,
                            auto_initialize=auto_initialize)
                
                return True
                
        except Exception as exc:
            _logger.error("pool_creation_failed", pool_id=pool_id, error=str(exc))
            # Clean up on failure
            async with self._lock:
                self.pools.pop(pool_id, None)
                self.pool_configs.pop(pool_id, None)
            return False
    
    async def destroy_pool(self, pool_id: str) -> bool:
        """Destroy a connection pool."""
        try:
            async with self._lock:
                if pool_id not in self.pools:
                    _logger.warning("pool_not_found", pool_id=pool_id)
                    return False
                
                pool = self.pools.pop(pool_id, None)
                self.pool_configs.pop(pool_id, None)
                
                await pool.close()
                
                _logger.info("grpc_connection_pool_destroyed", pool_id=pool_id)
                return True
                
        except Exception as exc:
            _logger.error("pool_destruction_failed", pool_id=pool_id, error=str(exc))
            return False
    
    async def get_pool(self, pool_id: str) -> Optional[GrpcConnectionPool]:
        """Get connection pool by ID."""
        async with self._lock:
            return self.pools.get(pool_id)
    
    async def list_pools(self) -> List[str]:
        """List all pool IDs."""
        async with self._lock:
            return list(self.pools.keys())
    
    async def get_pool_statistics(self, pool_id: str) -> Optional[PoolStatistics]:
        """Get statistics for a specific pool."""
        pool = await self.get_pool(pool_id)
        if pool:
            return await pool.get_statistics()
        return None
    
    async def get_all_statistics(self) -> Dict[str, PoolStatistics]:
        """Get statistics for all pools."""
        statistics = {}
        
        async with self._lock:
            for pool_id, pool in self.pools.items():
                try:
                    statistics[pool_id] = await pool.get_statistics()
                except Exception as exc:
                    _logger.error("pool_statistics_failed", pool_id=pool_id, error=str(exc))
        
        return statistics
    
    async def optimize_pools(self) -> List[OptimizationResult]:
        """Optimize all pools based on performance metrics."""
        results = []
        
        async with self._lock:
            for pool_id, pool in self.pools.items():
                try:
                    result = await self._optimize_pool(pool_id, pool)
                    if result:
                        results.append(result)
                except Exception as exc:
                    _logger.error("pool_optimization_failed", pool_id=pool_id, error=str(exc))
        
        return results
    
    async def _optimize_pool(self, pool_id: str, pool: GrpcConnectionPool) -> Optional[OptimizationResult]:
        """Optimize a specific pool."""
        stats = await pool.get_statistics()
        config = self.pool_configs[pool_id]
        
        optimizations = []
        performance_improvement = 0.0
        recommendations = []
        
        # Analyze pool utilization
        utilization = stats.get_utilization_rate()
        success_rate = stats.get_success_rate()
        
        # Pool size optimization
        if utilization > 0.8 and config.max_pool_size < 100:  # High utilization
            old_max = config.max_pool_size
            new_max = min(config.max_pool_size * 2, 100)
            config.max_pool_size = new_max
            optimizations.append(f"Increased max pool size from {old_max} to {new_max}")
            performance_improvement += 0.1
        
        elif utilization < 0.2 and config.min_pool_size > 2:  # Low utilization
            old_min = config.min_pool_size
            new_min = max(config.min_pool_size // 2, 2)
            config.min_pool_size = new_min
            optimizations.append(f"Decreased min pool size from {old_min} to {new_min}")
            performance_improvement += 0.05
        
        # Health check interval optimization
        if success_rate < 0.9 and config.health_check_interval > 30:  # Poor success rate
            old_interval = config.health_check_interval
            new_interval = max(config.health_check_interval // 2, 30)
            config.health_check_interval = new_interval
            optimizations.append(f"Decreased health check interval from {old_interval}s to {new_interval}s")
            performance_improvement += 0.1
        
        # Generate recommendations
        if stats.average_response_time > 1.0:  # High response time
            recommendations.append("Consider enabling compression for large messages")
        
        if stats.unhealthy_connections > 0:
            recommendations.append("Review network connectivity and server health")
        
        if stats.failed_requests / max(stats.total_requests, 1) > 0.1:
            recommendations.append("Investigate error patterns and consider circuit breaker")
        
        result = OptimizationResult(
            pool_id=pool_id,
            optimizations_applied=optimizations,
            performance_improvement=performance_improvement,
            recommendations=recommendations
        )
        
        self._optimization_history.append(result)
        
        # Keep only recent optimization history
        if len(self._optimization_history) > 100:
            self._optimization_history = self._optimization_history[-100:]
        
        _logger.info("pool_optimization_completed", 
                    pool_id=pool_id,
                    optimizations=len(optimizations),
                    improvement=performance_improvement)
        
        return result
    
    async def _process_creation_requests(self):
        """Process pending pool creation requests."""
        requests = self._creation_requests.copy()
        self._creation_requests.clear()
        
        for request in requests:
            await self.create_pool(request.pool_id, request.config, request.auto_initialize)
    
    async def _optimization_loop(self):
        """Background optimization loop."""
        while self.state == PoolManagerState.RUNNING:
            try:
                await self.optimize_pools()
                await asyncio.sleep(self.config.optimization_interval)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                _logger.error("optimization_loop_error", error=str(exc))
                await asyncio.sleep(self.config.optimization_interval)
    
    async def _health_check_loop(self):
        """Background health checking loop."""
        while self.state == PoolManagerState.RUNNING:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.config.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                _logger.error("health_check_loop_error", error=str(exc))
                await asyncio.sleep(self.config.health_check_interval)
    
    async def _perform_health_checks(self):
        """Perform health checks on all pools."""
        unhealthy_pools = []
        
        async with self._lock:
            for pool_id, pool in self.pools.items():
                try:
                    stats = await pool.get_statistics()
                    
                    # Check pool health indicators
                    if (stats.get_success_rate() < 0.5 or  # Low success rate
                        stats.unhealthy_connections > stats.total_connections / 2):  # Many unhealthy connections
                        unhealthy_pools.append(pool_id)
                        
                except Exception as exc:
                    _logger.error("pool_health_check_failed", pool_id=pool_id, error=str(exc))
                    unhealthy_pools.append(pool_id)
        
        # Report unhealthy pools
        if unhealthy_pools:
            _logger.warning("unhealthy_pools_detected", pools=unhealthy_pools)
    
    async def get_manager_statistics(self) -> Dict[str, Any]:
        """Get pool manager statistics."""
        async with self._lock:
            all_stats = await self.get_all_statistics()
            
            total_connections = sum(stats.total_connections for stats in all_stats.values())
            total_active = sum(stats.active_connections for stats in all_stats.values())
            total_requests = sum(stats.total_requests for stats in all_stats.values())
            total_successful = sum(stats.successful_requests for stats in all_stats.values())
            
            return {
                "state": self.state.value,
                "total_pools": len(self.pools),
                "total_connections": total_connections,
                "active_connections": total_active,
                "total_requests": total_requests,
                "successful_requests": total_successful,
                "overall_success_rate": total_successful / max(total_requests, 1),
                "optimization_history_size": len(self._optimization_history),
                "pending_creation_requests": len(self._creation_requests),
            }


# Global pool manager instance
_global_pool_manager: Optional[GrpcConnectionPoolManager] = None


async def get_pool_manager() -> GrpcConnectionPoolManager:
    """Get global pool manager instance."""
    global _global_pool_manager
    if _global_pool_manager is None:
        config = PoolManagerConfig()
        _global_pool_manager = GrpcConnectionPoolManager(config)
        await _global_pool_manager.start()
    return _global_pool_manager


def set_pool_manager(manager: GrpcConnectionPoolManager) -> None:
    """Set global pool manager instance."""
    global _global_pool_manager
    _global_pool_manager = manager
