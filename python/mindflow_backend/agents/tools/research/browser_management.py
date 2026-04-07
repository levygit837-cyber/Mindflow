"""Browser management tools for Research Agent autonomy.

Provides tools that allow the Research Agent to autonomously manage
browser instances, including creation, destruction, monitoring, and snapshot management.
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.services.browser import (
    BrowserHandle,
    BrowserLifecycleService,
    BrowserRequirements,
    BrowserSnapshotManager,
)

_logger = get_logger(__name__)


class CreateBrowserTool:
    """Tool for creating new browser instances.
    
    Allows the Research Agent to create browser instances on demand
    for specific tasks.
    """
    
    def __init__(
        self,
        lifecycle_service: BrowserLifecycleService | None = None,
    ):
        """Initialize the create browser tool.
        
        Args:
            lifecycle_service: Browser lifecycle service (created if None)
        """
        self.lifecycle_service = lifecycle_service or BrowserLifecycleService()
    
    async def execute(
        self,
        task_id: str,
        max_memory_mb: int = 512,
        require_snapshot: bool = False,
        timeout_seconds: int = 30,
    ) -> dict[str, Any]:
        """Create a new browser instance.
        
        Args:
            task_id: Task ID requesting the browser
            max_memory_mb: Maximum memory in MB
            require_snapshot: Whether to create initial snapshot
            timeout_seconds: Browser operation timeout
            
        Returns:
            dict[str, Any]: Browser handle information
        """
        _logger.info(
            "creating_browser",
            task_id=task_id,
            max_memory_mb=max_memory_mb,
            require_snapshot=require_snapshot,
        )
        
        try:
            requirements = BrowserRequirements(
                max_memory_mb=max_memory_mb,
                require_snapshot=require_snapshot,
                timeout_seconds=timeout_seconds,
            )
            
            handle = await self.lifecycle_service.acquire_browser(
                task_id=task_id,
                requirements=requirements,
            )
            
            return {
                "success": True,
                "instance_id": handle.instance_id,
                "task_id": handle.task_id,
                "acquired_at": handle.acquired_at.isoformat(),
                "has_snapshot": handle.snapshot_id is not None,
                "snapshot_id": handle.snapshot_id,
            }
            
        except Exception as exc:
            _logger.error(
                "create_browser_failed",
                task_id=task_id,
                error=str(exc),
                exc_info=True,
            )
            return {
                "success": False,
                "error": str(exc),
            }


class DestroyBrowserTool:
    """Tool for destroying browser instances.
    
    Allows the Research Agent to clean up browser instances
    when they are no longer needed.
    """
    
    def __init__(
        self,
        lifecycle_service: BrowserLifecycleService | None = None,
    ):
        """Initialize the destroy browser tool.
        
        Args:
            lifecycle_service: Browser lifecycle service (created if None)
        """
        self.lifecycle_service = lifecycle_service or BrowserLifecycleService()
    
    async def execute(
        self,
        instance_id: str,
        destroy: bool = True,
    ) -> dict[str, Any]:
        """Destroy a browser instance.
        
        Args:
            instance_id: Browser instance ID to destroy
            destroy: If True, destroy the browser; if False, return to pool
            
        Returns:
            dict[str, Any]: Destruction result
        """
        _logger.info(
            "destroying_browser",
            instance_id=instance_id,
            destroy=destroy,
        )
        
        try:
            # Get handle from pool (mock implementation)
            handle = BrowserHandle(
                instance_id=instance_id,
                task_id="unknown",
                acquired_at=None,  # type: ignore
                requirements=BrowserRequirements(),
            )
            
            await self.lifecycle_service.release_browser(handle, destroy=destroy)
            
            return {
                "success": True,
                "instance_id": instance_id,
                "action": "destroyed" if destroy else "returned_to_pool",
            }
            
        except Exception as exc:
            _logger.error(
                "destroy_browser_failed",
                instance_id=instance_id,
                error=str(exc),
                exc_info=True,
            )
            return {
                "success": False,
                "error": str(exc),
            }


class ListBrowsersTool:
    """Tool for listing active browser instances.
    
    Allows the Research Agent to see which browsers are currently active.
    """
    
    def __init__(
        self,
        lifecycle_service: BrowserLifecycleService | None = None,
    ):
        """Initialize the list browsers tool.
        
        Args:
            lifecycle_service: Browser lifecycle service (created if None)
        """
        self.lifecycle_service = lifecycle_service or BrowserLifecycleService()
    
    async def execute(self) -> dict[str, Any]:
        """List all active browser instances.
        
        Returns:
            dict[str, Any]: List of browser instances
        """
        _logger.info("listing_browsers")
        
        try:
            pool_status = await self.lifecycle_service.get_pool_status()
            
            return {
                "success": True,
                "total_instances": pool_status["total_instances"],
                "instances": pool_status["instances"],
            }
            
        except Exception as exc:
            _logger.error(
                "list_browsers_failed",
                error=str(exc),
                exc_info=True,
            )
            return {
                "success": False,
                "error": str(exc),
            }


class GetBrowserMetricsTool:
    """Tool for getting browser instance metrics.
    
    Allows the Research Agent to monitor browser performance and resource usage.
    """
    
    def __init__(
        self,
        lifecycle_service: BrowserLifecycleService | None = None,
    ):
        """Initialize the get browser metrics tool.
        
        Args:
            lifecycle_service: Browser lifecycle service (created if None)
        """
        self.lifecycle_service = lifecycle_service or BrowserLifecycleService()
    
    async def execute(self, instance_id: str) -> dict[str, Any]:
        """Get metrics for a specific browser instance.
        
        Args:
            instance_id: Browser instance ID
            
        Returns:
            dict[str, Any]: Browser metrics
        """
        _logger.info("getting_browser_metrics", instance_id=instance_id)
        
        try:
            metrics = await self.lifecycle_service.get_browser_metrics(instance_id)
            
            return {
                "success": True,
                "metrics": metrics,
            }
            
        except Exception as exc:
            _logger.error(
                "get_browser_metrics_failed",
                instance_id=instance_id,
                error=str(exc),
                exc_info=True,
            )
            return {
                "success": False,
                "error": str(exc),
            }


class CreateSnapshotTool:
    """Tool for creating browser state snapshots.
    
    Allows the Research Agent to create snapshots for rollback.
    """
    
    def __init__(
        self,
        lifecycle_service: BrowserLifecycleService | None = None,
    ):
        """Initialize the create snapshot tool.
        
        Args:
            lifecycle_service: Browser lifecycle service (created if None)
        """
        self.lifecycle_service = lifecycle_service or BrowserLifecycleService()
    
    async def execute(self, instance_id: str) -> dict[str, Any]:
        """Create a snapshot of the browser state.
        
        Args:
            instance_id: Browser instance ID
            
        Returns:
            dict[str, Any]: Snapshot creation result
        """
        _logger.info("creating_snapshot", instance_id=instance_id)
        
        try:
            # Get handle from pool (mock implementation)
            handle = BrowserHandle(
                instance_id=instance_id,
                task_id="unknown",
                acquired_at=None,  # type: ignore
                requirements=BrowserRequirements(),
            )
            
            snapshot_id = await self.lifecycle_service.create_snapshot(handle)
            
            return {
                "success": True,
                "instance_id": instance_id,
                "snapshot_id": snapshot_id,
            }
            
        except Exception as exc:
            _logger.error(
                "create_snapshot_failed",
                instance_id=instance_id,
                error=str(exc),
                exc_info=True,
            )
            return {
                "success": False,
                "error": str(exc),
            }


class RestoreSnapshotTool:
    """Tool for restoring browser state snapshots.
    
    Allows the Research Agent to restore browsers to a previous state.
    """
    
    def __init__(
        self,
        lifecycle_service: BrowserLifecycleService | None = None,
    ):
        """Initialize the restore snapshot tool.
        
        Args:
            lifecycle_service: Browser lifecycle service (created if None)
        """
        self.lifecycle_service = lifecycle_service or BrowserLifecycleService()
    
    async def execute(
        self,
        snapshot_id: str,
        task_id: str,
    ) -> dict[str, Any]:
        """Restore a browser from a snapshot.
        
        Args:
            snapshot_id: Snapshot ID to restore
            task_id: Task ID requesting the restore
            
        Returns:
            dict[str, Any]: Snapshot restoration result
        """
        _logger.info(
            "restoring_snapshot",
            snapshot_id=snapshot_id,
            task_id=task_id,
        )
        
        try:
            handle = await self.lifecycle_service.restore_snapshot(
                snapshot_id=snapshot_id,
                task_id=task_id,
            )
            
            return {
                "success": True,
                "snapshot_id": snapshot_id,
                "instance_id": handle.instance_id,
                "task_id": handle.task_id,
            }
            
        except Exception as exc:
            _logger.error(
                "restore_snapshot_failed",
                snapshot_id=snapshot_id,
                error=str(exc),
                exc_info=True,
            )
            return {
                "success": False,
                "error": str(exc),
            }


def get_browser_management_tools(
    lifecycle_service: BrowserLifecycleService | None = None,
) -> dict[str, Any]:
    """Get all browser management tools.
    
    Args:
        lifecycle_service: Browser lifecycle service (created if None)
        
    Returns:
        dict[str, Any]: Dictionary of management tools
    """
    return {
        "create_browser": CreateBrowserTool(lifecycle_service),
        "destroy_browser": DestroyBrowserTool(lifecycle_service),
        "list_browsers": ListBrowsersTool(lifecycle_service),
        "get_browser_metrics": GetBrowserMetricsTool(lifecycle_service),
        "create_snapshot": CreateSnapshotTool(lifecycle_service),
        "restore_snapshot": RestoreSnapshotTool(lifecycle_service),
    }
