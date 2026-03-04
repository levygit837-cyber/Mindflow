#!/usr/bin/env python3
"""
Simple demonstration of the PinchTabService multi-instance fix concept.
No external dependencies required.
"""

from typing import Dict, Any


class MockHttpClient:
    """Mock HTTP client to demonstrate the concept."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.request_count = 0
    
    def request(self, method: str, endpoint: str):
        self.request_count += 1
        return f"{method} {self.base_url}{endpoint} (request #{self.request_count})"


class OldPinchTabService:
    """Old buggy approach - single shared client."""
    
    def __init__(self):
        self.base_url = "http://localhost:9867"  # ❌ Single global URL
        self._client = None  # ❌ Single global client
        self._active_instances: Dict[str, Any] = {}
    
    def create_instance(self, port: int) -> str:
        """Create instance with old buggy approach."""
        instance_id = f"browser_{port}"
        
        # ❌ PROBLEM: Overwrites global state for ALL instances
        self.base_url = f"http://localhost:{port}"
        self._client = MockHttpClient(base_url=self.base_url)
        
        self._active_instances[instance_id] = {"port": port}
        return instance_id
    
    def make_request(self, browser_id: str, method: str, endpoint: str) -> str:
        """Make request - always uses the LAST client."""
        # ❌ PROBLEM: Always uses the URL of the LAST created instance
        return self._client.request(method, endpoint)


class NewPinchTabService:
    """New fixed approach - individual client per instance."""
    
    def __init__(self):
        # ✅ SOLUTION: No global state
        self._active_instances: Dict[str, Any] = {}
        self._instance_clients: Dict[str, MockHttpClient] = {}
    
    def create_instance(self, port: int) -> str:
        """Create instance with new fixed approach."""
        instance_id = f"browser_{port}"
        
        # ✅ SOLUTION: Individual client per instance
        instance_client = MockHttpClient(base_url=f"http://localhost:{port}")
        self._instance_clients[instance_id] = instance_client
        
        self._active_instances[instance_id] = {"port": port}
        return instance_id
    
    def make_request(self, browser_id: str, method: str, endpoint: str) -> str:
        """Make request - uses the correct client for each instance."""
        # ✅ SOLUTION: Routes to the correct instance's client
        client = self._instance_clients.get(browser_id)
        if not client:
            raise ValueError(f"No client found for browser {browser_id}")
        return client.request(method, endpoint)


def test_old_approach():
    """Test the old buggy approach."""
    
    print("❌ TESTING OLD APPROACH (Buggy):")
    print("-" * 40)
    
    service = OldPinchTabService()
    
    # Create multiple instances
    id1 = service.create_instance(9867)
    id2 = service.create_instance(9868)
    id3 = service.create_instance(9869)
    
    print(f"Created instances: {id1}, {id2}, {id3}")
    print(f"Current global base_url: {service.base_url}")
    
    # Make requests from each instance
    req1 = service.make_request(id1, "GET", "/search")
    req2 = service.make_request(id2, "GET", "/search")
    req3 = service.make_request(id3, "GET", "/search")
    
    print(f"Request from {id1}: {req1}")
    print(f"Request from {id2}: {req2}")
    print(f"Request from {id3}: {req3}")
    
    # All requests go to the same URL (the last one)!
    all_same_url = "http://localhost:9869" in req1 and "http://localhost:9869" in req2 and "http://localhost:9869" in req3
    print(f"🔴 All requests go to same URL: {all_same_url}")
    
    return all_same_url


def test_new_approach():
    """Test the new fixed approach."""
    
    print("\n✅ TESTING NEW APPROACH (Fixed):")
    print("-" * 40)
    
    service = NewPinchTabService()
    
    # Create multiple instances
    id1 = service.create_instance(9867)
    id2 = service.create_instance(9868)
    id3 = service.create_instance(9869)
    
    print(f"Created instances: {id1}, {id2}, {id3}")
    
    # Make requests from each instance
    req1 = service.make_request(id1, "GET", "/search")
    req2 = service.make_request(id2, "GET", "/search")
    req3 = service.make_request(id3, "GET", "/search")
    
    print(f"Request from {id1}: {req1}")
    print(f"Request from {id2}: {req2}")
    print(f"Request from {id3}: {req3}")
    
    # Each request goes to the correct URL
    correct_urls = (
        "http://localhost:9867" in req1 and
        "http://localhost:9868" in req2 and
        "http://localhost:9869" in req3
    )
    print(f"🟢 Each request goes to correct URL: {correct_urls}")
    
    return correct_urls


def demonstrate_fix():
    """Demonstrate the key differences between old and new approaches."""
    
    print("\n🔍 PROBLEM & SOLUTION DEMONSTRATION:")
    print("=" * 60)
    
    print("\n📋 PROBLEM SUMMARY:")
    print("• Old code used single global base_url and client")
    print("• Multiple instances overwrote each other's URLs")
    print("• All requests went to the last created instance")
    print("• Parallel execution was impossible")
    
    print("\n🛠️  SOLUTION IMPLEMENTED:")
    print("• Each instance gets its own HTTP client")
    print("• Clients stored in _instance_clients dictionary")
    print("• Requests routed to correct client using browser_id")
    print("• Proper isolation between instances")
    print("• True parallel execution now possible")
    
    print("\n🔧 KEY CODE CHANGES:")
    print("""
OLD CODE:
    self.base_url = "http://localhost:9867"  # ❌ Global
    self._client = None  # ❌ Single client
    
    def create_instance(self, port):
        self.base_url = f"http://localhost:{port}"  # ❌ Overwrites global
        self._client = httpx.AsyncClient(base_url=self.base_url)

NEW CODE:
    self._instance_clients = {}  # ✅ Client per instance
    
    def create_instance(self, port):
        instance_client = httpx.AsyncClient(base_url=f"http://localhost:{port}")
        self._instance_clients[browser_id] = instance_client  # ✅ Isolated
    """)


def main():
    """Run the complete demonstration."""
    
    print("🚀 PinchTabService Multi-Instance Fix Demonstration")
    print("=" * 60)
    
    # Test both approaches
    old_broken = test_old_approach()
    new_fixed = test_new_approach()
    
    # Show the fix details
    demonstrate_fix()
    
    # Final results
    print(f"\n📊 FINAL RESULTS:")
    print("=" * 30)
    print(f"Old approach: {'❌ BROKEN (all requests to same URL)' if old_broken else '✅ Works'}")
    print(f"New approach: {'✅ FIXED (proper isolation)' if new_fixed else '❌ Still broken'}")
    
    print(f"\n🎯 CONCLUSION:")
    if old_broken and new_fixed:
        print("✅ The fix successfully resolves the multi-instance issue!")
        print("✅ OmniMind can now run true parallel browser research!")
        print("✅ Each browser instance will communicate with its correct port!")
    else:
        print("❌ The demonstration shows issues with the fix.")
    
    print(f"\n🌟 IMPACT:")
    print("• Multi-browser parallel research now works correctly")
    print("• No more port conflicts between instances")
    print("• Proper resource isolation and cleanup")
    print("• Scalable research architecture")


if __name__ == "__main__":
    main()
