#!/usr/bin/env python3
"""
Test script to verify PinchTabService multi-instance functionality.
This test validates that each browser instance has its own HTTP client and base URL.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

from mindflow_backend.agents.research.pinchtab_service import PinchTabService
from mindflow_backend.schemas.research import BrowserSession, ResearchStatus


async def test_multi_instance_isolation():
    """Test that multiple instances have isolated HTTP clients."""
    
    print("🧪 Testing PinchTabService multi-instance isolation...")
    
    # Create service
    service = PinchTabService()
    
    # Mock the monitor and port manager
    service.monitor = MagicMock()
    service.port_manager = MagicMock()
    
    # Setup mock responses
    service.port_manager.is_available.return_value = False
    service.port_manager.allocate_port.side_effect = [9867, 9868, 9869]
    
    service.monitor.start_instance.side_effect = [
        {"instance_id": "browser_1", "port": 9867},
        {"instance_id": "browser_2", "port": 9868},
        {"instance_id": "browser_3", "port": 9869},
    ]
    
    service.monitor.stop_instance.return_value = True
    service.monitor.health_checker = MagicMock()
    service.monitor.health_checker.update_process_health = AsyncMock()
    
    try:
        # Create multiple instances
        print("📦 Creating multiple browser instances...")
        
        instance1 = await service.create_instance(headless=True, stealth=True)
        instance2 = await service.create_instance(headless=True, stealth=True)
        instance3 = await service.create_instance(headless=True, stealth=True)
        
        print(f"✅ Instance 1: {instance1.instance_id} (port: {instance1.tab_id})")
        print(f"✅ Instance 2: {instance2.instance_id} (port: {instance2.tab_id})")
        print(f"✅ Instance 3: {instance3.instance_id} (port: {instance3.tab_id})")
        
        # Verify each instance has its own HTTP client
        print("\n🔍 Verifying HTTP client isolation...")
        
        client1 = service._instance_clients[instance1.browser_id]
        client2 = service._instance_clients[instance2.browser_id]
        client3 = service._instance_clients[instance3.browser_id]
        
        print(f"🌐 Client 1 base URL: {client1.base_url}")
        print(f"🌐 Client 2 base URL: {client2.base_url}")
        print(f"🌐 Client 3 base URL: {client3.base_url}")
        
        # Verify URLs are different
        assert client1.base_url == "http://localhost:9867", f"Expected http://localhost:9867, got {client1.base_url}"
        assert client2.base_url == "http://localhost:9868", f"Expected http://localhost:9868, got {client2.base_url}"
        assert client3.base_url == "http://localhost:9869", f"Expected http://localhost:9869, got {client3.base_url}"
        
        # Verify clients are different objects
        assert client1 is not client2
        assert client2 is not client3
        assert client1 is not client3
        
        print("✅ HTTP clients are properly isolated!")
        
        # Test cleanup
        print("\n🧹 Testing cleanup...")
        
        success_count = await service.cleanup_all()
        assert success_count == 3, f"Expected 3 successful cleanups, got {success_count}"
        
        # Verify clients are cleaned up
        assert len(service._instance_clients) == 0, "Instance clients not cleaned up"
        assert len(service._active_instances) == 0, "Active instances not cleaned up"
        
        print("✅ Cleanup successful!")
        
        print("\n🎉 All tests passed! Multi-instance isolation is working correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Ensure cleanup
        try:
            await service.cleanup_all()
        except:
            pass


async def test_request_routing():
    """Test that requests are routed to the correct instance."""
    
    print("\n🧪 Testing request routing...")
    
    service = PinchTabService()
    
    # Mock setup
    service.monitor = MagicMock()
    service.port_manager = MagicMock()
    service.port_manager.is_available.return_value = False
    service.port_manager.allocate_port.return_value = 9870
    
    service.monitor.start_instance.return_value = {"instance_id": "browser_test", "port": 9870}
    service.monitor.health_checker = MagicMock()
    service.monitor.health_checker.update_process_health = AsyncMock()
    
    try:
        # Create instance
        instance = await service.create_instance()
        
        # Mock the HTTP client to track requests
        mock_client = AsyncMock()
        mock_client.request.return_value = MagicMock()
        mock_client.request.return_value.json.return_value = {"status": "ok"}
        mock_client.request.return_value.raise_for_status.return_value = None
        
        # Replace the instance client with mock
        service._instance_clients[instance.browser_id] = mock_client
        
        # Make a request
        await service._make_request("GET", "/test", browser_id=instance.browser_id)
        
        # Verify the mock client was called
        assert mock_client.request.called, "Mock client was not called"
        
        # Verify the correct URL was used
        call_args = mock_client.request.call_args
        assert call_args[0][0] == "GET", f"Expected GET method, got {call_args[0][0]}"
        assert call_args[0][1] == "/test", f"Expected /test endpoint, got {call_args[0][1]}"
        
        print("✅ Request routing works correctly!")
        
        # Cleanup
        await service.cleanup_all()
        return True
        
    except Exception as e:
        print(f"❌ Request routing test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("🚀 Starting PinchTabService multi-instance tests...\n")
    
    test1_result = await test_multi_instance_isolation()
    test2_result = await test_request_routing()
    
    print(f"\n📊 Test Results:")
    print(f"   Multi-instance isolation: {'✅ PASS' if test1_result else '❌ FAIL'}")
    print(f"   Request routing: {'✅ PASS' if test2_result else '❌ FAIL'}")
    
    if test1_result and test2_result:
        print("\n🎉 All tests passed! The implementation is working correctly.")
    else:
        print("\n❌ Some tests failed. Please check the implementation.")


if __name__ == "__main__":
    asyncio.run(main())
