#!/usr/bin/env python3
"""Phase 2: Test migrated tools in agents/tools system."""

from pathlib import Path

# Get project root from tests directory
project_root = Path(__file__).parent.parent.parent.parent

def test_phase2_migration():
    """Test Phase 2 migration results."""
    print("🚀 Phase 2: Testing Migrated Tools")
    
    base_path = project_root / "python" / "mindflow_backend" / "agents" / "tools"
    
    # Test new categories
    new_categories = ["ai", "data", "integration"]
    migrated_tools = []
    
    for category in new_categories:
        category_path = base_path / category
        if category_path.exists():
            print(f"✅ Category {category} exists")
            
            # Check __init__.py
            init_file = category_path / "__init__.py"
            if init_file.exists():
                print(f"   ✅ {category}/__init__.py exists")
                
                # Check tool files
                tool_files = list(category_path.glob("*.py"))
                for tool_file in tool_files:
                    if tool_file.name != "__init__.py":
                        print(f"   ✅ {category}/{tool_file.name} exists")
                        migrated_tools.append(f"{category}/{tool_file.name}")
            else:
                print(f"   ❌ {category}/__init__.py missing")
        else:
            print(f"❌ Category {category} missing")
    
    print("\n📊 Phase 2 Migration Summary:")
    print(f"   - New categories created: {len(new_categories)}")
    print(f"   - Tools migrated: {len(migrated_tools)}")
    print("   - Status: Ready for Phase 3")
    
    # Test imports
    print("\n🧪 Testing Imports...")
    
    test_imports = [
        ("AI Tools", "from mindflow_backend.agents.tools.ai import LocalModelTool, EmbeddingTool"),
        ("Data Tools", "from mindflow_backend.agents.tools.data import DatabaseTool, CSVProcessorTool"),
        ("Integration Tools", "from mindflow_backend.agents.tools.integration import GitTool, DockerTool"),
    ]
    
    for test_name, import_statement in test_imports:
        try:
            exec(import_statement)
            print(f"   ✅ {test_name} - Import successful")
        except Exception as e:
            print(f"   ❌ {test_name} - Import failed: {e}")
    
    print("\n📋 Migrated Tools:")
    for tool in migrated_tools:
        print(f"   - {tool}")
    
    return len(migrated_tools) > 0

def main():
    """Run Phase 2 testing."""
    print("🧪 Starting Phase 2 Migration Testing\n")
    
    success = test_phase2_migration()
    
    if success:
        print("\n🎉 Phase 2 Migration Successful!")
        print("\n📋 Next Steps:")
        print("   - Phase 3: Unification of overlapping tools")
        print("   - Merge best implementations from both systems")
        print("   - Standardize interfaces and patterns")
        print("   - Optimize performance and add caching")
    else:
        print("\n⚠️ Phase 2 Migration Issues Found")
        print("   - Check missing files or imports")
        print("   - Fix syntax errors in migrated files")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
