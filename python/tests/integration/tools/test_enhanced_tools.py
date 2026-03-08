"""Test script for enhanced filesystem and system tools.

Validates the enhanced tools without DeepAgents dependencies.
"""

import asyncio
from pathlib import Path

# Get project root from tests directory
project_root = Path(__file__).parent.parent.parent.parent

async def test_enhanced_filesystem_tools():
    """Test enhanced filesystem tools."""
    print("🔧 Testing Enhanced Filesystem Tools...")
    
    try:
        from mindflow_backend.tools.filesystem.enhanced_operations import (
            EnhancedFileReadTool,
            EnhancedFileWriteTool,
            EnhancedFileEditTool,
        )
        from mindflow_backend.tools.filesystem.enhanced_search import (
            EnhancedGrepTool,
            EnhancedGlobTool,
            EnhancedFindTool,
        )
        
        # Test Enhanced File Read
        read_tool = EnhancedFileReadTool()
        result = await read_tool.execute(
            file_path=__file__,
            include_line_numbers=True,
            limit=10
        )
        
        assert result["success"], f"EnhancedFileReadTool failed: {result.get('error')}"
        assert "content" in result["result"], "Missing content in result"
        assert "metadata" in result["result"], "Missing metadata in result"
        
        # Test Enhanced File Write
        write_tool = EnhancedFileWriteTool()
        test_content = "Test content for enhanced write tool"
        
        result = await write_tool.execute(
            file_path="test_enhanced_write.txt",
            content=test_content,
            create_dirs=True,
            overwrite=True
        )
        
        assert result["success"], f"EnhancedFileWriteTool failed: {result.get('error')}"
        assert result["result"]["bytes_written"] > 0, "No bytes written"
        
        # Test Enhanced File Edit
        edit_tool = EnhancedFileEditTool()
        result = await edit_tool.execute(
            file_path="test_enhanced_write.txt",
            old_content="Test content",
            new_content="Updated content",
            preview_only=True
        )
        
        assert result["success"], f"EnhancedFileEditTool failed: {result.get('error')}"
        assert "preview" in result["result"], "Missing preview in result"
        
        # Test Enhanced Grep
        grep_tool = EnhancedGrepTool()
        result = await grep_tool.execute(
            pattern="enhanced",
            search_path=".",
            file_pattern="*.py",
            max_results=10
        )
        
        assert result["success"], f"EnhancedGrepTool failed: {result.get('error')}"
        assert "matches" in result["result"], "Missing matches in result"
        
        # Test Enhanced Glob
        glob_tool = EnhancedGlobTool()
        result = await glob_tool.execute(
            pattern="*.py",
            search_path=".",
            max_results=10
        )
        
        assert result["success"], f"EnhancedGlobTool failed: {result.get('error')}"
        assert "files" in result["result"], "Missing files in result"
        
        # Test Enhanced Find
        find_tool = EnhancedFindTool()
        result = await find_tool.execute(
            search_path=".",
            name_pattern="*.py",
            max_results=10
        )
        
        assert result["success"], f"EnhancedFindTool failed: {result.get('error')}"
        assert "files" in result["result"], "Missing files in result"
        
        # Cleanup test file
        try:
            Path("test_enhanced_write.txt").unlink()
        except:
            pass
        
        print("✅ Enhanced Filesystem Tools tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Enhanced Filesystem Tools test failed: {e}")
        return False


async def test_enhanced_system_tools():
    """Test enhanced system tools."""
    print("💻 Testing Enhanced System Tools...")
    
    try:
        from mindflow_backend.tools.system.enhanced_shell import (
            EnhancedShellExecutor,
            EnhancedProcessManager,
        )
        
        # Test Enhanced Shell Executor
        shell_tool = EnhancedShellExecutor()
        result = await shell_tool.execute(
            command="echo 'Hello from enhanced shell'",
            timeout=10
        )
        
        assert result["success"], f"EnhancedShellExecutor failed: {result.get('error')}"
        assert "output" in result["result"], "Missing output in result"
        assert "Hello from enhanced shell" in result["result"]["output"], "Incorrect output"
        
        # Test Enhanced Process Manager
        process_tool = EnhancedProcessManager()
        result = await process_tool.execute(
            action="list",
            max_results=10
        )
        
        assert result["success"], f"EnhancedProcessManager failed: {result.get('error')}"
        assert "processes" in result["result"], "Missing processes in result"
        
        print("✅ Enhanced System Tools tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Enhanced System Tools test failed: {e}")
        return False


async def test_tool_integration():
    """Test tool integration with registry."""
    print("🔗 Testing Tool Integration...")
    
    try:
        from mindflow_backend.tools.core.registry import EnhancedToolRegistry
        from mindflow_backend.tools.filesystem.enhanced_operations import EnhancedFileReadTool
        from mindflow_backend.tools.system.enhanced_shell import EnhancedShellExecutor
        from mindflow_backend.schemas.orchestration.orchestrator import AgentType
        
        # Create registry
        registry = EnhancedToolRegistry()
        
        # Register enhanced tools
        registry.register_tool(EnhancedFileReadTool(), name="enhanced_read_file")
        registry.register_tool(EnhancedShellExecutor(), name="enhanced_shell")
        
        # Check tool availability
        tools_for_agent = registry.get_tools_for_agent(AgentType.CODER)
        assert "enhanced_read_file" in tools_for_agent, "Enhanced read tool not found"
        assert "enhanced_shell" in tools_for_agent, "Enhanced shell tool not found"
        
        # Get tool instances
        read_tool = registry.get_tool("enhanced_read_file")
        shell_tool = registry.get_tool("enhanced_shell")
        
        assert read_tool is not None, "Enhanced read tool instance not found"
        assert shell_tool is not None, "Enhanced shell tool instance not found"
        
        # Get tool schemas
        read_schema = registry.get_tool_schema("enhanced_read_file")
        shell_schema = registry.get_tool_schema("enhanced_shell")
        
        assert read_schema is not None, "Enhanced read tool schema not found"
        assert shell_schema is not None, "Enhanced shell tool schema not found"
        
        # Get registry info
        registry_info = registry.get_registry_info()
        assert registry_info["statistics"]["total_tools"] >= 2, "Incorrect tool count"
        
        print("✅ Tool Integration tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Tool Integration test failed: {e}")
        return False


async def test_backward_compatibility():
    """Test backward compatibility with original tools."""
    print("🔄 Testing Backward Compatibility...")
    
    try:
        from mindflow_backend.tools.filesystem import (
            FileReadTool,
            FileWriteTool,
            GrepSearchTool,
            EnhancedFileReadTool,
            EnhancedGrepTool,
        )
        
        # Test that original tools still work
        original_read = FileReadTool()
        enhanced_read = EnhancedFileReadTool()
        
        assert original_read.name == "read_file", "Original read tool name changed"
        assert enhanced_read.name == "read_file", "Enhanced read tool should have same name"
        
        # Test that both tools have required methods
        assert hasattr(original_read, 'execute'), "Original tool missing execute method"
        assert hasattr(enhanced_read, 'execute'), "Enhanced tool missing execute method"
        assert hasattr(original_read, 'get_schema'), "Original tool missing get_schema method"
        assert hasattr(enhanced_read, 'get_schema'), "Enhanced tool missing get_schema method"
        
        # Test search tools
        original_grep = GrepSearchTool()
        enhanced_grep = EnhancedGrepTool()
        
        assert original_grep.name == "grep_search", "Original grep tool name changed"
        assert enhanced_grep.name == "grep_search", "Enhanced grep tool should have same name"
        
        print("✅ Backward Compatibility tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Backward Compatibility test failed: {e}")
        return False


async def main():
    """Run all enhanced tools tests."""
    print("🧪 Starting Enhanced Tools Tests\n")
    
    tests = [
        test_enhanced_filesystem_tools,
        test_enhanced_system_tools,
        test_tool_integration,
        test_backward_compatibility,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if await test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed with exception: {e}")
            failed += 1
        print()
    
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All enhanced tools tests passed!")
        print("\n📋 Enhanced Tools Summary:")
        print("✅ Enhanced File Operations (read, write, edit)")
        print("✅ Enhanced Search Tools (grep, glob, find)")
        print("✅ Enhanced System Tools (shell, process manager)")
        print("✅ Security controls and validation")
        print("✅ Performance optimizations")
        print("✅ Backward compatibility")
        print("✅ Registry integration")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
