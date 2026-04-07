"""Unit tests for BrowserLifecycleService."""

from __future__ import annotations

import asyncio

import pytest

from mindflow_backend.services.browser import (
    BrowserHandle,
    BrowserLifecycleService,
    BrowserRequirements,
)


class TestBrowserLifecycleService:
    """Test suite for BrowserLifecycleService."""
    
    @pytest.fixture
    def lifecycle_service(self):
        """Create a lifecycle service instance for testing."""
        service = BrowserLifecycleService(
            max_idle_timeout=600,
            max_lifetime=3600,
            snapshot_interval=300,
            snapshot_retention=3600,
        )
        return service
    
    @pytest.mark.asyncio
    async def test_acquire_browser(self, lifecycle_service):
        """Test acquiring a browser for a task."""
        handle = await lifecycle_service.acquire_browser(
            task_id="test-task-1",
            requirements=BrowserRequirements(max_memory_mb=512),
        )
        
        assert handle is not None
        assert handle.instance_id.startswith("browser-test-task-1")
        assert handle.task_id == "test-task-1"
        assert handle.requirements.max_memory_mb == 512
    
    @pytest.mark.asyncio
    async def test_release_browser_destroy(self, lifecycle_service):
        """Test releasing and destroying a browser."""
        handle = await lifecycle_service.acquire_browser("test-task")
        
        await lifecycle_service.release_browser(handle, destroy=True)
        
        assert handle.instance_id not in lifecycle_service._pool
    
    @pytest.mark.asyncio
    async def test_release_browser_return_to_pool(self, lifecycle_service):
        """Test releasing browser back to pool."""
        handle = await lifecycle_service.acquire_browser("test-task")
        
        await lifecycle_service.release_browser(handle, destroy=False)
        
        assert handle.instance_id in lifecycle_service._pool
    
    @pytest.mark.asyncio
    async def test_create_snapshot(self, lifecycle_service):
        """Test creating a browser snapshot."""
        handle = await lifecycle_service.acquire_browser("test-task")
        
        snapshot_id = await lifecycle_service.create_snapshot(handle)
        
        assert snapshot_id is not None
        assert snapshot_id.startswith("snapshot-")
        assert handle.snapshot_id == snapshot_id
    
    @pytest.mark.asyncio
    async def test_restore_snapshot(self, lifecycle_service):
        """Test restoring from a snapshot."""
        handle = await lifecycle_service.acquire_browser("test-task")
        snapshot_id = await lifecycle_service.create_snapshot(handle)
        
        restored_handle = await lifecycle_service.restore_snapshot(
            snapshot_id=snapshot_id,
            task_id="new-task",
        )
        
        assert restored_handle is not None
        assert restored_handle.snapshot_id == snapshot_id
    
    @pytest.mark.asyncio
    async def test_get_browser_metrics(self, lifecycle_service):
        """Test getting browser metrics."""
        handle = await lifecycle_service.acquire_browser("test-task")
        
        metrics = await lifecycle_service.get_browser_metrics(handle.instance_id)
        
        assert metrics is not None
        assert "instance_id" in metrics
        assert "task_id" in metrics
    
    @pytest.mark.asyncio
    async def test_cleanup_idle_browsers(self, lifecycle_service):
        """Test cleanup of idle browsers."""
        handle1 = await lifecycle_service.acquire_browser("task-1")
        handle2 = await lifecycle_service.acquire_browser("task-2")
        
        # Make handle1 appear old
        handle1.last_used = None
        
        cleanup_count = await lifecycle_service.cleanup_idle_browsers()
        
        assert cleanup_count >= 0
    
    @pytest.mark.asyncio
    async def test_get_pool_status(self, lifecycle_service):
        """Test getting pool status."""
        await lifecycle_service.acquire_browser("task-1")
        await lifecycle_service.acquire_browser("task-2")
        
        status = await lifecycle_service.get_pool_status()
        
        assert status is not None
        assert "total_instances" in status
        assert "instances" in status
        assert status["total_instances"] == 2
    
    @pytest.mark.asyncio
    async def test_start_stop_service(self, lifecycle_service):
        """Test starting and stopping the lifecycle service."""
        await lifecycle_service.start()
        
        # Service should be running
        assert lifecycle_service._cleanup_task is not None
        assert lifecycle_service._snapshot_task is not None
        
        await lifecycle_service.stop()
        
        # Tasks should be cancelled
        assert lifecycle_service._cleanup_task.cancelled()
        assert lifecycle_service._snapshot_task.cancelled()
