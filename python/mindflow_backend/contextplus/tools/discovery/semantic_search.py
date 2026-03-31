# Semantic code search using embeddings with hybrid scoring
# FEATURE: Discovery - Semantic and keyword search over codebase files

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.contextplus.core.embeddings import (
    SearchDocument,
    fetch_embedding,
    hybrid_score,
    search_documents,
)
from mindflow_backend.contextplus.core.parser import analyze_file, flatten_symbols, is_supported_file
from mindflow_backend.contextplus.core.walker import walk_directory, WalkOptions
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools.base import (
    ParameterType,
    ToolParameter,
    ToolSchema,
)

_logger = get_logger(__name__)

SEMANTIC_SEARCH_SCHEMA = ToolSchema(
    name="semantic_search",
    description=(
        "Search the codebase by MEANING, not just exact variable names. Uses embeddings "
        "over file headers and symbol names. Example: searching 'user authentication' finds "
        "files about login, sessions, JWT even if those exact words aren't used."
    ),
    category="discovery",
    parameters=[
        ToolParameter(
            name="query",
            type=ParameterType.STRING,
            description="Natural language description of what you're looking for. Example: 'how are transactions signed'",
            required=True,
        ),
        ToolParameter(
            name="top_k",
            type=ParameterType.INTEGER,
            description="Number of matches to return. Default: 5.",
            required=False,
            default=5,
        ),
        ToolParameter(
            name="semantic_weight",
            type=ParameterType.FLOAT,
            description="Weight for embedding similarity in hybrid ranking. Default: 0.72.",
            required=False,
            default=0.72,
        ),
        ToolParameter(
            name="keyword_weight",
            type=ParameterType.FLOAT,
            description="Weight for keyword overlap in hybrid ranking. Default: 0.28.",
            required=False,
            default=0.28,
        ),
    ],
)


async def _build_search_documents(root_dir: str) -> list[SearchDocument]:
    """Build search index from all supported files in the project."""
    entries = walk_directory(WalkOptions(root_dir=root_dir, depth_limit=0))
    documents: list[SearchDocument] = []

    for entry in entries:
        if entry.is_directory:
            continue
        if not is_supported_file(entry.path):
            continue

        try:
            analysis = await analyze_file(entry.path)
            symbols = [s.name for s in flatten_symbols(analysis.symbols)]

            try:
                content = Path(entry.path).read_text(encoding="utf-8", errors="replace")[:500]
            except Exception:
                content = ""

            documents.append(
                SearchDocument(
                    path=entry.relative_path,
                    header=analysis.header,
                    symbols=symbols,
                    content=content,
                )
            )
        except Exception:
            continue

    return documents


async def _semantic_search(
    root_dir: str,
    query: str,
    top_k: int = 5,
    semantic_weight: float = 0.72,
    keyword_weight: float = 0.28,
) -> str:
    """Implementation of semantic code search."""
    documents = await _build_search_documents(root_dir)

    if not documents:
        return "No searchable documents found in the project."

    query_embedding = await fetch_embedding(query)

    results = await search_documents(
        documents=documents,
        query=query,
        query_embedding=query_embedding,
        top_k=top_k,
        semantic_weight=semantic_weight,
        keyword_weight=keyword_weight,
    )

    if not results:
        return f"No matches found for: \"{query}\""

    lines = [f'Semantic Search: "{query}" ({len(results)} results)\n']

    for i, result in enumerate(results, 1):
        lines.append(f"{i}. {result.path} (score: {result.score:.3f})")
        if result.header:
            lines.append(f"   {result.header}")
        if result.matched_symbols:
            lines.append(f"   Symbols: {', '.join(result.matched_symbols)}")
        lines.append(f"   Semantic: {result.semantic_score:.3f} | Keyword: {result.keyword_score:.3f}")
        lines.append("")

    return "\n".join(lines)


class SemanticSearchTool(AsyncToolInterface):
    """Semantic code search using embeddings and keyword matching."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "semantic_search"
        self.description = SEMANTIC_SEARCH_SCHEMA.description
        self._schema = SEMANTIC_SEARCH_SCHEMA

    def get_schema(self) -> dict[str, Any]:
        return self._schema.dict()

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        query = kwargs.get("query")
        if not query:
            return self._format_result(success=False, error="query is required")

        top_k = kwargs.get("top_k", 5)
        semantic_weight = kwargs.get("semantic_weight", 0.72)
        keyword_weight = kwargs.get("keyword_weight", 0.28)

        root_dir = self.root_dir or "."

        try:
            result = await _semantic_search(
                root_dir=root_dir,
                query=query,
                top_k=top_k,
                semantic_weight=semantic_weight,
                keyword_weight=keyword_weight,
            )
            return self._format_result(success=True, result=result)
        except Exception as e:
            _logger.error(f"semantic_search failed: {e}")
            return self._format_result(success=False, error=str(e))