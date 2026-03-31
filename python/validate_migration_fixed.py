#!/usr/bin/env python3
"""Script to validate the migration of interfaces and schemas."""

import sys
from pathlib import Path


def check_imports():
    """Test if all new imports work correctly."""
    print("🔍 Validating imports...")
    
    tests = [
        # Test agent interfaces
        "from mindflow_backend.interfaces.agents import EnhancedResearcher",
        "from mindflow_backend.interfaces.agents import TaskRagAgent", 
        "from mindflow_backend.interfaces.agents import CorePersonalityContract",
        "from mindflow_backend.interfaces.agents import PersonalitySpecialistSelector",
        
        # Test service interfaces
        "from mindflow_backend.interfaces.services import ContextRetrievalServiceInterface",
        "from mindflow_backend.interfaces.services import ContextEmbeddingServiceInterface",
        
        # Test infrastructure interfaces
        "from mindflow_backend.interfaces.infrastructure import BackendProtocol",
        
        # Test orchestrator interfaces
        "from mindflow_backend.interfaces.orchestrator import PersonalityManagerContract",
        
        # Test error interfaces
        "from mindflow_backend.interfaces.errors import ValidationErrorHandlerContract",
        
        # Test API interfaces
        "from mindflow_backend.interfaces.api import ControllerInterface",
        "from mindflow_backend.interfaces.api import ServiceInterface",
        
        # Test schemas
        "from mindflow_backend.schemas.memory.api import MemorySearchRequest",
        "from mindflow_backend.schemas.tools.base import ToolSchema",
        "from mindflow_backend.schemas.api.common import CommonSchema",
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

def check_file_structure():
    """Check if migrated files exist in correct locations."""
    print("\n📁 Checking file structure...")
    
    required_files = [
        # Agent interfaces
        "interfaces/agents/researcher.py",
        "interfaces/agents/task_rag_agent.py",
        "interfaces/agents/personality.py",
        
        # Service interfaces  
        "interfaces/services/context.py",
        
        # Infrastructure
        "interfaces/infrastructure/backend.py",
        
        # Orchestrator
        "interfaces/orchestrator/personality.py",
        
        # Errors
        "interfaces/errors/validation.py",
        
        # API
        "interfaces/api/legacy.py",
    ]
    
    base_path = Path("/home/levybonito/Projetos/MindFlow/python/mindflow_backend")
    missing = []
    existing = []
    
    for file_path in required_files:
        full_path = base_path / file_path
        if full_path.exists():
            existing.append(str(file_path))
            print(f"✅ {file_path}")
        else:
            missing.append(str(file_path))
            print(f"❌ {file_path}")
    
    print(f"\n📊 File Results: {len(existing)} exist, {len(missing)} missing")
    
    if missing:
        print("\n❌ Missing files:")
        for f in missing:
            print(f"  - {f}")
        return False
    
    return True

def check_old_files():
    """Check if old files still exist (should be aliases)."""
    print("\n🔍 Checking old files for aliases...")
    
    old_files = [
        "agents/interfaces/agents/researcher.py",
        "agents/interfaces/agents/task_rag_agent.py", 
        "agents/interfaces/core/personality.py",
        "services/interfaces/context_interfaces.py",
        "api/interfaces/__init__.py",
    ]
    
    base_path = Path("/home/levybonito/Projetos/MindFlow/python/mindflow_backend")
    aliases = []
    non_aliases = []
    
    for file_path in old_files:
        full_path = base_path / file_path
        if full_path.exists():
            with open(full_path) as f:
                content = f.read()
                if "DEPRECATED" in content or "forward compatibility" in content:
                    aliases.append(str(file_path))
                    print(f"✅ {file_path} (has alias)")
                else:
                    non_aliases.append(str(file_path))
                    print(f"⚠️  {file_path} (needs alias)")
        else:
            print(f"✅ {file_path} (removed)")
    
    print(f"\n📊 Old Files: {len(aliases)} have aliases, {len(non_aliases)} need aliases")
    
    if non_aliases:
        print("\n⚠️ Files needing aliases:")
        for f in non_aliases:
            print(f"  - {f}")
    
    return len(non_aliases) == 0

def main():
    """Run all validation checks."""
    print("🚀 MindFlow Migration Validation")
    print("=" * 50)
    
    checks = [
        ("File Structure", check_file_structure),
        ("Import Tests", check_imports),
        ("Old File Aliases", check_old_files),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} check failed: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 50)
    print("📋 SUMMARY")
    print("=" * 50)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ALL CHECKS PASSED! Migration appears successful.")
        return 0
    else:
        print("⚠️  SOME CHECKS FAILED! Review the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
