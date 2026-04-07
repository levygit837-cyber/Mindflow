"""Browser lifecycle service for centralized browser management.

Provides browser allocation, release, snapshot management, session persistence,
and cleanup for the MindFlow Research Agent.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.services.browser.docker_manager import (
    BrowserInstance,
    InstanceStatus,
    LightPandaDockerManager,
)
from mindflow_backend.services.browser.session_manager import (
    SessionManager,
    BrowserSession,
)
from mindflow_backend.services.browser.pool_manager import (
    BrowserPoolManager,
    PoolConfig,
)
from mindflow_backend.services.browser.metrics_collector import BrowserMetricsCollector

_logger = get_logger(__name__)


@dataclass
class BrowserRequirements:
    """Requirements for browser allocation."""

    max_memory_mb: int = 512
    require_snapshot: bool = False
    timeout_seconds: int = 30
    preferred_port: int | None = None
    session_id: str | None = None  # Session to restore


@dataclass
class BrowserHandle:
    """Handle for an allocated browser."""
    
    instance_id: str
    task_id: str
    acquired_at: datetime
    requirements: BrowserRequirements
    snapshot_id: str | None = None
    last_used: datetime = field(init=False)
    
    def __post_init__(self):
        """Initialize computed fields."""
        self.last_used = datetime.utcnow()


class BrowserLifecycleService:
    """Centralized browser lifecycle management service.
    
    This service coordinates:
    - Browser allocation and release
    - Pool management for reusable browsers
    - Snapshot creation and restoration
    - Cleanup of idle browsers
    - Integration with Docker Manager and Snapshot Manager
    """
    
    def __init__(
        self,
        docker_manager: LightPandaDockerManager | None = None,
        max_idle_timeout: int = 600,
        max_lifetime: int = 3600,
        snapshot_interval: int = 300,
        snapshot_retention: int = 3600,
        session_ttl_hours: int = 24,
        enable_pool: bool = True,
    ):
        """Initialize the browser lifecycle service.

        Args:
            docker_manager: Docker manager instance (created if None)
            max_idle_timeout: Max idle time before cleanup (seconds)
            max_lifetime: Max browser lifetime (seconds)
            snapshot_interval: Interval between automatic snapshots (seconds)
            snapshot_retention: Snapshot retention time (seconds)
            session_ttl_hours: Session time-to-live in hours
            enable_pool: Whether to enable intelligent browser pool
        """
        self.docker_manager = docker_manager or LightPandaDockerManager(
            base_port=int(os.getenv("LIGHTPANDA_PORT", "9222")),
            max_instances=int(os.getenv("LIGHTPANDA_MAX_INSTANCES", "5")),
            host=os.getenv("LIGHTPANDA_HOST", "127.0.0.1"),
        )

        self.max_idle_timeout = max_idle_timeout
        self.max_lifetime = max_lifetime
        self.snapshot_interval = snapshot_interval
        self.snapshot_retention = snapshot_retention

        # Browser pool management
        self._pool: dict[str, BrowserHandle] = {}
        self._pool_lock = asyncio.Lock()

        # Background tasks
        self._cleanup_task: asyncio.Task | None = None
        self._snapshot_task: asyncio.Task | None = None

        # Session management
        self.session_manager = SessionManager(
            session_ttl_hours=session_ttl_hours
        )

        # Metrics collector
        self.metrics_collector = BrowserMetricsCollector()

        # Browser pool manager
        self.pool_manager: BrowserPoolManager | None = None
        self.enable_pool = enable_pool
    
    async def start(self) -> None:
        """Start the lifecycle service and background tasks."""
        _logger.info("browser_lifecycle_service_starting")

        # Start pool manager if enabled
        if self.enable_pool:
            pool_config = PoolConfig(
                min_instances=int(os.getenv("BROWSER_POOL_MIN", "2")),
                max_instances=int(os.getenv("BROWSER_POOL_MAX", "20")),
                warm_instances=int(os.getenv("BROWSER_POOL_WARM", "3")),
            )
            self.pool_manager = BrowserPoolManager(
                lifecycle_service=self,
                metrics_collector=self.metrics_collector,
                config=pool_config,
            )
            await self.pool_manager.start()

        # Start background cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        # Start background snapshot task
        self._snapshot_task = asyncio.create_task(self._snapshot_loop())
        
        _logger.info("browser_lifecycle_service_started")
    
    async def stop(self) -> None:
        """Stop the lifecycle service and cleanup resources."""
        _logger.info("browser_lifecycle_service_stopping")

        # Stop pool manager if enabled
        if self.pool_manager:
            await self.pool_manager.stop()

        # Cancel background tasks
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        if self._snapshot_task:
            self._snapshot_task.cancel()
            try:
                await self._snapshot_task
            except asyncio.CancelledError:
                pass

        # Cleanup all browsers
        async with self._pool_lock:
            for handle in list(self._pool.values()):
                await self.release_browser(handle, destroy=True)

        _logger.info("browser_lifecycle_service_stopped")
    
    async def acquire_browser(
        self,
        task_id: str,
        requirements: BrowserRequirements | None = None,
    ) -> BrowserHandle:
        """Acquire a browser for a task.

        Args:
            task_id: ID of the task requesting the browser
            requirements: Browser requirements (uses defaults if None)

        Returns:
            BrowserHandle: Handle for the allocated browser

        Raises:
            RuntimeError: If browser allocation fails
        """
        requirements = requirements or BrowserRequirements()

        _logger.info(
            "acquiring_browser",
            task_id=task_id,
            require_snapshot=requirements.require_snapshot,
            session_id=requirements.session_id,
        )

        try:
            # Use pool manager if enabled
            if self.enable_pool and self.pool_manager:
                pooled = await self.pool_manager.acquire(task_id, requirements)
                return pooled.handle

            # Fallback to direct acquisition
            # Check if session restore is requested
            if requirements.session_id:
                # Return handle with session_id for restoration by caller
                # The actual restoration happens in CDP connection
                instance = await self.docker_manager.create_browser_instance(
                    task_id,
                    requirements.max_memory_mb,
                    requirements.preferred_port,
                )
                handle = BrowserHandle(
                    instance_id=instance.instance_id,
                    task_id=task_id,
                    acquired_at=datetime.utcnow(),
                    requirements=requirements,
                )
            else:
                # Create new browser instance
                instance = await self.docker_manager.create_browser_instance(
                    task_id,
                    requirements.max_memory_mb,
                    requirements.preferred_port,
                )
                handle = BrowserHandle(
                    instance_id=instance.instance_id,
                    task_id=task_id,
                    acquired_at=datetime.utcnow(),
                    requirements=requirements,
                )

            # Add to pool
            async with self._pool_lock:
                self._pool[instance.instance_id] = handle

            _logger.info(
                "browser_acquired",
                instance_id=instance.instance_id,
                task_id=task_id,
                session_id=requirements.session_id,
            )

            return handle

        except Exception as e:
            _logger.error("browser_acquisition_failed", task_id=task_id, error=str(e))
            raise RuntimeError(f"Failed to acquire browser: {e}") from e

    async def release_browser(
        self,
        handle: BrowserHandle,
        destroy: bool = False,
    ) -> None:
        """Release a browser back to the pool or destroy it.
        
        Args:
            handle: Browser handle to release
            destroy: If True, destroy the browser instead of returning to pool
        """
        _logger.info(
            "releasing_browser",
            instance_id=handle.instance_id,
            destroy=destroy,
        )
        
        try:
            # Use pool manager if enabled and handle is in pool
            if self.enable_pool and self.pool_manager and handle.instance_id in self._pool:
                # Check if this is a pooled browser
                from mindflow_backend.services.browser.pool_manager import PooledBrowser
                # Since we don't have PooledBrowser here, check if it was acquired from pool
                # For simplicity, release to pool if not explicitly destroying
                if not destroy:
                    # Create a temporary PooledBrowser for release
                    from mindflow_backend.services.browser.pool_manager import PoolState
                    pooled = PooledBrowser(
                        handle=handle,
                        pool_state=PoolState.READY,
                        pooled_at=handle.acquired_at,
                    )
                    await self.pool_manager.release(pooled, destroy=False)
                else:
                    await self.pool_manager.release(
                        PooledBrowser(
                            handle=handle,
                            pool_state=PoolState.READY,
                            pooled_at=handle.acquired_at,
                        ),
                        destroy=True,
                    )
            else:
                # Fallback to direct release
                async with self._pool_lock:
                    if handle.instance_id in self._pool:
                        if destroy:
                            # Destroy the browser
                            await self.docker_manager.destroy_browser_instance(
                                handle.instance_id
                            )
                            del self._pool[handle.instance_id]
                        else:
                            # Return to pool (update last used time)
                            handle.last_used = datetime.utcnow()
                            await self.docker_manager.update_instance_activity(
                                handle.instance_id
                            )
            
            _logger.info(
                "browser_released",
                instance_id=handle.instance_id,
                action="destroyed" if destroy else "returned_to_pool",
            )
            
        except Exception as exc:
            _logger.error(
                "browser_release_failed",
                instance_id=handle.instance_id,
                error=str(exc),
                exc_info=True,
            )
    
    async def create_snapshot(self, handle: BrowserHandle) -> str:
        """Create a snapshot of the browser state.
        
        Args:
            handle: Browser handle to snapshot
            
        Returns:
            str: Snapshot ID
        """
        _logger.info("creating_snapshot", instance_id=handle.instance_id)
        
        # In production, integrate with SnapshotManager
        # snapshot_id = await self.snapshot_manager.capture_snapshot(
        #     handle.instance_id
        # )
        
        # Mock snapshot ID
        snapshot_id = f"snapshot-{handle.instance_id}-{int(datetime.utcnow().timestamp())}"
        
        _logger.info("snapshot_created", instance_id=handle.instance_id, snapshot_id=snapshot_id)
        
        return snapshot_id
    
    async def restore_snapshot(
        self,
        snapshot_id: str,
        task_id: str,
    ) -> BrowserHandle:
        """Restore a browser from a snapshot.
        
        Args:
            snapshot_id: Snapshot ID to restore
            task_id: Task ID requesting the restore
            
        Returns:
            BrowserHandle: Handle for the restored browser
        """
        _logger.info("restoring_snapshot", snapshot_id=snapshot_id, task_id=task_id)
        
        # In production, integrate with SnapshotManager
        # instance = await self.snapshot_manager.restore_snapshot(
        #     snapshot_id,
        #     task_id
        # )
        
        # For now, create a new browser
        handle = await self.acquire_browser(task_id)
        handle.snapshot_id = snapshot_id
        
        _logger.info(
            "snapshot_restored",
            snapshot_id=snapshot_id,
            instance_id=handle.instance_id,
        )
        
        return handle
    
    async def get_browser_metrics(self, instance_id: str) -> dict[str, Any]:
        """Get metrics for a specific browser.
        
        Args:
            instance_id: Browser instance ID
            
        Returns:
            dict[str, Any]: Browser metrics
        """
        metrics = await self.docker_manager.get_instance_metrics(instance_id)
        
        # Add lifecycle metrics
        if instance_id in self._pool:
            handle = self._pool[instance_id]
            now = datetime.utcnow()
            metrics.update({
                "task_id": handle.task_id,
                "acquired_at": handle.acquired_at.isoformat(),
                "last_used": handle.last_used.isoformat(),
                "idle_time_seconds": (now - handle.last_used).total_seconds(),
                "lifetime_seconds": (now - handle.acquired_at).total_seconds(),
                "has_snapshot": handle.snapshot_id is not None,
            })
        
        return metrics
    
    async def cleanup_idle_browsers(self) -> int:
        """Clean up idle browsers from the pool.
        
        Returns:
            int: Number of browsers cleaned up
        """
        _logger.info("cleaning_up_idle_browsers")
        
        cleanup_count = 0
        now = datetime.utcnow()
        
        async with self._pool_lock:
            for handle in list(self._pool.values()):
                # Check idle time
                idle_time = (now - handle.last_used).total_seconds()
                
                # Check lifetime
                lifetime = (now - handle.acquired_at).total_seconds()
                
                should_cleanup = (
                    idle_time > self.max_idle_timeout
                    or lifetime > self.max_lifetime
                )
                
                if should_cleanup:
                    _logger.info(
                        "cleaning_up_browser",
                        instance_id=handle.instance_id,
                        idle_seconds=idle_time,
                        lifetime_seconds=lifetime,
                        reason="idle" if idle_time > self.max_idle_timeout else "max_lifetime",
                    )
                    
                    try:
                        await self.docker_manager.destroy_browser_instance(
                            handle.instance_id
                        )
                        del self._pool[handle.instance_id]
                        cleanup_count += 1
                    except Exception as exc:
                        _logger.error(
                            "browser_cleanup_failed",
                            instance_id=handle.instance_id,
                            error=str(exc),
                        )
        
        if cleanup_count > 0:
            _logger.info("idle_browser_cleanup_completed", count=cleanup_count)
        
        return cleanup_count
    
    async def _cleanup_loop(self) -> None:
        """Background task for periodic cleanup."""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                await self.cleanup_idle_browsers()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                _logger.error("cleanup_loop_error", error=str(exc), exc_info=True)
    
    async def _snapshot_loop(self) -> None:
        """Background task for periodic snapshots."""
        while True:
            try:
                await asyncio.sleep(self.snapshot_interval)
                
                # Create snapshots for active browsers
                async with self._pool_lock:
                    for handle in self._pool.values():
                        try:
                            await self.create_snapshot(handle)
                        except Exception as exc:
                            _logger.error(
                                "snapshot_creation_failed",
                                instance_id=handle.instance_id,
                                error=str(exc),
                            )
                            
            except asyncio.CancelledError:
                break
            except Exception as exc:
                _logger.error("snapshot_loop_error", error=str(exc), exc_info=True)
    
    async def get_pool_status(self) -> dict[str, Any]:
        """Get the current status of the browser pool.
        
        Returns:
            dict[str, Any]: Pool status information
        """
        async with self._pool_lock:
            now = datetime.utcnow()
            
            return {
                "total_instances": len(self._pool),
                "instances": [
                    {
                        "instance_id": h.instance_id,
                        "task_id": h.task_id,
                        "acquired_at": h.acquired_at.isoformat(),
                        "last_used": h.last_used.isoformat(),
                        "idle_seconds": (now - h.last_used).total_seconds(),
                        "lifetime_seconds": (now - h.acquired_at).total_seconds(),
                        "has_snapshot": h.snapshot_id is not None,
                    }
                    for h in self._pool.values()
                ],
            }
