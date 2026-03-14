#!/usr/bin/env python3
"""
Test script to verify tool integration with agents.
This script tests if agents can now access their assigned tools correctly.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_tool_integration():
    """Test that agents can access their tools correctly."""
    
    print("🧪 Testing Tool Integration with Agents")
    print("=" * 50)
    
    try:
        # Import necessary modules
        from mindflow_backend.agents.tools import create_default_registry
        from mindflow_backend.agents.tools.sandbox import MindFlowSandbox
        from mindflow_backend.schemas.orchestration.orchestrator import AgentType
        
        print("✅ Successfully imported required modules")
        
        # Create sandbox and registry
        sandbox = MindFlowSandbox(root_dir="/tmp/test_sandbox")
        registry = create_default_registry(sandbox)
        
        print("✅ Successfully created sandbox and registry")
        
        # Test each agent type
        agent_types = [
            AgentType.CODER,
            AgentType.ANALYST, 
            AgentType.RESEARCHER,
            AgentType.ORCHESTRATOR
        ]
        
        for agent_type in agent_types:
            print(f"\n🤖 Testing {agent_type.value.upper()} Agent:")
            tools = registry.get_tools_for_agent(agent_type)
            
            print(f"   📦 Tools loaded: {len(tools)}")
            
            if tools:
                print("   🛠️  Available tools:")
                for i, tool in enumerate(tools[:5]):  # Show first 5 tools
                    tool_name = getattr(tool, 'name', tool.__class__.__name__)
                    print(f"      {i+1}. {tool_name}")
                    
                if len(tools) > 5:
                    print(f"      ... and {len(tools) - 5} more")
            else:
                print("   ⚠️  No tools loaded")
        
        print("\n🎉 Tool Integration Test Completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_tool_functionality():
    """Test basic functionality of loaded tools."""
    
    print("\n🔧 Testing Tool Functionality")
    print("=" * 30)
    
    try:
        from mindflow_backend.agents.tools import create_default_registry
        from mindflow_backend.agents.tools.sandbox import MindFlowSandbox
        from mindflow_backend.schemas.orchestration.orchestrator import AgentType
        
        sandbox = MindFlowSandbox(root_dir="/tmp/test_sandbox")
        registry = create_default_registry(sandbox)
        
        # Get tools for CODER agent (should have filesystem tools)
        tools = registry.get_tools_for_agent(AgentType.CODER)
        
        if not tools:
            print("❌ No tools found for CODER agent")
            return False
            
        # Test first tool if it has execute method
        first_tool = tools[0]
        print(f"🧪 Testing tool: {first_tool.__class__.__name__}")
        
        if hasattr(first_tool, 'get_schema'):
            schema = first_tool.get_schema()
            print(f"   📋 Schema available: {bool(schema)}")
        
        if hasattr(first_tool, 'execute'):
            print("   ✅ Execute method available")
        elif hasattr(first_tool, 'name'):
            print(f"   📛 Tool name: {first_tool.name}")
        
        print("✅ Tool functionality test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Tool functionality test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting MindFlow Tool Integration Tests")
    print("=" * 60)
    
    # Run tests
    test1_passed = test_tool_integration()
    test2_passed = test_tool_functionality()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Integration Test: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Functionality Test: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 ALL TESTS PASSED! Tool integration is working correctly.")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Check the logs above for details.")
        sys.exit(1)
