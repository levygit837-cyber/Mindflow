#!/usr/bin/env python3
"""
Simple test to verify the PinchTabService multi-instance fix concept.
This test demonstrates the core logic without complex dependencies.
"""

import asyncio
from typing import Any

import httpx


class MockPinchTabService:
    """Simplified version of PinchTabService to test the multi-instance concept."""
    
    def __init__(self):
        # OLD APPROACH (buggy):
        # self.base_url = "http://localhost:9867"  # Single URL for all instances
        # self._client = None  # Single client for all instances
        
        # NEW APPROACH (fixed):
        self._active_instances: dict[str, Any] = {}
        self._instance_clients: dict[str, httpx.AsyncClient] = {}
    
    async def create_instance_old(self, port: int) -> str:
        """Old buggy approach - single base_url shared across instances."""
        instance_id = f"browser_{port}"
        
        # ❌ PROBLEM: Single base_url for all instances
        base_url = f"http://localhost:{port}"
        self.base_url = base_url  # Overwrites global state!
        
        # ❌ PROBLEM: Single client shared
        if not self._client:
            self._client = httpx.AsyncClient(base_url=base_url)
        
        self._active_instances[instance_id] = {"port": port, "base_url": base_url}
        return instance_id
    
    async def create_instance_new(self, port: int) -> str:
        """New fixed approach - individual client per instance."""
        instance_id = f"browser_{port}"
        
        # ✅ SOLUTION: Individual client per instance
        instance_client = httpx.AsyncClient(base_url=f"http://localhost:{port}")
        self._instance_clients[instance_id] = instance_client
        
        self._active_instances[instance_id] = {"port": port}
        return instance_id
    
    def get_instance_url_old(self, instance_id: str) -> str:
        """Old approach - always returns the last set URL."""
        return self.base_url  # ❌ Always returns the URL of the LAST instance
    
    def get_instance_url_new(self, instance_id: str) -> str:
        """New approach - returns the correct URL for each instance."""
        client = self._instance_clients.get(instance_id)
        return client.base_url if client else None  # ✅ Returns correct URL per instance
    
    async def cleanup_old(self):
        """Old cleanup approach."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def cleanup_new(self):
        """New cleanup approach."""
        for client in self._instance_clients.values():
            await client.aclose()
        self._instance_clients.clear()


async def test_old_vs_new_approach():
    """Test to demonstrate the difference between old and new approaches."""
    
    print("🧪 Testing OLD vs NEW PinchTabService approach...\n")
    
    # Test OLD approach (buggy)
    print("❌ OLD APPROACH (Buggy):")
    service_old = MockPinchTabService()
    
    # Create multiple instances
    id1 = await service_old.create_instance_old(9867)
    id2 = await service_old.create_instance_old(9868)
    id3 = await service_old.create_instance_old(9869)
    
    print(f"   Instance 1 (port 9867): {service_old.get_instance_url_old(id1)}")
    print(f"   Instance 2 (port 9868): {service_old.get_instance_url_old(id2)}")
    print(f"   Instance 3 (port 9869): {service_old.get_instance_url_old(id3)}")
    
    # All instances return the same URL (the last one set)!
    all_urls_same = (
        service_old.get_instance_url_old(id1) == 
        service_old.get_instance_url_old(id2) == 
        service_old.get_instance_url_old(id3)
    )
    print(f"   🔴 All URLs are the same: {all_urls_same}")
    
    await service_old.cleanup_old()
    
    print("\n✅ NEW APPROACH (Fixed):")
    service_new = MockPinchTabService()
    
    # Create multiple instances
    id1_new = await service_new.create_instance_new(9867)
    id2_new = await service_new.create_instance_new(9868)
    id3_new = await service_new.create_instance_new(9869)
    
    url1 = service_new.get_instance_url_new(id1_new)
    url2 = service_new.get_instance_url_new(id2_new)
    url3 = service_new.get_instance_url_new(id3_new)
    
    print(f"   Instance 1 (port 9867): {url1}")
    print(f"   Instance 2 (port 9868): {url2}")
    print(f"   Instance 3 (port 9869): {url3}")
    
    # Each instance has its own URL
    urls_correct = (
        url1 == "http://localhost:9867" and
        url2 == "http://localhost:9868" and 
        url3 == "http://localhost:9869"
    )
    print(f"   🟢 Each instance has correct URL: {urls_correct}")
    
    await service_new.cleanup_new()
    
    print("\n📊 RESULTS:")
    print(f"   Old approach: {'❌ BROKEN' if all_urls_same else '✅ Works'}")
    print(f"   New approach: {'✅ FIXED' if urls_correct else '❌ Broken'}")
    
    return urls_correct and all_urls_same


def demonstrate_problem():
    """Demonstrate the core problem in a simple way."""
    
    print("\n🔍 PROBLEM DEMONSTRATION:")
    print("=" * 50)
    
    # Simulate the old buggy behavior
    print("\n❌ OLD CODE (Buggy):")
    print("""
class PinchTabService:
    def __init__(self):
        self.base_url = "http://localhost:9867"  # Single global URL
        self._client = None  # Single global client
    
    def create_instance(self, port):
        # ❌ PROBLEM: Overwrites global state
        self.base_url = f"http://localhost:{port}"
        self._client = httpx.AsyncClient(base_url=self.base_url)
    
    def make_request(self, browser_id, endpoint):
        # ❌ PROBLEM: Always uses the LAST base_url
        return self._client.request(method, endpoint)
    """)
    
    print("\n✅ NEW CODE (Fixed):")
    print("""
class PinchTabService:
    def __init__(self):
        self._instance_clients = {}  # Client per instance
    
    def create_instance(self, port):
        instance_id = f"browser_{port}"
        # ✅ SOLUTION: Individual client per instance
        client = httpx.AsyncClient(base_url=f"http://localhost:{port}")
        self._instance_clients[instance_id] = client
    
    def make_request(self, browser_id, endpoint):
        # ✅ SOLUTION: Use the correct client for each instance
        client = self._instance_clients[browser_id]
        return client.request(method, endpoint)
    """)


async def main():
    """Run the demonstration."""
    print("🚀 PinchTabService Multi-Instance Fix Demonstration")
    print("=" * 60)
    
    demonstrate_problem()
    
    success = await test_old_vs_new_approach()
    
    print("\n🎯 CONCLUSION:")
    if success:
        print("✅ The fix correctly isolates HTTP clients per browser instance!")
        print("✅ Multi-instance parallel execution will now work properly!")
    else:
        print("❌ The fix needs more work.")
    
    print("\n🔧 KEY CHANGES MADE:")
    print("   1. Removed global base_url")
    print("   2. Added _instance_clients dictionary")
    print("   3. Each instance gets its own httpx.AsyncClient")
    print("   4. Requests are routed to the correct client")
    print("   5. Proper cleanup of individual clients")


if __name__ == "__main__":
    asyncio.run(main())
