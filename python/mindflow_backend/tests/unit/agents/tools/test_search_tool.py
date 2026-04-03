"""Testes para o módulo Tool Search Tool."""

import pytest

from mindflow_backend.agents.tools.deferred_loader import (
    DeferredTool,
    DeferredToolLoader,
)
from mindflow_backend.agents.tools.search_tool import (
    create_search_tool,
    create_tool_info_tool,
)
from mindflow_backend.schemas.tools.builder import ToolContext, build_tool
from mindflow_backend.schemas.tools.result import ToolResult


@pytest.fixture
def loader():
    """Fixture para DeferredToolLoader com ferramentas."""
    loader = DeferredToolLoader()

    async def factory(name: str):
        async def my_callable(input: dict, context: ToolContext) -> ToolResult:
            return ToolResult(content=f"ok from {name}")

        return build_tool(
            name=name,
            description=f"Description for {name}",
            callable=my_callable,
        )

    tools = [
        DeferredTool(
            name="ReadFile",
            description="Reads a file from disk",
            loader=lambda: factory("ReadFile"),
            tags=["file", "read"],
            priority=10,
        ),
        DeferredTool(
            name="WriteFile",
            description="Writes a file to disk",
            loader=lambda: factory("WriteFile"),
            tags=["file", "write"],
            priority=5,
        ),
        DeferredTool(
            name="SearchCode",
            description="Searches code patterns",
            loader=lambda: factory("SearchCode"),
            tags=["search", "code"],
            priority=8,
        ),
    ]
    loader.register_many(tools)
    return loader


@pytest.fixture
def search_tool(loader):
    """Fixture para ferramenta de busca."""
    return create_search_tool(loader)


@pytest.fixture
def info_tool(loader):
    """Fixture para ferramenta de informações."""
    return create_tool_info_tool(loader)


@pytest.fixture
def context():
    """Fixture para contexto de execução."""
    return ToolContext(session_id="test-session")


class TestCreateSearchTool:
    """Testes para create_search_tool."""

    def test_search_tool_creation(self, search_tool):
        """Testa criação da ferramenta de busca."""
        assert search_tool.name == "ToolSearch"
        assert search_tool.is_concurrency_safe is True
        assert search_tool.is_read_only is False

    @pytest.mark.asyncio
    async def test_search_empty_query(self, search_tool, context):
        """Testa busca com query vazia."""
        result = await search_tool.callable({"query": ""}, context)
        assert result.is_error is True
        assert "Query vazia" in result.content

    @pytest.mark.asyncio
    async def test_search_select(self, search_tool, context):
        """Testa busca por select."""
        result = await search_tool.callable(
            {"query": "select:ReadFile,WriteFile"},
            context,
        )
        assert result.is_error is False
        assert "ReadFile" in result.content
        assert "WriteFile" in result.content
        assert "2 ferramenta(s)" in result.content

    @pytest.mark.asyncio
    async def test_search_keyword(self, search_tool, context):
        """Testa busca por keyword."""
        result = await search_tool.callable({"query": "file"}, context)
        assert result.is_error is False
        assert "ReadFile" in result.content
        assert "WriteFile" in result.content

    @pytest.mark.asyncio
    async def test_search_tag(self, search_tool, context):
        """Testa busca por tag."""
        result = await search_tool.callable({"query": "+file"}, context)
        assert result.is_error is False
        assert "ReadFile" in result.content
        assert "WriteFile" in result.content

    @pytest.mark.asyncio
    async def test_search_no_results(self, search_tool, context):
        """Testa busca sem resultados."""
        result = await search_tool.callable(
            {"query": "nonexistent tool"},
            context,
        )
        assert result.is_error is False
        assert "Nenhuma ferramenta encontrada" in result.content
        assert "Ferramentas disponíveis" in result.content

    @pytest.mark.asyncio
    async def test_search_max_results(self, search_tool, context):
        """Testa busca com limite de resultados."""
        result = await search_tool.callable(
            {"query": "file", "max_results": 1},
            context,
        )
        assert result.is_error is False
        # Deve retornar apenas 1 ferramenta
        assert "1 ferramenta(s)" in result.content

    @pytest.mark.asyncio
    async def test_search_metadata(self, search_tool, context):
        """Testa metadata do resultado."""
        result = await search_tool.callable(
            {"query": "select:ReadFile"},
            context,
        )
        assert result.is_error is False
        assert "loaded_tools" in result.metadata
        assert "ReadFile" in result.metadata["loaded_tools"]


class TestCreateToolInfoTool:
    """Testes para create_tool_info_tool."""

    def test_tool_info_creation(self, info_tool):
        """Testa criação da ferramenta de info."""
        assert info_tool.name == "ToolInfo"
        assert info_tool.is_concurrency_safe is True
        assert info_tool.is_read_only is True

    @pytest.mark.asyncio
    async def test_tool_info_all(self, info_tool, context):
        """Testa informações de todas as ferramentas."""
        result = await info_tool.callable({}, context)
        assert result.is_error is False
        assert "Status das Ferramentas" in result.content
        assert "Total Deferred" in result.content

    @pytest.mark.asyncio
    async def test_tool_info_specific_deferred(self, info_tool, context):
        """Testa informações de ferramenta deferred específica."""
        result = await info_tool.callable({"tool_name": "ReadFile"}, context)
        assert result.is_error is False
        assert "ReadFile" in result.content
        assert "(deferred)" in result.content

    @pytest.mark.asyncio
    async def test_tool_info_not_found(self, info_tool, context):
        """Testa informações de ferramenta não encontrada."""
        result = await info_tool.callable(
            {"tool_name": "NonExistent"},
            context,
        )
        assert result.is_error is True
        assert "não encontrada" in result.content


class TestSearchToolEdgeCases:
    """Testes para casos extremos do search tool."""

    @pytest.mark.asyncio
    async def test_search_with_special_characters(self, search_tool, context):
        """Testa busca com caracteres especiais."""
        result = await search_tool.callable(
            {"query": "file+read"},
            context,
        )
        # Não deve levantar exceção
        assert result is not None

    @pytest.mark.asyncio
    async def test_search_select_partial_match(self, search_tool, context):
        """Testa select com match parcial."""
        result = await search_tool.callable(
            {"query": "select:ReadFile,NonExistent"},
            context,
        )
        assert result.is_error is False
        assert "ReadFile" in result.content
        # NonExistent não deve estar no resultado
        assert "1 ferramenta(s)" in result.content

    @pytest.mark.asyncio
    async def test_search_default_max_results(self, search_tool, context):
        """Testa max_results default."""
        result = await search_tool.callable({"query": "file"}, context)
        assert result.is_error is False
        # Default é 5, mas temos apenas 2 com "file"
        assert "2 ferramenta(s)" in result.content