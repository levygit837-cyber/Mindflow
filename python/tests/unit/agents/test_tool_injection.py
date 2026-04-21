"""Tests for tool injection module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from mindflow_backend.agents._base import BaseAgent
from mindflow_backend.agents.tools.tool_injection import (
    ToolPromptInjector,
    get_tool_descriptions_section,
    inject_tools_into_prompt,
)
from mindflow_backend.schemas.orchestration.orchestrator import AgentType, ToolScope


class MockTool:
    """Mock tool for testing."""

    def __init__(self, name: str, description: str, input_schema: dict | None = None):
        self.name = name
        self.description = description
        self.input_schema = input_schema


class MockRegistry:
    """Mock registry for testing."""

    def __init__(self, tools: list[MockTool] | None = None):
        self._tools = {t.name: t for t in (tools or [])}

    def filter_by_category(self, category: str) -> list[MockTool]:
        return list(self._tools.values())


@pytest.fixture
def mock_agent():
    """Create a mock agent with tool scopes."""
    return BaseAgent(
        agent_role=AgentType.CODER,
        system_prompt="You are a coder.",
        tools=[ToolScope.FILESYSTEM, ToolScope.SHELL],
    )


@pytest.fixture
def mock_registry():
    """Create a mock registry with sample tools."""
    tools = [
        MockTool(
            "Read",
            "Reads a file from the filesystem.",
            {"type": "object", "properties": {"file_path": {"type": "string"}}},
        ),
        MockTool(
            "Write",
            "Writes content to a file.",
            {"type": "object", "properties": {"file_path": {"type": "string"}, "content": {"type": "string"}}},
        ),
        MockTool(
            "Bash",
            "Executes a shell command.",
            {"type": "object", "properties": {"command": {"type": "string"}}},
        ),
    ]
    return MockRegistry(tools)


def test_generate_tool_descriptions(mock_registry, mock_agent):
    """Test that tool descriptions are generated in XML format."""
    injector = ToolPromptInjector(mock_registry)
    result = injector.generate_tool_descriptions(mock_agent)

    assert "# Available Tools" in result
    assert "<functions>" in result
    assert "<name>Read</name>" in result
    assert "<name>Write</name>" in result
    assert "<name>Bash</name>" in result
    assert "Reads a file" in result
    assert "</functions>" in result


def test_generate_tool_descriptions_empty_registry():
    """Test empty registry returns empty string."""
    registry = MockRegistry([])
    agent = BaseAgent(
        agent_role=AgentType.CODER,
        system_prompt="Test",
        tools=[ToolScope.FILESYSTEM],
    )
    injector = ToolPromptInjector(registry)
    result = injector.generate_tool_descriptions(agent)
    assert result == ""


def test_generate_usage_instructions(mock_registry, mock_agent):
    """Test usage instructions are generated based on agent scopes."""
    injector = ToolPromptInjector(mock_registry)
    result = injector.generate_usage_instructions(mock_agent)

    assert "# Using Your Tools" in result
    assert "Read tool" in result or "read files" in result.lower()


def test_inject_into_system_prompt(mock_registry, mock_agent):
    """Test tool injection into system prompt."""
    injector = ToolPromptInjector(mock_registry)
    base_prompt = "You are a helpful assistant."
    result = injector.inject_into_system_prompt(base_prompt, mock_agent)

    assert base_prompt in result
    assert "<functions>" in result
    assert "# Available Tools" in result


def test_format_tool_as_xml(mock_registry):
    """Test individual tool formatting."""
    injector = ToolPromptInjector(mock_registry)
    tool = MockTool("TestTool", "A test tool.", {"type": "object"})
    result = injector._format_tool_as_xml(tool)

    assert "<function>" in result
    assert "<name>TestTool</name>" in result
    assert "<description>A test tool.</description>" in result
    assert "<parameters>" in result
    assert "</function>" in result


def test_format_tool_without_schema():
    """Test tool formatting without input schema."""
    registry = MockRegistry([])
    injector = ToolPromptInjector(registry)
    tool = MockTool("NoSchema", "Tool without schema.", None)
    result = injector._format_tool_as_xml(tool)

    assert "<name>NoSchema</name>" in result
    assert "<parameters>{}</parameters>" in result


def test_get_tool_descriptions_section(mock_registry, mock_agent):
    """Test convenience function."""
    result = get_tool_descriptions_section(mock_registry, mock_agent)
    assert "<functions>" in result


def test_inject_tools_into_prompt(mock_registry, mock_agent):
    """Test convenience function for full injection."""
    base = "Base prompt."
    result = inject_tools_into_prompt(base, mock_registry, mock_agent)
    assert base in result
    assert "<functions>" in result


def test_deduplicate_tools():
    """Test that duplicate tools are deduplicated."""
    tool1 = MockTool("Same", "First.", None)
    tool2 = MockTool("Same", "Second.", None)
    registry = MockRegistry([tool1, tool2])
    agent = BaseAgent(
        agent_role=AgentType.CODER,
        system_prompt="Test",
        tools=[ToolScope.FILESYSTEM],
    )
    injector = ToolPromptInjector(registry)
    tools = injector._get_tools_for_agent(agent)
    names = [t.name for t in tools]
    assert names.count("Same") == 1