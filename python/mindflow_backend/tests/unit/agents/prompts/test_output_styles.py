"""Tests for Output Styles system."""

from __future__ import annotations

import pytest

from mindflow_backend.agents.prompts.assembler import AssemblyContext, PromptAssembler
from mindflow_backend.agents.prompts.layers.output_style import OutputStyleLayer
from mindflow_backend.agents.prompts.styles.manager import OutputStyleManager
from mindflow_backend.schemas.prompts.output_style import (
    DEFAULT_OUTPUT_STYLE_NAME,
    OutputStyleConfig,
    OutputStyleSource,
    OutputStyles,
)


@pytest.mark.asyncio
async def test_load_builtin_styles():
    """Test loading built-in output styles."""
    manager = OutputStyleManager()
    styles = await manager.load_all_styles()

    # Should have all built-in styles
    assert "default" in styles
    assert "explanatory" in styles
    assert "learning" in styles
    assert "concise" in styles

    # Verify built-in source
    for style in styles.values():
        assert style.source == OutputStyleSource.BUILT_IN


@pytest.mark.asyncio
async def test_get_default_style():
    """Test getting the default style."""
    manager = OutputStyleManager()
    style = await manager.get_style_config()

    assert style is not None
    assert style.name == "default"
    assert style.source == OutputStyleSource.BUILT_IN


@pytest.mark.asyncio
async def test_get_specific_style():
    """Test getting a specific style by name."""
    manager = OutputStyleManager()

    # Get explanatory style
    style = await manager.get_style_config("explanatory")
    assert style is not None
    assert style.name == "explanatory"
    assert "step-by-step" in style.prompt.lower()

    # Get learning style
    style = await manager.get_style_config("learning")
    assert style is not None
    assert style.name == "learning"
    assert "teacher" in style.prompt.lower()

    # Get concise style
    style = await manager.get_style_config("concise")
    assert style is not None
    assert style.name == "concise"
    assert "concise" in style.prompt.lower()


@pytest.mark.asyncio
async def test_get_nonexistent_style():
    """Test getting a style that doesn't exist."""
    manager = OutputStyleManager()
    style = await manager.get_style_config("nonexistent_style")

    # Should return None for nonexistent styles
    assert style is None


@pytest.mark.asyncio
async def test_get_style_prompt():
    """Test getting formatted style prompt."""
    manager = OutputStyleManager()
    prompt = await manager.get_style_prompt("explanatory")

    assert prompt is not None
    assert "# Output Style: explanatory" in prompt
    assert "step-by-step" in prompt.lower()


@pytest.mark.asyncio
async def test_output_style_layer():
    """Test OutputStyleLayer rendering."""
    manager = OutputStyleManager()
    layer = OutputStyleLayer(manager, style_name="explanatory")

    context = AssemblyContext()
    result = await layer.render(context)

    assert result is not None
    assert "# Output Style: explanatory" in result


@pytest.mark.asyncio
async def test_output_style_layer_from_context():
    """Test OutputStyleLayer with style from context."""
    manager = OutputStyleManager()
    layer = OutputStyleLayer(manager)

    context = AssemblyContext()
    context.extra["output_style"] = "learning"

    result = await layer.render(context)

    assert result is not None
    assert "# Output Style: learning" in result
    assert "teacher" in result.lower()


@pytest.mark.asyncio
async def test_output_style_layer_with_assembler():
    """Test OutputStyleLayer integrated with PromptAssembler."""
    assembler = PromptAssembler()
    assembler.add_layer(OutputStyleLayer())

    context = AssemblyContext()
    context.extra["output_style"] = "concise"

    result = await assembler.assemble(context)

    assert "# Output Style: concise" in result


@pytest.mark.asyncio
async def test_output_style_layer_priority():
    """Test that OutputStyleLayer has correct priority."""
    layer = OutputStyleLayer()

    assert layer.name == "output_style"
    assert layer.priority == 90


@pytest.mark.asyncio
async def test_output_style_layer_with_style():
    """Test creating a new layer with specific style."""
    manager = OutputStyleManager()
    original_layer = OutputStyleLayer(manager, style_name="default")

    # Create new layer with different style
    new_layer = original_layer.with_style("explanatory")

    assert new_layer._style_name == "explanatory"
    assert original_layer._style_name == "default"  # Original unchanged


@pytest.mark.asyncio
async def test_clear_cache():
    """Test clearing the styles cache."""
    manager = OutputStyleManager()

    # Load styles
    await manager.load_all_styles()
    assert manager._initialized is True

    # Clear cache
    manager.clear_cache()
    assert manager._initialized is False
    assert len(manager._cache) == 0


@pytest.mark.asyncio
async def test_style_config_model():
    """Test OutputStyleConfig model validation."""
    config = OutputStyleConfig(
        name="test_style",
        description="Test style for testing",
        prompt="This is a test prompt.",
        source=OutputStyleSource.BUILT_IN,
        keep_coding_instructions=True,
        force_for_plugin=False,
    )

    assert config.name == "test_style"
    assert config.description == "Test style for testing"
    assert config.prompt == "This is a test prompt."
    assert config.source == OutputStyleSource.BUILT_IN
    assert config.keep_coding_instructions is True
    assert config.force_for_plugin is False


@pytest.mark.asyncio
async def test_output_styles_enum():
    """Test OutputStyles enum values."""
    assert OutputStyles.DEFAULT.value == "default"
    assert OutputStyles.EXPLANATORY.value == "explanatory"
    assert OutputStyles.LEARNING.value == "learning"
    assert OutputStyles.CONCISE.value == "concise"


@pytest.mark.asyncio
async def test_default_constants():
    """Test default style constants."""
    from mindflow_backend.schemas.prompts.output_style import (
        DEFAULT_OUTPUT_STYLE_DESCRIPTION,
        DEFAULT_OUTPUT_STYLE_LABEL,
    )

    assert DEFAULT_OUTPUT_STYLE_NAME == "default"
    assert DEFAULT_OUTPUT_STYLE_LABEL == "Default"
    assert "efficiently" in DEFAULT_OUTPUT_STYLE_DESCRIPTION.lower()