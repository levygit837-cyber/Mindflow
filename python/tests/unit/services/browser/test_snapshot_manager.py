"""Unit tests for BrowserSnapshotManager."""

from __future__ import annotations

import asyncio

import pytest

from mindflow_backend.services.browser import (
    BrowserSnapshotManager,
    Snapshot,
)


class TestBrowserSnapshotManager:
    """Test suite for BrowserSnapshotManager."""
    
    @pytest.fixture
    def snapshot_manager(self):
        """Create a snapshot manager instance for testing."""
        return BrowserSnapshotManager(
            retention_seconds=3600,
            max_snapshots_per_browser=10,
        )
    
    @pytest.mark.asyncio
    async def test_capture_snapshot(self, snapshot_manager):
        """Test capturing a browser snapshot."""
        snapshot_id = await snapshot_manager.capture_snapshot(
            browser_id="browser-1",
            url="https://example.com",
            cookies=[{"name": "session", "value": "abc123"}],
            localStorage={"key": "value"},
        )
        
        assert snapshot_id is not None
        assert snapshot_id.startswith("snapshot-browser-1")
        
        snapshot = await snapshot_manager.get_snapshot(snapshot_id)
        assert snapshot is not None
        assert snapshot.browser_id == "browser-1"
        assert snapshot.url == "https://example.com"
        assert len(snapshot.cookies) == 1
        assert snapshot.localStorage["key"] == "value"
    
    @pytest.mark.asyncio
    async def test_restore_snapshot(self, snapshot_manager):
        """Test restoring a snapshot."""
        snapshot_id = await snapshot_manager.capture_snapshot(
            browser_id="browser-1",
            url="https://example.com",
        )
        
        result = await snapshot_manager.restore_snapshot(
            snapshot_id=snapshot_id,
            target_browser_id="browser-2",
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_restore_nonexistent_snapshot(self, snapshot_manager):
        """Test restoring a non-existent snapshot."""
        result = await snapshot_manager.restore_snapshot(
            snapshot_id="non-existent",
            target_browser_id="browser-1",
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_list_snapshots(self, snapshot_manager):
        """Test listing snapshots for a browser."""
        await snapshot_manager.capture_snapshot(browser_id="browser-1")
        await snapshot_manager.capture_snapshot(browser_id="browser-1")
        await snapshot_manager.capture_snapshot(browser_id="browser-1")
        
        snapshots = await snapshot_manager.list_snapshots("browser-1")
        
        assert len(snapshots) == 3
    
    @pytest.mark.asyncio
    async def test_list_snapshots_empty(self, snapshot_manager):
        """Test listing snapshots for browser with no snapshots."""
        snapshots = await snapshot_manager.list_snapshots("non-existent")
        
        assert len(snapshots) == 0
    
    @pytest.mark.asyncio
    async def test_delete_snapshot(self, snapshot_manager):
        """Test deleting a snapshot."""
        snapshot_id = await snapshot_manager.capture_snapshot(browser_id="browser-1")
        
        result = await snapshot_manager.delete_snapshot(snapshot_id)
        
        assert result is True
        assert await snapshot_manager.get_snapshot(snapshot_id) is None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_snapshot(self, snapshot_manager):
        """Test deleting a non-existent snapshot."""
        result = await snapshot_manager.delete_snapshot("non-existent")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_cleanup_old_snapshots(self, snapshot_manager):
        """Test cleanup of old snapshots."""
        # Create a snapshot
        snapshot_id = await snapshot_manager.capture_snapshot(browser_id="browser-1")
        
        # Manually set old timestamp
        snapshot = await snapshot_manager.get_snapshot(snapshot_id)
        snapshot.created_at = snapshot.created_at.replace(
            year=2020, month=1, day=1
        )
        
        cleanup_count = await snapshot_manager.cleanup_old_snapshots(max_age_seconds=3600)
        
        assert cleanup_count == 1
        assert await snapshot_manager.get_snapshot(snapshot_id) is None
    
    @pytest.mark.asyncio
    async def test_max_snapshots_per_browser(self, snapshot_manager):
        """Test that max snapshots per browser is enforced."""
        snapshot_manager.max_snapshots_per_browser = 3
        
        # Create 5 snapshots
        for i in range(5):
            await snapshot_manager.capture_snapshot(browser_id="browser-1")
        
        snapshots = await snapshot_manager.list_snapshots("browser-1")
        
        # Should only keep 3 (LRU eviction)
        assert len(snapshots) == 3
    
    @pytest.mark.asyncio
    async def test_get_stats(self, snapshot_manager):
        """Test getting snapshot manager statistics."""
        await snapshot_manager.capture_snapshot(browser_id="browser-1")
        await snapshot_manager.capture_snapshot(browser_id="browser-2")
        await snapshot_manager.capture_snapshot(browser_id="browser-1")
        
        stats = await snapshot_manager.get_stats()
        
        assert stats is not None
        assert "total_snapshots" in stats
        assert "total_browsers" in stats
        assert stats["total_snapshots"] == 3
        assert stats["total_browsers"] == 2
    
    @pytest.mark.asyncio
    async def test_snapshot_to_dict(self, snapshot_manager):
        """Test snapshot serialization to dict."""
        snapshot_id = await snapshot_manager.capture_snapshot(
            browser_id="browser-1",
            url="https://example.com",
        )
        
        snapshot = await snapshot_manager.get_snapshot(snapshot_id)
        snapshot_dict = snapshot.to_dict()
        
        assert "snapshot_id" in snapshot_dict
        assert "browser_id" in snapshot_dict
        assert "created_at" in snapshot_dict
        assert "url" in snapshot_dict
    
    @pytest.mark.asyncio
    async def test_snapshot_from_dict(self, snapshot_manager):
        """Test snapshot deserialization from dict."""
        snapshot_data = {
            "snapshot_id": "test-snapshot-1",
            "browser_id": "browser-1",
            "created_at": "2024-01-01T00:00:00",
            "url": "https://example.com",
            "cookies": [],
            "localStorage": {},
            "sessionStorage": {},
            "page_state": {},
        }
        
        snapshot = Snapshot.from_dict(snapshot_data)
        
        assert snapshot.snapshot_id == "test-snapshot-1"
        assert snapshot.browser_id == "browser-1"
        assert snapshot.url == "https://example.com"
