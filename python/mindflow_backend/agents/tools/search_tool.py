"""Tool Search Tool - Busca e carrega ferramentas deferred sob demanda.

Inspirado no ToolSearchTool do Claude Code.
Permite ao modelo descobrir e carregar ferramentas que não estão no prompt inicial.
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.agents.tools.deferred_loader import DeferredToolLoader
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools.builder import InterruptBehavior, ToolContext, build_tool
from mindflow_backend.schemas.tools.result import ToolResult

_logger = get_logger(__name__)


def create_search_tool(loader: DeferredToolLoader) -> Any:
    """Cria ferramenta de busca de ferramentas deferred.

    Args:
        loader: DeferredToolLoader com ferramentas registradas

    Returns:
        BuiltTool configurada para busca
    """

    async def search_deferred_tools(
        tool_input: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        """Busca e carrega ferramentas deferred.

        Args:
            tool_input: Dict com 'query' e opcionalmente 'max_results'
            context: Contexto de execução

        Returns:
            ToolResult com ferramentas encontradas ou erro
        """
        query = tool_input.get("query", "")
        max_results = tool_input.get("max_results", 5)

        if not query:
            return ToolResult(
                content="❌ Query vazia. Use 'select:ToolA,ToolB' ou 'keyword search'.",
                is_error=True,
            )

        _logger.info(
            "tool_search_started",
            query=query,
            max_results=max_results,
        )

        # Busca ferramentas deferred
        results = loader.search(query, max_results=max_results)

        if not results:
            # Retorna resumo de todas as ferramentas disponíveis
            summary = loader.get_deferred_summary()
            available = "\n".join(
                f"  - {t['name']}: {t['description']}"
                for t in summary
            )
            return ToolResult(
                content=(
                    f"❓ Nenhuma ferramenta encontrada para '{query}'.\n\n"
                    f"Ferramentas disponíveis:\n{available}"
                ),
                is_error=False,
            )

        # Carrega ferramentas encontradas
        loaded_tools = []
        for deferred in results:
            tool = await loader.load_tool(deferred.name)
            if tool:
                loaded_tools.append(tool)

        if not loaded_tools:
            return ToolResult(
                content=f"❌ Erro ao carregar ferramentas para '{query}'.",
                is_error=True,
            )

        # Formata resultado
        tool_descriptions = []
        for tool in loaded_tools:
            desc = await tool.get_description() if hasattr(tool, "get_description") else tool.description
            tool_descriptions.append(
                f"<function>"
                f'{{"name": "{tool.name}", "description": "{desc}"}}'
                f"</function>"
            )

        result_content = (
            f"<functions>\n"
            + "\n".join(tool_descriptions)
            + "\n</functions>\n\n"
            f"✅ {len(loaded_tools)} ferramenta(s) carregada(s) e disponível(is) para uso."
        )

        _logger.info(
            "tool_search_completed",
            query=query,
            found=len(results),
            loaded=len(loaded_tools),
        )

        return ToolResult(
            content=result_content,
            is_error=False,
            metadata={
                "loaded_tools": [t.name for t in loaded_tools],
                "total_deferred": loader.get_deferred_count(),
                "total_loaded": loader.get_loaded_count(),
            },
        )

    return build_tool(
        name="ToolSearch",
        description=(
            "Busca e carrega ferramentas adicionais sob demanda. "
            "Use quando precisar de funcionalidade não disponível nas ferramentas ativas. "
            "Formatos de query:\n"
            "- 'select:ToolA,ToolB' - Carrega ferramentas específicas por nome\n"
            "- 'keyword search' - Busca por palavras-chave\n"
            "- '+tag' - Busca por tag obrigatória"
        ),
        callable=search_deferred_tools,
        is_concurrency_safe=True,
        is_read_only=False,
        interrupt_behavior=InterruptBehavior.CANCEL,
    )


def create_tool_info_tool(loader: DeferredToolLoader) -> Any:
    """Cria ferramenta de informações sobre ferramentas disponíveis.

    Args:
        loader: DeferredToolLoader com ferramentas registradas

    Returns:
        BuiltTool configurada para informações
    """

    async def get_tool_info(
        tool_input: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        """Retorna informações sobre ferramentas disponíveis.

        Args:
            tool_input: Dict com 'tool_name' opcional
            context: Contexto de execução

        Returns:
            ToolResult com informações das ferramentas
        """
        tool_name = tool_input.get("tool_name")

        if tool_name:
            # Info de uma ferramenta específica
            if tool_name in loader._loaded:
                tool = loader._loaded[tool_name]
                desc = await tool.get_description() if hasattr(tool, "get_description") else tool.description
                return ToolResult(
                    content=(
                        f"📋 **{tool.name}**\n\n"
                        f"Descrição: {desc}\n"
                        f"Concurrency Safe: {tool.is_concurrency_safe}\n"
                        f"Read Only: {tool.is_read_only}\n"
                        f"Timeout: {tool.timeout_seconds}s"
                    ),
                    is_error=False,
                )
            elif tool_name in loader._deferred:
                deferred = loader._deferred[tool_name]
                return ToolResult(
                    content=(
                        f"📋 **{deferred.name}** (deferred)\n\n"
                        f"Descrição: {deferred.description}\n"
                        f"Tags: {', '.join(deferred.tags)}\n"
                        f"Prioridade: {deferred.priority}\n"
                        f"Status: {'Carregada' if deferred.is_loaded else 'Não carregada'}"
                    ),
                    is_error=False,
                )
            else:
                return ToolResult(
                    content=f"❓ Ferramenta '{tool_name}' não encontrada.",
                    is_error=True,
                )

        # Resumo de todas as ferramentas
        stats = loader.get_stats()
        summary = loader.get_deferred_summary()

        content = (
            f"📊 **Status das Ferramentas**\n\n"
            f"Total Deferred: {stats['total_deferred']}\n"
            f"Total Loaded: {stats['total_loaded']}\n\n"
            f"**Ferramentas Carregadas:**\n"
        )

        for name in stats["loaded_names"]:
            content += f"  ✅ {name}\n"

        content += f"\n**Ferramentas Disponíveis (deferred):**\n"
        for tool_info in summary:
            status = "✅" if tool_info["loaded"] else "⏳"
            content += f"  {status} {tool_info['name']}: {tool_info['description']}\n"

        return ToolResult(
            content=content,
            is_error=False,
            metadata=stats,
        )

    return build_tool(
        name="ToolInfo",
        description="Retorna informações sobre ferramentas disponíveis (carregadas e deferred).",
        callable=get_tool_info,
        is_concurrency_safe=True,
        is_read_only=True,
        interrupt_behavior=InterruptBehavior.CANCEL,
    )