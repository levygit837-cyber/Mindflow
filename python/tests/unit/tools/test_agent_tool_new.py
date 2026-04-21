"""Unit tests for AgentTool."""

import pytest

from mindflow_backend.agents.tools.orchestration import AgentTool


@pytest.fixture
def agent_tool():
    """Create an AgentTool instance."""
    return AgentTool()


class TestAgentTool:
    """Test AgentTool functionality."""

    def test_tool_name(self, agent_tool: AgentTool) -> None:
        """Test that tool has correct name."""
        assert agent_tool.name == "AgentTool"

    def test_tool_description(self, agent_tool: AgentTool) -> None:
        """Test that tool has description."""
        assert agent_tool.description
        assert "delegate" in agent_tool.description.lower()

    def test_get_schema(self, agent_tool: AgentTool) -> None:
        """Test that schema is valid."""
        schema = agent_tool.get_schema()
        assert schema["name"] == "AgentTool"
        assert "parameters" in schema
        assert "description" in schema["parameters"]
        
        # Check required parameters
        required = schema["parameters"].get("required", [])
        assert "description" in required
        assert "prompt" in required

    def test_schema_has_required_fields(self, agent_tool: AgentTool) -> None:
        """Test that schema has all required fields."""
        schema = agent_tool.get_schema()
        properties = schema["parameters"]["properties"]
        
        # Claude-style parameters
        assert "description" in properties
        assert "prompt" in properties
        assert "subagent_type" in properties
        assert "model" in properties
        assert "run_in_background" in properties
        assert "name" in properties
        assert "isolation" in properties
        
        # Preserved from delegate_to_agent
        assert "scope" in properties
        assert "context" in properties
        assert "expected_output" in properties
