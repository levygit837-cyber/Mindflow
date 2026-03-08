#!/usr/bin/env python3
"""Phase 3: Unify overlapping tools between agents and backend."""

import os
import shutil
from pathlib import Path

def copy_best_implementation(source_file: Path, target_file: Path) -> bool:
    """Copy the best implementation from backend to agents."""
    try:
        # Ensure target directory exists
        target_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy the file
        shutil.copy2(source_file, target_file)
        print(f"✅ Copied {source_file.name} -> {target_file}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to copy {source_file}: {e}")
        return False

def phase3_unification():
    """Phase 3: Unify overlapping tools."""
    print("🔄 Phase 3: Unifying Overlapping Tools")
    
    base_path = Path("mindflow_backend")
    backend_tools = base_path / "tools"
    agents_tools = base_path / "agents" / "tools"
    
    # Tools to unify (backend -> agents)
    unification_map = [
        # Filesystem tools
        ("filesystem/file_operations.py", "filesystem/file_operations_unified.py"),
        ("filesystem/search_tools.py", "filesystem/search_tools_unified.py"),
        
        # System tools - add missing ones
        ("system/shell_tools.py", "system/shell_executor.py"),
        ("system/resource_monitor.py", "system/resource_monitor.py"),
        ("system/info_collector.py", "system/system_info.py"),
        
        # Web tools - add missing one
        ("web/web_tools.py", "web/web_scraper.py"),
    ]
    
    unified_count = 0
    
    for source_relative, target_relative in unification_map:
        source_file = backend_tools / source_relative
        target_file = agents_tools / target_relative
        
        if source_file.exists():
            if copy_best_implementation(source_file, target_file):
                unified_count += 1
        else:
            print(f"⚠️  Source file not found: {source_file}")
    else:
        print(f"⚠️  Target path invalid: {target_file}")
    
    print(f"\n📊 Phase 3 Unification Summary:")
    print(f"   - Files unified: {unified_count}")
    print(f"   - Status: Ready for Phase 4")
    
    return unified_count > 0

def main():
    """Run Phase 3 unification."""
    print("🧪 Starting Phase 3 Tool Unification\n")
    
    success = phase3_unification()
    
    if success:
        print("\n🎉 Phase 3 Unification Successful!")
        print("\n📋 Next Steps:")
        print("   - Phase 4: Reorganization and cleanup")
        print("   - Update imports and __init__.py files")
        print("   - Remove old /tools directory")
        print("   - Final testing and validation")
    else:
        print("\n⚠️ Phase 3 Unification Issues Found")
        print("   - Check missing source files")
        print("   - Verify file permissions")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
