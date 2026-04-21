"""Tests for PromptAssembler and prompt layers."""

from __future__ import annotations

import pytest

from mindflow_backend.agents.prompts.assembler import AssemblyContext, PromptAssembler


class MockLayer:
    """Mock layer for testing."""

    def __init__(self, name: str, priority: int, content: str | None = None) -> None:
        self.name = name
        self.priority = priority
        self._content = content

    async def render(self, context: AssemblyContext) -> str | None:
        return self._content


@pytest.mark.asyncio
async def test_assembler_empty():
    """Test assembler with no layers."""
    assembler = PromptAssembler()
    result = await assembler.assemble()
    assert result == ""


@pytest.mark.asyncio
async def test_assembler_single_layer():
    """Test assembler with a single layer."""
    assembler = PromptAssembler()
    assembler.add_layer(MockLayer("test", 100, "Hello World"))
    result = await assembler.assemble()
    assert result == "Hello World"


@pytest.mark.asyncio
async def test_assembler_multiple_layers():
    """Test assembler with multiple layers."""
    assembler = PromptAssembler()
    assembler.add_layer(MockLayer("low", 10, "Low Priority"))
    assembler.add_layer(MockLayer("high", 100, "High Priority"))
    assembler.add_layer(MockLayer("medium", 50, "Medium Priority"))
    result = await assembler.assemble()
    # Higher priority should come first
    assert result == "High Priority\n\nMedium Priority\n\nLow Priority"


@pytest.mark.asyncio
async def test_assembler_none_content():
    """Test assembler skips layers that return None."""
    assembler = PromptAssembler()
    assembler.add_layer(MockLayer("none", 100, None))
    assembler.add_layer(MockLayer("content", 50, "Content"))
    result = await assembler.assemble()
    assert result == "Content"


@pytest.mark.asyncio
async def test_assembler_context():
    """Test assembler passes context to layers."""
    class ContextLayer:
        name = "context"
        priority = 100

        async def render(self, context: AssemblyContext) -> str:
            return f"Dir: {context.working_directory}"

    assembler = PromptAssembler()
    assembler.add_layer(ContextLayer())
    ctx = AssemblyContext(working_directory="/test/path")
    result = await assembler.assemble(ctx)
    assert result == "Dir: /test/path"


@pytest.mark.asyncio
async def test_assembler_exception_handling():
    """Test assembler handles exceptions gracefully."""
    class FailingLayer:
        name = "failing"
        priority = 100

        async def render(self, context: AssemblyContext) -> str:
            raise ValueError("Test error")

    assembler = PromptAssembler()
    assembler.add_layer(FailingLayer())
    assembler.add_layer(MockLayer("working", 50, "Working"))
    result = await assembler.assemble()
    # Should not fail, just skip the failing layer
    assert result == "Working"


def test_assembler_sync():
    """Test synchronous assembly."""
    assembler = PromptAssembler()
    assembler.add_layer(MockLayer("test", 100, "Sync Test"))
    result = assembler.assemble_sync()
    assert result == "Sync Test"


@pytest.mark.asyncio
async def test_base_prompt_layer():
    """Test BasePromptLayer."""
    from mindflow_backend.agents.prompts.layers.base import BasePromptLayer
    from mindflow_backend.agents.prompts.base import MINDFLOW_PREAMBLE, PERSISTENCE_DIRECTIVE

    layer = BasePromptLayer()
    result = await layer.render(AssemblyContext())
    assert MINDFLOW_PREAMBLE in result
    assert PERSISTENCE_DIRECTIVE in result

    layer_with_personality = BasePromptLayer("Custom personality")
    result = await layer_with_personality.render(AssemblyContext())
    assert "Custom personality" in result


@pytest.mark.asyncio
async def test_environment_layer():
    """Test EnvironmentLayer."""
    from mindflow_backend.agents.prompts.layers.environment import EnvironmentLayer

    layer = EnvironmentLayer()
    result = await layer.render(AssemblyContext())
    assert "## Environment Details" in result
    assert "Current Date:" in result
    assert "Operating System:" in result
    assert "Working Directory:" in result


@pytest.mark.asyncio
async def test_memory_layer():
    """Test MemoryFileLayer."""
    from mindflow_backend.agents.prompts.layers.memory import MemoryFileLayer

    layer = MemoryFileLayer()
    # Should return None if no memory files exist
    result = await layer.render(AssemblyContext())
    # Result can be None or contain content if CLAUDE.md exists
    assert result is None or "## Project Memory" in result


@pytest.mark.asyncio
async def test_git_layer():
    """Test GitContextLayer."""
    from mindflow_backend.agents.prompts.layers.git import GitContextLayer

    layer = GitContextLayer()
    # Without working directory, should return None
    result = await layer.render(AssemblyContext())
    assert result is None


@pytest.mark.asyncio
async def test_tool_layer():
    """Test ToolDescriptionLayer."""
    from mindflow_backend.agents.prompts.layers.tools import ToolDescriptionLayer

    layer = ToolDescriptionLayer()
    # Without agent, should return None
    result = await layer.render(AssemblyContext())
    assert result is None


@pytest.mark.asyncio
async def test_build_assembled_prompt():
    """Test build_assembled_prompt function."""
    from mindflow_backend.agents.prompts.base import build_assembled_prompt

    result = await build_assembled_prompt(
        personality_prompt="Test personality",
        include_tools=False,
        include_environment=True,
        include_git=False,
        include_memory=False,
    )
    assert "Test personality" in result
    assert "## Environment Details" in result