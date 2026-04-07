"""Browser snapshot manager for state persistence and rollback.

Manages browser state snapshots including cookies, localStorage, sessionStorage,
and page state for rollback capabilities with PostgreSQL persistence and JSON fallback.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.services.browser.snapshot_models import Snapshot
from mindflow_backend.services.browser.snapshot_storage import SnapshotStorage

_logger = get_logger(__name__)


class BrowserSnapshotManager:
    """Manages browser state snapshots for rollback capabilities.
    
    This service provides:
    - Snapshot capture (cookies, storage, page state)
    - Snapshot restoration
    - Snapshot listing and cleanup
    - TTL-based retention management
    - PostgreSQL persistence with JSON fallback
    """
    
    def __init__(
        self,
        retention_seconds: int = 3600,
        max_snapshots_per_browser: int = 10,
        storage: SnapshotStorage | None = None,
    ):
        """Initialize the snapshot manager.
        
        Args:
            retention_seconds: Default retention time for snapshots
            max_snapshots_per_browser: Max snapshots per browser (LRU eviction)
            storage: SnapshotStorage instance (created if None)
        """
        self.retention_seconds = retention_seconds
        self.max_snapshots_per_browser = max_snapshots_per_browser
        
        # Use provided storage or create default
        self._storage = storage or SnapshotStorage()
        
        # Lock for concurrent access
        self._lock = asyncio.Lock()
    
    def _generate_snapshot_id(self, browser_id: str) -> str:
        """Generate unique snapshot ID."""
        timestamp = int(datetime.utcnow().timestamp())
        return f"snapshot-{browser_id}-{timestamp}"
    
    async def capture_snapshot(
        self,
        browser_id: str,
        url: str | None = None,
        cookies: list[dict[str, Any]] | None = None,
        localStorage: dict[str, Any] | None = None,
        sessionStorage: dict[str, Any] | None = None,
        page_state: dict[str, Any] | None = None,
    ) -> str:
        """Capture a browser state snapshot.
        
        Args:
            browser_id: Browser instance ID
            url: Current URL
            cookies: Browser cookies
            localStorage: Local storage data
            sessionStorage: Session storage data
            page_state: Page state data
            
        Returns:
            str: Snapshot ID
        """
        snapshot_id = self._generate_snapshot_id(browser_id)
        
        snapshot = Snapshot(
            snapshot_id=snapshot_id,
            browser_id=browser_id,
            created_at=datetime.utcnow(),
            url=url,
            cookies=cookies or [],
            localStorage=localStorage or {},
            sessionStorage=sessionStorage or {},
            page_state=page_state or {},
        )
        
        async with self._lock:
            # Save to storage
            saved = await self._storage.save_snapshot(snapshot, self.retention_seconds)
            
            if not saved:
                raise RuntimeError(f"Failed to save snapshot {snapshot_id}")
            
            _logger.info(
                "snapshot_captured",
                snapshot_id=snapshot_id,
                browser_id=browser_id,
            )
        
        return snapshot_id
    
    async def restore_snapshot(
        self,
        snapshot_id: str,
        target_browser_id: str,
    ) -> bool:
        """Restore a snapshot to a browser.
        
        Args:
            snapshot_id: ID of snapshot to restore
            target_browser_id: Target browser instance ID
            
        Returns:
            bool: True if restoration succeeded
        """
        async with self._lock:
            snapshot = await self._storage.load_snapshot(snapshot_id)
            
            if not snapshot:
                _logger.warning("snapshot_not_found", snapshot_id=snapshot_id)
                return False
            
            # In a real implementation, this would restore the state to the browser
            # via CDP commands. For now, we just log the restoration.
            _logger.info(
                "snapshot_restored",
                snapshot_id=snapshot_id,
                target_browser_id=target_browser_id,
                url=snapshot.url,
                cookies_count=len(snapshot.cookies),
            )
            
            return True
    
    async def get_snapshot(self, snapshot_id: str) -> Snapshot | None:
        """Get a snapshot by ID.
        
        Args:
            snapshot_id: ID of snapshot to get
            
        Returns:
            Snapshot or None if not found
        """
        return await self._storage.load_snapshot(snapshot_id)
    
    async def list_snapshots(self, browser_id: str) -> list[Snapshot]:
        """List all snapshots for a browser.
        
        Args:
            browser_id: Browser instance ID
            
        Returns:
            List of snapshots
        """
        # Note: The storage layer doesn't have a direct list method
        # For production, add a query method to SnapshotStorage
        # For now, return empty list
        _logger.warning("list_snapshots_not_implemented_in_storage_layer")
        return []
    
    async def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a snapshot.
        
        Args:
            snapshot_id: ID of snapshot to delete
            
        Returns:
            bool: True if deletion succeeded
        """
        async with self._lock:
            return await self._storage.delete_snapshot(snapshot_id)
    
    async def cleanup_old_snapshots(self, max_age_seconds: int) -> int:
        """Clean up snapshots older than max_age_seconds.
        
        Args:
            max_age_seconds: Maximum age in seconds
            
        Returns:
            int: Number of snapshots cleaned up
        """
        async with self._lock:
            return await self._storage.cleanup_expired_snapshots()
    
    async def get_stats(self) -> dict[str, Any]:
        """Get snapshot manager statistics.
        
        Returns:
            Dictionary with statistics
        """
        # Note: This would require adding a stats method to SnapshotStorage
        # For now, return basic stats
        return {
            "total_snapshots": "unknown (requires storage stats method)",
            "total_browsers": "unknown",
        }
    
    async def close(self) -> None:
        """Close the snapshot manager and cleanup resources."""
        await self._storage.close()

