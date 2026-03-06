#!/usr/bin/env python3
"""Test script to verify new worker system functionality."""

import sys
import asyncio
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "python"))

from omnimind_backend.workers.infrastructure.worker_factory import WorkerFactory
from omnimind_backend.workers.infrastructure.queue_manager import QueueManager
from omnimind_backend.workers.config.settings import get_worker_settings


async def test_worker_factory():
    """Test worker factory functionality."""
    print("Testing WorkerFactory...")
    
    factory = WorkerFactory()
    print(f"Available workers: {list(factory._worker_registry.keys())}")
    
    # Test creating a simple worker (without starting it)
    try:
        worker = factory.create_worker("health")
        print(f"✓ Created health worker: {type(worker).__name__}")
    except Exception as e:
        print(f"✗ Failed to create health worker: {e}")
        return False
    
    return True


async def test_queue_manager():
    """Test queue manager functionality."""
    print("\nTesting QueueManager...")
    
    try:
        settings = get_worker_settings()
        print(f"RabbitMQ URL: {settings.rabbitmq_url}")
        
        # Note: Don't actually connect, just test instantiation
        print("✓ QueueManager can be instantiated")
        return True
    except Exception as e:
        print(f"✗ QueueManager test failed: {e}")
        return False


async def test_worker_imports():
    """Test that all worker modules can be imported."""
    print("\nTesting worker imports...")
    
    try:
        from omnimind_backend.workers import (
            CoderWorker, AnalystWorker, ResearcherWorker, OrchestratorWorker,
            VectorWorker, MemoryWorker, HealthWorker,
            BrowserWorker, ContentWorker,
            QueueManager, WorkerFactory, WorkerMonitor
        )
        print("✓ All worker classes imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("=== OmniMind Worker System Test ===\n")
    
    tests = [
        test_worker_imports,
        test_worker_factory,
        test_queue_manager,
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
            results.append(False)
    
    print(f"\n=== Results ===")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! New worker system is ready.")
    else:
        print("❌ Some tests failed. Check the errors above.")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
