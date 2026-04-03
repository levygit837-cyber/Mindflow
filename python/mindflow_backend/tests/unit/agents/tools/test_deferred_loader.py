"""Testes para o módulo DeferredToolLoader."""

import asyncio
import pytest
from unittest.mock import patch, MagicMock
import importlib
import sys

# Mock do redis antes de importar
redis_mock = MagicMock()
redis_mock.exceptions = MagicMock()
redis_mock.asyncio = MagicMock()
sys.modules['redis'] = redis_mock
sys.modules['redis.exceptions'] = redis_mock.exceptions
sys.modules['redis.asyncio'] = redis_mock.asyncio

from mindflow_backend.schemas.tools.builder import ToolContext, build_tool
from mindflow_backend.schemas.tools.result import ToolResult

# Importa diretamente o módulo
deferred_loader_module = importlib.import_module('mindflow_backend.agents.tools.deferred_loader')
DeferredTool = deferred_loader_module.DeferredTool
DeferredToolLoader = deferred_loader_module.DeferredToolLoader


@pytest.fixture
def loader():
    """Fixture para DeferredToolLoader."""
    return DeferredToolLoader()


@pytest.fixture
def sample_tool_factory():
    """Fixture para factory de ferramenta de exemplo."""

    async def factory():
        async def my_callable(input: dict, context: ToolContext) -> ToolResult:
            return ToolResult(content="ok")

        return build_tool(
            name="SampleTool",
            description="Sample tool for testing",
            callable=my_callable,
        )

    return factory


@pytest.fixture
def sample_deferred_tool(sample_tool_factory):
    """Fixture para DeferredTool de exemplo."""
    return DeferredTool(
        name="SampleTool",
        description="Sample tool for testing",
        loader=sample_tool_factory,
        tags=["test", "sample"],
        priority=10,
    )


class TestDeferredTool:
    """Testes para DeferredTool dataclass."""

    def test_deferred_tool_basic(self, sample_tool_factory):
        """Testa criação básica de DeferredTool."""
        tool = DeferredTool(
            name="TestTool",
            description="Test description",
            loader=sample_tool_factory,
        )
        assert tool.name == "TestTool"
        assert tool.description == "Test description"
        assert tool.schema is None
        assert tool.tags == []
        assert tool.priority == 0

    def test_deferred_tool_with_tags(self, sample_tool_factory):
        """Testa DeferredTool com tags."""
        tool = DeferredTool(
            name="TestTool",
            description="Test description",
            loader=sample_tool_factory,
            tags=["tag1", "tag2"],
            priority=5,
        )
        assert tool.tags == ["tag1", "tag2"]
        assert tool.priority == 5

    def test_is_loaded_false(self, sample_deferred_tool):
        """Testa que is_loaded é False inicialmente."""
        assert sample_deferred_tool.is_loaded is False

    def test_is_loaded_true(self, sample_deferred_tool):
        """Testa que is_loaded é True após definir schema."""
        sample_deferred_tool.schema = {"type": "object"}
        assert sample_deferred_tool.is_loaded is True


class TestDeferredToolLoader:
    """Testes para DeferredToolLoader."""

    def test_register_deferred(self, loader, sample_deferred_tool):
        """Testa registro de ferramenta deferred."""
        loader.register_deferred(sample_deferred_tool)
        assert "SampleTool" in loader._deferred
        assert loader.get_deferred_count() == 1

    def test_register_duplicate_logs_warning(self, loader, sample_deferred_tool):
        """Testa que registro duplicado loga warning."""
        loader.register_deferred(sample_deferred_tool)
        loader.register_deferred(sample_deferred_tool)  # Duplicate
        # Não deve levantar exceção, apenas logar warning
        assert loader.get_deferred_count() == 1

    def test_register_many(self, loader, sample_tool_factory):
        """Testa registro de múltiplas ferramentas."""
        tools = [
            DeferredTool(name=f"Tool{i}", description=f"Tool {i}", loader=sample_tool_factory)
            for i in range(3)
        ]
        loader.register_many(tools)
        assert loader.get_deferred_count() == 3

    @pytest.mark.asyncio
    async def test_load_tool(self, loader, sample_deferred_tool):
        """Testa carregamento de ferramenta."""
        loader.register_deferred(sample_deferred_tool)
        tool = await loader.load_tool("SampleTool")

        assert tool is not None
        assert tool.name == "SampleTool"
        assert loader.get_loaded_count() == 1

    @pytest.mark.asyncio
    async def test_load_tool_already_loaded(self, loader, sample_deferred_tool):
        """Testa que ferramenta já carregada é retornada do cache."""
        loader.register_deferred(sample_deferred_tool)
        tool1 = await loader.load_tool("SampleTool")
        tool2 = await loader.load_tool("SampleTool")

        assert tool1 is tool2
        assert loader.get_loaded_count() == 1

    @pytest.mark.asyncio
    async def test_load_tool_not_found(self, loader):
        """Testa carregamento de ferramenta não encontrada."""
        tool = await loader.load_tool("NonExistent")
        assert tool is None

    @pytest.mark.asyncio
    async def test_load_tool_error(self, loader):
        """Testa carregamento com erro na factory."""

        async def failing_factory():
            raise RuntimeError("Factory failed")

        deferred = DeferredTool(
            name="FailingTool",
            description="Tool that fails",
            loader=failing_factory,
        )
        loader.register_deferred(deferred)
        tool = await loader.load_tool("FailingTool")

        assert tool is None
        assert loader.get_loaded_count() == 0

    @pytest.mark.asyncio
    async def test_load_many(self, loader, sample_tool_factory):
        """Testa carregamento de múltiplas ferramentas."""
        for i in range(3):
            loader.register_deferred(
                DeferredTool(
                    name=f"Tool{i}",
                    description=f"Tool {i}",
                    loader=sample_tool_factory,
                )
            )

        tools = await loader.load_many(["Tool0", "Tool1", "Tool2"])
        assert len(tools) == 3
        assert loader.get_loaded_count() == 3

    @pytest.mark.asyncio
    async def test_load_many_partial_failure(self, loader, sample_tool_factory):
        """Testa carregamento parcial com falhas."""

        async def failing_factory():
            raise RuntimeError("Fail")

        loader.register_deferred(
            DeferredTool(name="GoodTool", description="Good", loader=sample_tool_factory)
        )
        loader.register_deferred(
            DeferredTool(name="BadTool", description="Bad", loader=failing_factory)
        )

        tools = await loader.load_many(["GoodTool", "BadTool"])
        assert len(tools) == 1
        # A factory sample_tool_factory cria uma ferramenta chamada "SampleTool"
        assert tools[0].name == "SampleTool"


class TestDeferredToolLoaderSearch:
    """Testes para busca de ferramentas deferred."""

    @pytest.fixture
    def loader_with_tools(self, loader, sample_tool_factory):
        """Loader com ferramentas registradas."""
        tools = [
            DeferredTool(
                name="ReadFile",
                description="Reads a file from disk",
                loader=sample_tool_factory,
                tags=["file", "read"],
                priority=10,
            ),
            DeferredTool(
                name="WriteFile",
                description="Writes a file to disk",
                loader=sample_tool_factory,
                tags=["file", "write"],
                priority=5,
            ),
            DeferredTool(
                name="SearchCode",
                description="Searches code patterns",
                loader=sample_tool_factory,
                tags=["search", "code"],
                priority=8,
            ),
        ]
        loader.register_many(tools)
        return loader

    def test_search_select(self, loader_with_tools):
        """Testa busca por select."""
        results = loader_with_tools.search("select:ReadFile,WriteFile")
        assert len(results) == 2
        names = [r.name for r in results]
        assert "ReadFile" in names
        assert "WriteFile" in names

    def test_search_select_not_found(self, loader_with_tools):
        """Testa busca por select com ferramenta não encontrada."""
        results = loader_with_tools.search("select:NonExistent")
        assert len(results) == 0

    def test_search_keyword(self, loader_with_tools):
        """Testa busca por keyword."""
        results = loader_with_tools.search("file")
        assert len(results) == 2
        names = [r.name for r in results]
        assert "ReadFile" in names
        assert "WriteFile" in names

    def test_search_tag(self, loader_with_tools):
        """Testa busca por tag."""
        results = loader_with_tools.search("+file")
        assert len(results) == 2
        names = [r.name for r in results]
        assert "ReadFile" in names
        assert "WriteFile" in names

    def test_search_tag_with_keyword(self, loader_with_tools):
        """Testa busca por tag com keyword."""
        results = loader_with_tools.search("+file read")
        assert len(results) == 1
        assert results[0].name == "ReadFile"

    def test_search_no_results(self, loader_with_tools):
        """Testa busca sem resultados."""
        results = loader_with_tools.search("nonexistent keyword")
        assert len(results) == 0

    def test_search_max_results(self, loader_with_tools):
        """Testa limite de resultados."""
        results = loader_with_tools.search("file", max_results=1)
        assert len(results) == 1

    def test_search_sorted_by_priority(self, loader_with_tools):
        """Testa que resultados são ordenados por prioridade."""
        results = loader_with_tools.search("file")
        assert results[0].priority >= results[1].priority


class TestDeferredToolLoaderStats:
    """Testes para estatísticas do loader."""

    def test_get_deferred_summary(self, loader, sample_tool_factory):
        """Testa resumo de ferramentas deferred."""
        loader.register_deferred(
            DeferredTool(
                name="Tool1",
                description="Tool 1",
                loader=sample_tool_factory,
            )
        )
        summary = loader.get_deferred_summary()

        assert len(summary) == 1
        assert summary[0]["name"] == "Tool1"
        assert summary[0]["description"] == "Tool 1"
        assert summary[0]["loaded"] is False

    @pytest.mark.asyncio
    async def test_get_deferred_summary_loaded(self, loader, sample_deferred_tool):
        """Testa resumo após carregamento."""
        loader.register_deferred(sample_deferred_tool)
        await loader.load_tool("SampleTool")
        summary = loader.get_deferred_summary()

        assert len(summary) == 1
        assert summary[0]["loaded"] is True

    def test_get_stats(self, loader, sample_tool_factory):
        """Testa estatísticas do loader."""
        loader.register_deferred(
            DeferredTool(
                name="Tool1",
                description="Tool 1",
                loader=sample_tool_factory,
            )
        )
        stats = loader.get_stats()

        assert stats["total_deferred"] == 1
        assert stats["total_loaded"] == 0
        assert "Tool1" in stats["deferred_names"]