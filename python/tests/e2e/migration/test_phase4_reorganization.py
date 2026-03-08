#!/usr/bin/env python3
"""Phase 4: Test reorganized structure."""

from pathlib import Path

# Get project root from tests directory
project_root = Path(__file__).parent.parent.parent.parent

def test_phase4_reorganization():
    """Test Phase 4 reorganization results."""
    print("🗂️ Phase 4: Testing Reorganized Structure")
    
    base_path = project_root / "python" / "mindflow_backend" / "agents" / "tools"
    
    # Test directory structure
    expected_categories = ["filesystem", "system", "web", "ai", "data", "integration", "code", "research", "base"]
    
    existing_categories = []
    for category in expected_categories:
        category_path = base_path / category
        if category_path.exists():
            existing_categories.append(category)
            print(f"✅ {category}/ exists")
        else:
            print(f"❌ {category}/ missing")
    
    print(f"\n📊 Directory Structure:")
    print(f"   - Categories: {len(existing_categories)}/{len(expected_categories)}")
    
    # Test key files
    key_files = [
        "filesystem/file_operations.py",
        "filesystem/search_tools.py",
        "system/shell_executor.py",
        "system/resource_monitor.py",
        "system/system_info.py",
        "web/web_scraper.py",
        "ai/model_tools.py",
        "data/data_tools.py",
        "integration/integration_tools.py",
    ]
    
    existing_files = []
    syntax_errors = []
    
    for file_path in key_files:
        full_path = base_path / file_path
        if full_path.exists():
            existing_files.append(file_path)
            
            # Test syntax
            try:
                with open(full_path, 'r') as f:
                    content = f.read()
                compile(content, str(full_path), 'exec')
                print(f"   ✅ {file_path} - Syntax OK")
            except SyntaxError as e:
                print(f"   ❌ {file_path} - Syntax Error: {e}")
                syntax_errors.append(file_path)
        else:
            print(f"   ❌ {file_path} missing")
    
    print(f"\n📊 Key Files Status:")
    print(f"   - Files found: {len(existing_files)}/{len(key_files)}")
    print(f"   - Syntax errors: {len(syntax_errors)}")
    
    # Test imports (basic check)
    print(f"\n🧪 Testing Basic Imports...")
    
    import_tests = [
        ("Filesystem", "from mindflow_backend.agents.tools.filesystem import FileReadTool"),
        ("System", "from mindflow_backend.agents.tools.system import ShellExecutorTool"),
        ("Web", "from mindflow_backend.agents.tools.web import WebScraperTool"),
        ("AI", "from mindflow_backend.agents.tools.ai import LocalModelTool"),
        ("Data", "from mindflow_backend.agents.tools.data import DatabaseTool"),
        ("Integration", "from mindflow_backend.agents.tools.integration import GitTool"),
    ]
    
    import_errors = []
    
    for test_name, import_statement in import_tests:
        try:
            exec(import_statement)
            print(f"   ✅ {test_name} - Import OK")
        except Exception as e:
            print(f"   ❌ {test_name} - Import Error: {e}")
            import_errors.append(test_name)
    
    print(f"\n📊 Import Status:")
    print(f"   - Import errors: {len(import_errors)}")
    
    return len(existing_categories) >= 7 and len(syntax_errors) == 0 and len(import_errors) <= 2

def main():
    """Run Phase 4 testing."""
    print("🧪 Starting Phase 4 Reorganization Testing\n")
    
    success = test_phase4_reorganization()
    
    if success:
        print("\n🎉 Phase 4 Reorganization Successful!")
        print("\n📋 Next Steps:")
        print("   - Phase 5: Final cleanup")
        print("   - Remove old /tools directory")
        print("   - Update all imports in codebase")
        print("   - Final testing and validation")
        print("\n🚀 System Ready for Final Phase!")
    else:
        print("\n⚠️ Phase 4 Reorganization Issues Found")
        print("   - Check missing files or directories")
        print("   - Fix remaining syntax errors")
        print("   - Resolve import issues")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
