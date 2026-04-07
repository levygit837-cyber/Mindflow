"""Intelligent browser pool with dynamic scaling."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from collections import deque

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.services.browser.lifecycle_service import (
    BrowserHandle,
    BrowserLifecycleService,
    BrowserRequirements,
)
from mindflow_backend.services.browser.metrics_collector import BrowserMetricsCollector

_logger = get_logger(__name__)


class PoolState(str, Enum):
    """State of the browser pool."""
    IDLE = "idle"
    WARMING = "warming"
    READY = "ready"
    BUSY = "busy"
    DEGRADED = "degraded"
    DRAINING = "draining"


@dataclass
class PoolConfig:
    """Configuration for the browser pool."""
    min_instances: int = 2
    max_instances: int = 20
    warm_instances: int = 3
    pre_warm_delay: int = 5  # seconds
    health_check_interval: int = 30
    scale_up_threshold: float = 0.7  # 70% utilization
    scale_down_threshold: float = 0.3  # 30% utilization
    instance_idle_timeout: int = 600  # 10 minutes


@dataclass
class PooledBrowser:
    """Browser in the pool with pool metadata."""
    handle: BrowserHandle
    pool_state: PoolState
    pooled_at: datetime
    last_health_check: datetime | None = None
    health_score: float = 1.0  # 0.0 - 1.0
    request_count: int = 0
    error_count: int = 0


class BrowserPoolManager:
    """Manages intelligent browser pool."""

    def __init__(
        self,
        lifecycle_service: BrowserLifecycleService,
        metrics_collector: BrowserMetricsCollector,
        config: PoolConfig | None = None,
    ):
        """Initialize the browser pool manager.

        Args:
            lifecycle_service: Browser lifecycle service
            metrics_collector: Metrics collector for health scoring
            config: Pool configuration
        """
        self.lifecycle_service = lifecycle_service
        self.metrics_collector = metrics_collector
        self.config = config or PoolConfig()

        self._pool: dict[str, PooledBrowser] = {}
        self._ready_queue: deque[str] = deque()
        self._lock = asyncio.Lock()
        self._logger = get_logger(__name__)

        # Background tasks
        self._health_check_task: asyncio.Task | None = None
        self._scaling_task: asyncio.Task | None = None
        self._pre_warm_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start pool manager and background tasks."""
        _logger.info("browser_pool_starting", config=self.config.dict())

        # Pre-warm initial instances
        await self._pre_warm_instances()

        # Start background tasks
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        self._scaling_task = asyncio.create_task(self._scaling_loop())

        _logger.info("browser_pool_started")

    async def stop(self) -> None:
        """Stop pool manager and cleanup."""
        _logger.info("browser_pool_stopping")

        # Cancel background tasks
        if self._health_check_task:
            self._health_check_task.cancel()
        if self._scaling_task:
            self._scaling_task.cancel()
        if self._pre_warm_task:
            self._pre_warm_task.cancel()

        # Drain pool
        await self.drain_pool()

        _logger.info("browser_pool_stopped")

    async def acquire(
        self,
        task_id: str,
        requirements: BrowserRequirements | None = None,
    ) -> PooledBrowser:
        """Acquire browser from pool (or create new if necessary).

        Args:
            task_id: Task ID
            requirements: Browser requirements

        Returns:
            PooledBrowser: Pooled browser
        """
        requirements = requirements or BrowserRequirements()

        async with self._lock:
            # Try to get from ready queue
            while self._ready_queue:
                instance_id = self._ready_queue.popleft()
                if instance_id in self._pool:
                    pooled = self._pool[instance_id]
                    if pooled.health_score > 0.5:  # Healthy enough
                        pooled.pool_state = PoolState.BUSY
                        pooled.request_count += 1
                        return pooled

            # No ready browsers, create new
            handle = await self.lifecycle_service.acquire_browser(task_id, requirements)
            pooled = PooledBrowser(
                handle=handle,
                pool_state=PoolState.BUSY,
                pooled_at=datetime.utcnow(),
            )
            self._pool[handle.instance_id] = pooled

            # Trigger scaling check
            asyncio.create_task(self._check_scaling())

            return pooled

    async def release(self, pooled: PooledBrowser, destroy: bool = False) -> None:
        """Release browser back to pool.

        Args:
            pooled: Pooled browser
            destroy: If True, destroy the browser instead of returning to pool
        """
        async with self._lock:
            if destroy or pooled.health_score < 0.3:
                # Destroy unhealthy or explicitly requested
                await self.lifecycle_service.release_browser(pooled.handle, destroy=True)
                if pooled.handle.instance_id in self._pool:
                    del self._pool[pooled.handle.instance_id]
            else:
                # Return to pool
                pooled.pool_state = PoolState.READY
                pooled.handle.last_used = datetime.utcnow()
                self._ready_queue.append(pooled.handle.instance_id)

    async def _pre_warm_instances(self) -> None:
        """Pre-warm initial instances."""
        _logger.info("pre_warming_instances", count=self.config.warm_instances)

        for i in range(self.config.warm_instances):
            task_id = f"prewarm-{i}"
            try:
                handle = await self.lifecycle_service.acquire_browser(task_id)
                pooled = PooledBrowser(
                    handle=handle,
                    pool_state=PoolState.WARMING,
                    pooled_at=datetime.utcnow(),
                )
                self._pool[handle.instance_id] = pooled

                # Wait for warm-up
                await asyncio.sleep(self.config.pre_warm_delay)

                # Mark as ready
                pooled.pool_state = PoolState.READY
                self._ready_queue.append(handle.instance_id)

                _logger.info("instance_warmed", instance_id=handle.instance_id)
            except Exception as exc:
                _logger.error("pre_warm_failed", task_id=task_id, error=str(exc))

    async def _health_check_loop(self) -> None:
        """Loop for periodic health checks."""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                _logger.error("health_check_loop_error", error=str(exc))

    async def _perform_health_checks(self) -> None:
        """Execute health checks on all browsers in pool."""
        async with self._lock:
            for instance_id, pooled in list(self._pool.items()):
                try:
                    # Get metrics
                    metrics = await self.lifecycle_service.get_browser_metrics(instance_id)

                    # Calculate health score
                    health_score = self._calculate_health_score(metrics)

                    # Update pooled browser
                    pooled.health_score = health_score
                    pooled.last_health_check = datetime.utcnow()

                    # Log degraded instances
                    if health_score < 0.5:
                        _logger.warning(
                            "browser_degraded",
                            instance_id=instance_id,
                            health_score=health_score,
                        )
                except Exception as exc:
                    _logger.error("health_check_failed", instance_id=instance_id, error=str(exc))
                    pooled.health_score = 0.0

    def _calculate_health_score(self, metrics: dict[str, Any]) -> float:
        """Calculate health score based on metrics."""
        score = 1.0

        # Penalize high error rate
        error_rate = metrics.get("error_rate", 0)
        score -= error_rate * 2.0

        # Penalize high memory usage
        memory_mb = metrics.get("memory_usage_mb", 0)
        if memory_mb > 500:
            score -= 0.3
        elif memory_mb > 300:
            score -= 0.1

        # Penalize high CPU usage
        cpu_percent = metrics.get("cpu_usage_percent", 0)
        if cpu_percent > 80:
            score -= 0.2
        elif cpu_percent > 60:
            score -= 0.1

        # Penalize long idle time
        idle_time = metrics.get("idle_time_seconds", 0)
        if idle_time > 3600:  # 1 hour
            score -= 0.2

        return max(0.0, min(1.0, score))

    async def _scaling_loop(self) -> None:
        """Loop for auto-scaling."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self._check_scaling()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                _logger.error("scaling_loop_error", error=str(exc))

    async def _check_scaling(self) -> None:
        """Check if scaling is needed."""
        async with self._lock:
            total_instances = len(self._pool)
            busy_count = sum(
                1 for p in self._pool.values() if p.pool_state == PoolState.BUSY
            )
            utilization = busy_count / total_instances if total_instances > 0 else 0

            # Scale up if needed
            if utilization > self.config.scale_up_threshold and total_instances < self.config.max_instances:
                _logger.info("scaling_up", utilization=utilization, current=total_instances)
                await self._scale_up()

            # Scale down if needed
            elif utilization < self.config.scale_down_threshold and total_instances > self.config.min_instances:
                _logger.info("scaling_down", utilization=utilization, current=total_instances)
                await self._scale_down()

    async def _scale_up(self) -> None:
        """Scale pool by adding new instance."""
        task_id = f"scaleup-{int(datetime.utcnow().timestamp())}"
        try:
            handle = await self.lifecycle_service.acquire_browser(task_id)
            pooled = PooledBrowser(
                handle=handle,
                pool_state=PoolState.WARMING,
                pooled_at=datetime.utcnow(),
            )
            self._pool[handle.instance_id] = pooled

            await asyncio.sleep(self.config.pre_warm_delay)
            pooled.pool_state = PoolState.READY
            self._ready_queue.append(handle.instance_id)

            _logger.info("scaled_up", instance_id=handle.instance_id)
        except Exception as exc:
            _logger.error("scale_up_failed", error=str(exc))

    async def _scale_down(self) -> None:
        """Scale pool by removing idle instance."""
        # Find least recently used ready instance
        ready_instances = [
            (instance_id, pooled)
            for instance_id, pooled in self._pool.items()
            if pooled.pool_state == PoolState.READY
        ]

        if ready_instances:
            # Sort by last_used
            ready_instances.sort(key=lambda x: x[1].handle.last_used)
            instance_id, pooled = ready_instances[0]

            await self.lifecycle_service.release_browser(pooled.handle, destroy=True)
            if instance_id in self._pool:
                del self._pool[instance_id]

            _logger.info("scaled_down", instance_id=instance_id)

    async def drain_pool(self) -> None:
        """Drain pool by destroying all browsers."""
        async with self._lock:
            for instance_id, pooled in list(self._pool.items()):
                await self.lifecycle_service.release_browser(pooled.handle, destroy=True)

            self._pool.clear()
            self._ready_queue.clear()

    async def get_pool_status(self) -> dict[str, Any]:
        """Get pool status."""
        from dataclasses import asdict
        async with self._lock:
            state_counts = {}
            for pooled in self._pool.values():
                state_counts[pooled.pool_state.value] = state_counts.get(pooled.pool_state.value, 0) + 1

            return {
                "total_instances": len(self._pool),
                "ready_instances": len(self._ready_queue),
                "state_counts": state_counts,
                "config": asdict(self.config),
                "average_health_score": sum(p.health_score for p in self._pool.values()) / len(self._pool) if self._pool else 0.0,
            }
