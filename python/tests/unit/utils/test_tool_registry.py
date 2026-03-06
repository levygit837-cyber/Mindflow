import pytest
from pathlib import Path
from mindflow_backend.agents.tools import create_default_registry
from mindflow_backend.agents.tools.sandbox import MindFlowSandbox
from mindflow_backend.schemas.orchestrator import AgentType

def test_tool_registry_scopes():
    # Setup a mock sandbox
    sandbox = MindFlowSandbox(root_dir="./test_sandbox")
    registry = create_default_registry(sandbox)
    
    # Check all tool names
    all_tools = registry.get_all_tool_names()
    assert "read_file" in all_tools
    assert "ls_info" in all_tools
    
    # By default, create_default_registry registers tools for all agents
    coder_tools = registry.get_tools_for_agent(AgentType.CODER)
    analyst_tools = registry.get_tools_for_agent(AgentType.ANALYST)
    
    assert len(coder_tools) > 0
    assert len(analyst_tools) > 0

def test_sandbox_execution():
    sandbox = MindFlowSandbox()
    result = sandbox.execute("echo 'hello world'")
    
    assert result.exit_code == 0
    assert "hello world" in result.output

def test_sandbox_filesystem(tmp_path):
    sandbox = MindFlowSandbox(root_dir=tmp_path)
    
    # Write a file
    write_result = sandbox.write("test.txt", "content")
    assert write_result.error is None
    assert (tmp_path / "test.txt").read_text() == "content"
    
    # Read via sandbox
    content = sandbox.read("test.txt")
    assert "content" in content
