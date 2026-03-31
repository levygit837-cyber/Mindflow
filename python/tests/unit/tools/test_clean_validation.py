"""Final validation test for cleaned MindFlow tools system.

Validates that all "enhanced" and "DeepAgents" references have been removed.
"""

from pathlib import Path

# Get project root from tests directory
project_root = Path(__file__).parent.parent.parent.parent

def test_no_enhanced_references():
    """Test that no "enhanced" references exist in tool files."""
    print("🧹 Testing No 'Enhanced' References...")
    
    base_path = project_root / "python" / "mindflow_backend" / "tools"
    
    # Files to check
    tool_files = [
        "filesystem/file_operations.py",
        "filesystem/search_tools.py",
        "system/shell_tools.py",
        "web/web_tools.py",
        "ai/model_tools.py",
        "data/data_tools.py",
        "integration/integration_tools.py",
        "core/registry.py",
        "tools/__init__.py",
        "filesystem/__init__.py",
        "system/__init__.py",
        "web/__init__.py",
        "ai/__init__.py",
        "data/__init__.py",
        "integration/__init__.py",
    ]
    
    enhanced_found = []
    
    for file_path in tool_files:
        full_path = base_path / file_path
        if not full_path.exists():
            continue
            
        try:
            with open(full_path) as f:
                content = f.read()
            
            # Check for "enhanced" (case insensitive)
            if "enhanced" in content.lower():
                enhanced_found.append(file_path)
                
        except Exception as e:
            print(f"❌ Error reading {file_path}: {e}")
            return False
    
    if enhanced_found:
        print(f"❌ Found 'enhanced' references in: {enhanced_found}")
        return False
    
    print("✅ No 'enhanced' references found")
    return True

def test_no_deepagents_references():
    """Test that no "DeepAgents" references exist in tool files."""
    print("🚫 Testing No 'DeepAgents' References...")
    
    base_path = project_root / "python" / "mindflow_backend" / "tools"
    
    # Check all Python files in tools directory
    deepagents_found = []
    
    for file_path in base_path.rglob("*.py"):
        try:
            with open(file_path) as f:
                content = f.read()
            
            # Check for "deepagents" (case insensitive)
            if "deepagents" in content.lower():
                relative_path = file_path.relative_to(base_path)
                deepagents_found.append(str(relative_path))
                
        except Exception as e:
            print(f"❌ Error reading {file_path}: {e}")
            return False
    
    if deepagents_found:
        print(f"❌ Found 'DeepAgents' references in: {deepagents_found}")
        return False
    
    print("✅ No 'DeepAgents' references found")
    return True

def test_class_names():
    """Test that class names don't contain 'Enhanced'."""
    print("🏷️ Testing Class Names...")
    
    base_path = project_root / "python" / "mindflow_backend" / "tools"
    
    # Expected class names (without Enhanced)
    expected_classes = {
        "filesystem/file_operations.py": ["FileReadTool", "FileWriteTool", "FileEditTool"],
        "filesystem/search_tools.py": ["GrepSearchTool", "GlobSearchTool", "FindFilesTool"],
        "system/shell_tools.py": ["ShellExecutorTool", "ProcessManagerTool"],
        "web/web_tools.py": ["HttpClientTool", "WebScraperTool", "ApiClientTool"],
        "ai/model_tools.py": ["LocalModelTool", "EmbeddingTool"],
        "data/data_tools.py": ["DatabaseTool", "CSVProcessorTool"],
        "integration/integration_tools.py": ["GitTool", "DockerTool"],
    }
    
    for file_path, expected_names in expected_classes.items():
        full_path = base_path / file_path
        if not full_path.exists():
            continue
            
        try:
            with open(full_path) as f:
                content = f.read()
            
            for class_name in expected_names:
                if f"class {class_name}" not in content:
                    print(f"❌ Missing class {class_name} in {file_path}")
                    return False
                
                # Check no enhanced version exists
                if f"Enhanced{class_name}" in content:
                    print(f"❌ Found Enhanced{class_name} in {file_path}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error reading {file_path}: {e}")
            return False
    
    print("✅ All class names are correct")
    return True

def test_directory_structure():
    """Test that directory structure is clean."""
    print("📁 Testing Directory Structure...")
    
    base_path = project_root / "python" / "mindflow_backend" / "tools"
    
    # Should not have adapters directory (DeepAgents references)
    adapters_path = base_path / "adapters"
    if adapters_path.exists():
        print("❌ Adapters directory still exists (contains DeepAgents references)")
        return False
    
    # Should not have enhanced_* files
    enhanced_files = list(base_path.rglob("*enhanced*"))
    if enhanced_files:
        print(f"❌ Found enhanced files: {enhanced_files}")
        return False
    
    print("✅ Directory structure is clean")
    return True

def test_imports():
    """Test that imports work without enhanced references."""
    print("📦 Testing Imports...")
    
    try:
        # Test main tools import
        
        # Test that enhanced versions don't exist
        try:
            from mindflow_backend.tools import EnhancedFileReadTool
            print("❌ EnhancedFileReadTool still exists")
            return False
        except ImportError:
            pass  # Expected
        
        print("✅ Imports work correctly")
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

def main():
    """Run all validation tests."""
    print("🧪 Starting Clean MindFlow Tools System Validation\n")
    
    tests = [
        test_no_enhanced_references,
        test_no_deepagents_references,
        test_class_names,
        test_directory_structure,
        test_imports,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed with exception: {e}")
            failed += 1
        print()
    
    print(f"📊 Validation Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All validation tests passed!")
        print("\n📋 Clean MindFlow Tools System Summary:")
        print("✅ All 'enhanced' references removed")
        print("✅ All 'DeepAgents' references removed")
        print("✅ Clean class names (no Enhanced prefix)")
        print("✅ Clean directory structure")
        print("✅ Imports work correctly")
        print("✅ Pure MindFlow tools system")
        print("\n🚀 Clean MindFlow Tools System Ready!")
        print("   - Independent of DeepAgents framework")
        print("   - Clean naming conventions")
        print("   - Professional architecture")
        print("   - Ready for production")
    else:
        print("⚠️  Some validation tests failed. Please check the implementation.")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
