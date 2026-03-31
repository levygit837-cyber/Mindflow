#!/usr/bin/env python3
"""Simple validation script for basic imports."""

import sys


def test_basic_imports():
    """Test basic imports without complex schemas."""
    print("🔍 Testing basic imports...")
    
    tests = [
        # Test basic agent interfaces
        "from mindflow_backend.interfaces.agents import CorePersonalityContract",
        "from mindflow_backend.interfaces.agents import PersonalitySpecialistSelector",
        
        # Test basic service interfaces
        "from mindflow_backend.interfaces.services import BaseServiceInterface",
        "from mindflow_backend.interfaces.services import CommunicationServiceInterface",
        
        # Test basic infrastructure
        "from mindflow_backend.interfaces.infrastructure import BackendProtocol",
        
        # Test basic API interfaces
        "from mindflow_backend.interfaces.api.controllers import AgentControllerInterface",
        
        # Test basic schemas
        "from mindflow_backend.schemas.memory.api import MemorySearchRequest",
        "from mindflow_backend.schemas.tools.base import ParameterType",
    ]
    
    failed = []
    passed = []
    
    for test in tests:
        try:
            exec(test)
            passed.append(test)
            print(f"✅ {test}")
        except Exception as e:
            failed.append(f"{test}: {e}")
            print(f"❌ {test}: {e}")
    
    print(f"\n📊 Results: {len(passed)} passed, {len(failed)} failed")
    
    if failed:
        print("\n❌ Failed imports:")
        for f in failed:
            print(f"  - {f}")
        return False
    
    return True

def main():
    """Run basic validation."""
    print("🚀 Simple MindFlow Migration Validation")
    print("=" * 50)
    
    if test_basic_imports():
        print("\n" + "=" * 50)
        print("🎉 BASIC IMPORTS PASSED! Migration core is working.")
        return 0
    else:
        print("\n" + "=" * 50)
        print("⚠️  BASIC IMPORTS FAILED! Review core issues.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
