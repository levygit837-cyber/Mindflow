"""Deferred Tool Loader - Carregamento lazy de ferramentas MCP.

Inspirado no ToolSearchTool do Claude Code.
Permite carregar ferramentas sob demanda para reduzir overhead de contexto.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Awaitable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools.builder import BuiltTool

_logger = get_logger(__name__)

T = TypeVar("T")


@dataclass
class DeferredTool:
    """Ferramenta que será carregada sob demanda.

    Attributes:
        name: Nome único da ferramenta
        description: Descrição breve (aparece no prompt)
        loader: Factory async para carregar a ferramenta completa
        schema: Schema de input (None se não carregado ainda)
        tags: Tags para busca
        priority: Prioridade de carregamento (maior = mais prioritário)
    """

    name: str
    description: str
    loader: Callable[[], Awaitable[BuiltTool]]
    schema: dict[str, Any] | None = None
    tags: list[str] = field(default_factory=list)
    priority: int = 0

    @property
    def is_loaded(self) -> bool:
        """Verifica se a ferramenta já foi carregada."""
        return self.schema is not None


class DeferredToolLoader:
    """Gerencia carregamento lazy de ferramentas.

    Carrega ferramentas sob demanda quando solicitadas pelo modelo,
    reduzindo o tamanho do system prompt inicial.

    Example:
        ```python
        loader = DeferredToolLoader()

        # Registra ferramenta para carregamento lazy
        loader.register_deferred(DeferredTool(
            name="ComplexAnalysis",
            description="Realiza análise complexa de código",
            loader=load_complex_analysis_tool,
            tags=["analysis", "code"],
        ))

        # Carrega quando solicitado
        tool = await loader.load_tool("ComplexAnalysis")
        ```
    """

    def __init__(self) -> None:
        self._deferred: dict[str, DeferredTool] = {}
        self._loaded: dict[str, BuiltTool] = {}
        self._load_lock = asyncio.Lock()

    def register_deferred(self, tool: DeferredTool) -> None:
        """Registra ferramenta para carregamento sob demanda.

        Args:
            tool: DeferredTool com configuração de carregamento
        """
        if tool.name in self._deferred:
            _logger.warning(
                "deferred_tool_already_registered",
                tool_name=tool.name,
            )
            return

        self._deferred[tool.name] = tool
        _logger.debug(
            "deferred_tool_registered",
            tool_name=tool.name,
            tags=tool.tags,
            priority=tool.priority,
        )

    def register_many(self, tools: list[DeferredTool]) -> None:
        """Registra múltiplas ferramentas de uma vez.

        Args:
            tools: Lista de DeferredTool
        """
        for tool in tools:
            self.register_deferred(tool)

    async def load_tool(self, name: str) -> BuiltTool | None:
        """Carrega ferramenta específica por nome.

        Args:
            name: Nome da ferramenta

        Returns:
            BuiltTool carregada ou None se não encontrada
        """
        # Já carregada?
        if name in self._loaded:
            return self._loaded[name]

        # Existe como deferred?
        if name not in self._deferred:
            _logger.warning(
                "deferred_tool_not_found",
                tool_name=name,
            )
            return None

        # Carrega com lock para evitar race conditions
        async with self._load_lock:
            # Verifica novamente após lock
            if name in self._loaded:
                return self._loaded[name]

            deferred = self._deferred[name]
            try:
                _logger.info("loading_deferred_tool", tool_name=name)
                tool = await deferred.loader()
                self._loaded[name] = tool

                # Atualiza schema no deferred para marcar como carregado
                deferred.schema = {"type": "object", "loaded": True}

                _logger.info(
                    "deferred_tool_loaded",
                    tool_name=name,
                )
                return tool

            except Exception as exc:
                _logger.error(
                    "deferred_tool_load_failed",
                    tool_name=name,
                    error=str(exc),
                )
                return None

    async def load_many(self, names: list[str]) -> list[BuiltTool]:
        """Carrega múltiplas ferramentas.

        Args:
            names: Lista de nomes de ferramentas

        Returns:
            Lista de BuiltTool carregadas
        """
        tasks = [self.load_tool(name) for name in names]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        tools: list[BuiltTool] = []
        for result in results:
            if isinstance(result, BuiltTool):
                tools.append(result)
            elif isinstance(result, Exception):
                _logger.error(
                    "deferred_tool_load_error",
                    error=str(result),
                )

        return tools

    def search(self, query: str, max_results: int = 5) -> list[DeferredTool]:
        """Busca ferramentas por query.

        Suporta:
        - "select:ToolA,ToolB" - Seleção direta por nome
        - "keyword search" - Busca por palavras-chave
        - "+tag" - Busca por tag obrigatória

        Args:
            query: Query de busca
            max_results: Máximo de resultados

        Returns:
            Lista de DeferredTool encontradas
        """
        # Select direto
        if query.startswith("select:"):
            names = query[7:].split(",")
            names = [n.strip() for n in names]
            return [
                self._deferred[n]
                for n in names
                if n in self._deferred
            ][:max_results]

        # Busca por tag obrigatória
        if query.startswith("+"):
            tag = query[1:].split()[0]
            remaining = query[len(tag) + 2:].strip()
            results = [
                tool
                for tool in self._deferred.values()
                if tag in tool.tags
            ]
            # Filtra por remaining se houver
            if remaining:
                results = [
                    tool
                    for tool in results
                    if remaining.lower() in tool.name.lower()
                    or remaining.lower() in tool.description.lower()
                ]
            return sorted(results, key=lambda t: -t.priority)[:max_results]

        # Busca por palavras-chave
        query_lower = query.lower()
        results = [
            tool
            for tool in self._deferred.values()
            if query_lower in tool.name.lower()
            or query_lower in tool.description.lower()
            or any(query_lower in tag.lower() for tag in tool.tags)
        ]
        return sorted(results, key=lambda t: -t.priority)[:max_results]

    def get_deferred_summary(self) -> list[dict[str, Any]]:
        """Retorna resumo das ferramentas deferred para o prompt.

        Returns:
            Lista de dicts com nome e descrição
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "loaded": tool.is_loaded,
            }
            for tool in sorted(
                self._deferred.values(),
                key=lambda t: -t.priority,
            )
        ]

    def get_loaded_count(self) -> int:
        """Retorna número de ferramentas carregadas."""
        return len(self._loaded)

    def get_deferred_count(self) -> int:
        """Retorna número de ferramentas deferred."""
        return len(self._deferred)

    def get_stats(self) -> dict[str, Any]:
        """Retorna estatísticas do loader."""
        return {
            "total_deferred": len(self._deferred),
            "total_loaded": len(self._loaded),
            "loaded_names": list(self._loaded.keys()),
            "deferred_names": list(self._deferred.keys()),
        }