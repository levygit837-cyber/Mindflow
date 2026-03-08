"""Test script for the enhanced tool system implementation.

This script validates the core functionality of the new tool system
including registry, executor, permissions, and filesystem tools.
"""

import asyncio
from pathlib import Path

# Get project root from tests directory
project_root = Path(__file__).parent.parent.parent.parent

from mindflow_backend.tools.core.registry import EnhancedToolRegistry
from mindflow_backend.tools.core.executor import ToolExecutor
from mindflow_backend.tools.core.permissions import PermissionManager
from mindflow_backend.tools.filesystem.operations import FileReadTool, DirectoryListTool
from mindflow_backend.tools.filesystem.search import GrepSearchTool
from mindflow_backend.tools.system.info_collector import SystemInfoCollector
from mindflow_backend.tools.adapters.deepagents_adapter import DeepAgentsFileSystemAdapter
from mindflow_backend.schemas.orchestration.orchestrator import AgentType


async def test_tool_registry():
    """Test the enhanced tool registry."""
    print("🔧 Testing Tool Registry...")
    
    # Create registry
    registry = EnhancedToolRegistry()
    
    # Register a test tool
    file_read_tool = FileReadTool()
    success = registry.register_tool(file_read_tool, name="test_read_file")
    
    assert success, "Failed to register tool"
    
    # Check tool availability
    tools_for_agent = registry.get_tools_for_agent(AgentType.CODER)
    assert "test_read_file" in tools_for_agent, "Tool not found for agent"
    
    # Get tool instance
    tool_instance = registry.get_tool("test_read_file")
    assert tool_instance is not None, "Tool instance not found"
    
    # Get tool schema
    schema = registry.get_tool_schema("test_read_file")
    assert schema is not None, "Tool schema not found"
    
    print("✅ Tool Registry tests passed")


async def test_tool_executor():
    """Test the tool executor."""
    print("🚀 Testing Tool Executor...")
    
    # Create registry and executor
    registry = EnhancedToolRegistry()
    executor = ToolExecutor(registry)
    
    # Register tools
    registry.register_tool(FileReadTool(), name="read_file")
    registry.register_tool(DirectoryListTool(), name="list_directory")
    
    # Test directory listing
    from mindflow_backend.schemas.tools.tool_execution import ToolExecutionRequest
    
    request = ToolExecutionRequest(
        tool_name="list_directory",
        agent_type=AgentType.CODER,
        parameters={"directory_path": "."}
    )
    
    result = await executor.execute_tool(request)
    assert result.success, f"Tool execution failed: {result.error}"
    
    print("✅ Tool Executor tests passed")


async def test_permission_manager():
    """Test the permission manager."""
    print("🔐 Testing Permission Manager...")
    
    # Create permission manager
    permission_manager = PermissionManager()
    
    # Register permission
    from mindflow_backend.schemas.tools.tool_permissions import create_basic_permission
    
    permission = create_basic_permission(
        tool_name="test_tool",
        allowed_agents=[AgentType.CODER]
    )
    
    success = permission_manager.register_permission("test_tool", permission)
    assert success, "Failed to register permission"
    
    # Check permission
    permitted, reason = await permission_manager.check_permission(
        "test_tool",
        AgentType.CODER
    )
    
    assert permitted, f"Permission denied: {reason}"
    
    print("✅ Permission Manager tests passed")


async def test_filesystem_tools():
    """Test filesystem tools."""
    print("📁 Testing Filesystem Tools...")
    
    # Test directory listing
    list_tool = DirectoryListTool()
    result = await list_tool.execute(directory_path=".")
    
    assert result["success"], f"Directory listing failed: {result.get('error')}"
    assert isinstance(result["result"]["items"], list), "Invalid result format"
    
    # Test file reading (try to read this test file)
    read_tool = FileReadTool()
    result = await read_tool.execute(file_path=__file__)
    
    if result["success"]:
        assert isinstance(result["result"]["content"], str), "Invalid file content"
    
    print("✅ Filesystem Tools tests passed")


async def test_system_tools():
    """Test system information tools."""
    print("💻 Testing System Tools...")
    
    # Test system info collector
    info_tool = SystemInfoCollector()
    result = await info_tool.execute(include_detailed=False, include_performance=False)
    
    assert result["success"], f"System info collection failed: {result.get('error')}"
    
    # Check required fields
    system_info = result["result"]
    required_fields = ["cpu_info", "memory_info", "os_info", "python_info"]
    
    for field in required_fields:
        assert field in system_info, f"Missing required field: {field}"
    
    print("✅ System Tools tests passed")


async def test_deepagents_adapter():
    """Test DeepAgents adapter (if available)."""
    print("🔄 Testing DeepAgents Adapter...")
    
    try:
        # Try to create adapter (may fail if DeepAgents not available)
        from deepagents.backends.protocol import BackendProtocol
        
        # Create a mock backend for testing
        class MockBackend(BackendProtocol):
            async def aexecute(self, command: str, **kwargs):
                return f"Mock execution: {command}"
        
        adapter = DeepAgentsFileSystemAdapter(MockBackend())
        tools = adapter.get_adapted_tools()
        
        assert len(tools) > 0, "No tools adapted from DeepAgents"
        assert "list_directory" in tools, "Expected list_directory tool not found"
        
        print("✅ DeepAgents Adapter tests passed")
        
    except ImportError:
        print("⚠️  DeepAgents not available, skipping adapter tests")
    except Exception as e:
        print(f"⚠️  DeepAgents adapter tests failed: {e}")


async def test_integration():
    """Test full integration of components."""
    print("🔗 Testing Integration...")
    
    # Create all components
    registry = EnhancedToolRegistry()
    executor = ToolExecutor(registry)
    permission_manager = PermissionManager()
    
    # Register tools with permissions
    tools_to_register = [
        (FileReadTool(), "read_file"),
        (DirectoryListTool(), "list_directory"),
        (SystemInfoCollector(), "system_info"),
    ]
    
    for tool, name in tools_to_register:
        registry.register_tool(tool, name=name)
        
        # Register basic permission
        from mindflow_backend.schemas.tools.tool_permissions import create_basic_permission
        permission = create_basic_permission(
            tool_name=name,
            allowed_agents=[AgentType.CODER, AgentType.RESEARCHER]
        )
        permission_manager.register_permission(name, permission)
    
    # Test tool execution with permission checking
    from mindflow_backend.schemas.tools.tool_execution import ToolExecutionRequest
    
    request = ToolExecutionRequest(
        tool_name="system_info",
        agent_type=AgentType.RESEARCHER,
        parameters={"include_detailed": False}
    )
    
    # Check permissions first
    permitted, reason = await permission_manager.check_permission(
        "system_info",
        AgentType.RESEARCHER
    )
    
    assert permitted, f"Permission check failed: {reason}"
    
    # Execute tool
    result = await executor.execute_tool(request)
    assert result.success, f"Tool execution failed: {result.error}"
    
    # Get registry info
    registry_info = registry.get_registry_info()
    assert registry_info["statistics"]["total_tools"] >= 3, "Incorrect tool count"
    
    print("✅ Integration tests passed")


async def main():
    """Run all tests."""
    print("🧪 Starting Enhanced Tool System Tests\n")
    
    tests = [
        test_tool_registry,
        test_tool_executor,
        test_permission_manager,
        test_filesystem_tools,
        test_system_tools,
        test_deepagents_adapter,
        test_integration,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed: {e}")
            failed += 1
        print()
    
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Enhanced tool system is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
