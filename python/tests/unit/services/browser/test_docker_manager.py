"""Unit tests for LightPandaDockerManager."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import pytest

from mindflow_backend.services.browser.docker_manager import (
    BrowserInstance,
    InstanceStatus,
    LightPandaDockerManager,
)


class TestLightPandaDockerManager:
    """Test suite for LightPandaDockerManager."""
    
    @pytest.fixture
    def manager(self):
        """Create a Docker manager instance for testing."""
        return LightPandaDockerManager(
            base_port=9222,
            max_instances=5,
            host="127.0.0.1",
        )
    
    @pytest.mark.asyncio
    async def test_create_browser_instance(self, manager):
        """Test creating a new browser instance."""
        instance = await manager.create_browser_instance("test-task-1")
        
        assert instance is not None
        assert instance.instance_id.startswith("browser-test-task-1")
        assert instance.port == 9222
        assert instance.host == "127.0.0.1"
        assert instance.status == InstanceStatus.RUNNING
        assert instance.task_id == "test-task-1"
        assert instance.cdp_url == "http://127.0.0.1:9222"
    
    @pytest.mark.asyncio
    async def test_create_multiple_instances(self, manager):
        """Test creating multiple browser instances."""
        instance1 = await manager.create_browser_instance("task-1")
        instance2 = await manager.create_browser_instance("task-2")
        instance3 = await manager.create_browser_instance("task-3")
        
        assert instance1.instance_id != instance2.instance_id
        assert instance2.instance_id != instance3.instance_id
        assert instance1.port == 9222
        assert instance2.port == 9223
        assert instance3.port == 9224
    
    @pytest.mark.asyncio
    async def test_max_instances_limit(self, manager):
        """Test that max instances limit is enforced."""
        manager.max_instances = 2
        
        await manager.create_browser_instance("task-1")
        await manager.create_browser_instance("task-2")
        
        with pytest.raises(RuntimeError, match="Maximum.*instances reached"):
            await manager.create_browser_instance("task-3")
    
    @pytest.mark.asyncio
    async def test_destroy_browser_instance(self, manager):
        """Test destroying a browser instance."""
        instance = await manager.create_browser_instance("test-task")
        
        result = await manager.destroy_browser_instance(instance.instance_id)
        
        assert result is True
        assert instance.instance_id not in manager._instances
    
    @pytest.mark.asyncio
    async def test_destroy_nonexistent_instance(self, manager):
        """Test destroying a non-existent instance."""
        result = await manager.destroy_browser_instance("non-existent-id")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_instance_status(self, manager):
        """Test getting instance status."""
        instance = await manager.create_browser_instance("test-task")
        
        status = await manager.get_instance_status(instance.instance_id)
        
        assert status == InstanceStatus.RUNNING
    
    @pytest.mark.asyncio
    async def test_get_status_nonexistent(self, manager):
        """Test getting status for non-existent instance."""
        status = await manager.get_instance_status("non-existent-id")
        
        assert status == InstanceStatus.UNKNOWN
    
    @pytest.mark.asyncio
    async def test_list_active_instances(self, manager):
        """Test listing active instances."""
        instance1 = await manager.create_browser_instance("task-1")
        instance2 = await manager.create_browser_instance("task-2")
        
        await manager.destroy_browser_instance(instance1.instance_id)
        
        active = await manager.list_active_instances()
        
        assert len(active) == 1
        assert active[0].instance_id == instance2.instance_id
    
    @pytest.mark.asyncio
    async def test_cleanup_stale_instances(self, manager):
        """Test cleanup of stale instances."""
        instance = await manager.create_browser_instance("test-task")
        
        # Simulate old instance
        instance.created_at = datetime.utcnow() - timedelta(hours=2)
        
        cleanup_count = await manager.cleanup_stale_instances(max_age_seconds=3600)
        
        assert cleanup_count == 1
        assert instance.instance_id not in manager._instances
    
    @pytest.mark.asyncio
    async def test_update_instance_activity(self, manager):
        """Test updating instance activity timestamp."""
        instance = await manager.create_browser_instance("test-task")
        
        result = await manager.update_instance_activity(instance.instance_id)
        
        assert result is True
        assert instance.last_activity is not None
    
    @pytest.mark.asyncio
    async def test_get_instance_metrics(self, manager):
        """Test getting instance metrics."""
        instance = await manager.create_browser_instance("test-task")
        
        metrics = await manager.get_instance_metrics(instance.instance_id)
        
        assert metrics is not None
        assert "instance_id" in metrics
        assert "status" in metrics
        assert "uptime_seconds" in metrics
        assert "memory_usage_mb" in metrics
    
    @pytest.mark.asyncio
    async def test_get_all_metrics(self, manager):
        """Test getting aggregated metrics."""
        await manager.create_browser_instance("task-1")
        await manager.create_browser_instance("task-2")
        
        metrics = await manager.get_all_metrics()
        
        assert metrics is not None
        assert "total_instances" in metrics
        assert "active_instances" in metrics
        assert metrics["total_instances"] == 2
