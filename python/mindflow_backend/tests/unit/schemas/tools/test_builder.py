"""Testes para o módulo build_tool() pattern."""

import pytest

from mindflow_backend.schemas.tools.builder import (
    InterruptBehavior,
    ToolBuilder,
    ToolContext,
    build_tool,
)
from mindflow_backend.schemas.tools.result import ToolResult


@pytest.fixture
def simple_tool_input():
    """Input simples para testes."""
    return {"message": "test"}


@pytest.fixture
def simple_context():
    """Contexto simples para testes."""
    return ToolContext(session_id="test-session")


class TestBuildTool:
    """Testes para a função build_tool()."""

    def test_build_tool_basic(self):
        """Testa criação básica de ferramenta."""

        async def my_callable(input: dict, context: ToolContext) -> ToolResult:
            return ToolResult(content="ok")

        tool = build_tool(
            name="TestTool",
            description="Test tool",
            callable=my_callable,
        )

        assert tool.name == "TestTool"
        assert tool.description == "Test tool"
        assert tool.is_concurrency_safe is True
        assert tool.is_read_only is False
        assert tool.interrupt_behavior == InterruptBehavior.BLOCK
        assert tool.max_result_size_chars == 100_000
        assert tool.timeout_seconds == 30.0

    def test_build_tool_with_custom_defaults(self):
        """Testa criação com defaults customizados."""

        async def my_callable(input: dict, context: ToolContext) -> ToolResult:
            return ToolResult(content="ok")

        tool = build_tool(
            name="CustomTool",
            description="Custom tool",
            callable=my_callable,
            is_concurrency_safe=False,
            is_read_only=True,
            interrupt_behavior=InterruptBehavior.CANCEL,
            max_result_size_chars=50_000,
            timeout_seconds=60.0,
        )

        assert tool.name == "CustomTool"
        assert tool.is_concurrency_safe is False
        assert tool.is_read_only is True
        assert tool.interrupt_behavior == InterruptBehavior.CANCEL
        assert tool.max_result_size_chars == 50_000
        assert tool.timeout_seconds == 60.0

    @pytest.mark.asyncio
    async def test_build_tool_get_description_static(self):
        """Testa get_description com descrição estática."""

        async def my_callable(input: dict, context: ToolContext) -> ToolResult:
            return ToolResult(content="ok")

        tool = build_tool(
            name="TestTool",
            description="Static description",
            callable=my_callable,
        )

        desc = await tool.get_description()
        assert desc == "Static description"

    @pytest.mark.asyncio
    async def test_build_tool_get_description_dynamic(self):
        """Testa get_description com descrição dinâmica."""

        async def my_callable(input: dict, context: ToolContext) -> ToolResult:
            return ToolResult(content="ok")

        async def dynamic_description() -> str:
            return "Dynamic description"

        tool = build_tool(
            name="TestTool",
            description=dynamic_description,
            callable=my_callable,
        )

        desc = await tool.get_description()
        assert desc == "Dynamic description"


class TestToolBuilder:
    """Testes para a classe ToolBuilder."""

    def test_builder_basic(self):
        """Testa builder básico."""

        async def my_callable(input: dict, context: ToolContext) -> ToolResult:
            return ToolResult(content="ok")

        tool = (
            ToolBuilder("TestTool")
            .with_description("Test description")
            .with_callable(my_callable)
            .build()
        )

        assert tool.name == "TestTool"
        assert tool.description == "Test description"

    def test_builder_fluent(self):
        """Testa builder fluente com múltiplas configurações."""

        async def my_callable(input: dict, context: ToolContext) -> ToolResult:
            return ToolResult(content="ok")

        tool = (
            ToolBuilder("FluentTool")
            .with_description("Fluent description")
            .with_callable(my_callable)
            .concurrency_safe(False)
            .read_only(True)
            .with_interrupt_behavior(InterruptBehavior.CANCEL)
            .with_max_result_size(75_000)
            .with_timeout(45.0)
            .build()
        )

        assert tool.name == "FluentTool"
        assert tool.is_concurrency_safe is False
        assert tool.is_read_only is True
        assert tool.interrupt_behavior == InterruptBehavior.CANCEL
        assert tool.max_result_size_chars == 75_000
        assert tool.timeout_seconds == 45.0

    def test_builder_without_callable_raises(self):
        """Testa que builder sem callable levanta erro."""
        builder = ToolBuilder("NoCallable").with_description("No callable")

        with pytest.raises(ValueError, match="requires a callable"):
            builder.build()

    def test_builder_chaining(self):
        """Testa encadeamento de métodos do builder."""

        async def my_callable(input: dict, context: ToolContext) -> ToolResult:
            return ToolResult(content="ok")

        builder = ToolBuilder("ChainTool")
        assert builder.with_description("desc") is builder
        assert builder.with_callable(my_callable) is builder
        assert builder.concurrency_safe(False) is builder
        assert builder.read_only(True) is builder


class TestInterruptBehavior:
    """Testes para InterruptBehavior enum."""

    def test_cancel_value(self):
        """Testa valor CANCEL."""
        assert InterruptBehavior.CANCEL.value == "cancel"

    def test_block_value(self):
        """Testa valor BLOCK."""
        assert InterruptBehavior.BLOCK.value == "block"

    def test_enum_members(self):
        """Testa membros do enum."""
        assert len(InterruptBehavior) == 2
        assert InterruptBehavior.CANCEL in InterruptBehavior
        assert InterruptBehavior.BLOCK in InterruptBehavior


class TestToolContext:
    """Testes para ToolContext."""

    def test_context_basic(self):
        """Testa criação básica de contexto."""
        ctx = ToolContext(session_id="test-123")
        assert ctx.session_id == "test-123"
        assert ctx.cwd is None
        assert ctx.abort_signal is None
        assert ctx.metadata == {}

    def test_context_with_metadata(self):
        """Testa contexto com metadata."""
        ctx = ToolContext(
            session_id="test-123",
            cwd="/home/user",
            metadata={"key": "value"},
        )
        assert ctx.session_id == "test-123"
        assert ctx.cwd == "/home/user"
        assert ctx.metadata == {"key": "value"}

    def test_context_default_metadata(self):
        """Testa que metadata default é dict vazio."""
        ctx = ToolContext(session_id="test")
        ctx.metadata["new_key"] = "new_value"
        assert ctx.metadata == {"new_key": "new_value"}