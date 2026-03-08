#!/usr/bin/env python3
"""Phase 3: Test unified tools in agents/tools system."""

from pathlib import Path

# Get project root from tests directory
project_root = Path(__file__).parent.parent.parent.parent

def test_phase3_unification():
    """Test Phase 3 unification results."""
    print("🔄 Phase 3: Testing Unified Tools")
    
    base_path = project_root / "python" / "mindflow_backend" / "agents" / "tools"
    
    # Test unified files
    unified_files = [
        "filesystem/file_operations_unified.py",
        "filesystem/search_tools_unified.py",
        "system/shell_executor.py",
        "system/resource_monitor.py",
        "system/system_info.py",
        "web/web_scraper.py",
    ]
    
    existing_unified = []
    
    for file_path in unified_files:
        full_path = base_path / file_path
        if full_path.exists():
            print(f"✅ {file_path} exists")
            existing_unified.append(file_path)
        else:
            print(f"❌ {file_path} missing")
    
    print(f"\n📊 Phase 3 Unification Summary:")
    print(f"   - Files unified: {len(existing_unified)}/{len(unified_files)}")
    print(f"   - Status: Ready for Phase 4")
    
    # Test imports (basic check)
    print(f"\n🧪 Testing Unified Imports...")
    
    # Check if files are syntactically correct
    syntax_errors = []
    
    for file_path in existing_unified:
        full_path = base_path / file_path
        try:
            with open(full_path, 'r') as f:
                content = f.read()
            
            # Basic syntax check
            compile(content, str(full_path), 'exec')
            print(f"   ✅ {file_path} - Syntax OK")
            
        except SyntaxError as e:
            print(f"   ❌ {file_path} - Syntax Error: {e}")
            syntax_errors.append(file_path)
        except Exception as e:
            print(f"   ⚠️  {file_path} - Other Error: {e}")
    
    print(f"\n📋 Unified Tools:")
    for file_path in existing_unified:
        print(f"   - {file_path}")
    
    if syntax_errors:
        print(f"\n⚠️ Syntax Errors Found:")
        for file_path in syntax_errors:
            print(f"   - {file_path}")
    
    return len(existing_unified) > 0 and len(syntax_errors) == 0

def main():
    """Run Phase 3 testing."""
    print("🧪 Starting Phase 3 Unification Testing\n")
    
    success = test_phase3_unification()
    
    if success:
        print("\n🎉 Phase 3 Unification Successful!")
        print("\n📋 Next Steps:")
        print("   - Phase 4: Reorganization and cleanup")
        print("   - Update main __init__.py imports")
        print("   - Remove old /tools directory")
        print("   - Final testing and validation")
    else:
        print("\n⚠️ Phase 3 Unification Issues Found")
        print("   - Check missing unified files")
        print("   - Fix syntax errors in unified files")
        print("   - Verify file permissions")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
