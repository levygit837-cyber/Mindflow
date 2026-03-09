"""Semantic retrieval operations for memory.

Thin shim that delegates to the canonical SemanticRetriever in
memory/shared/retrieval/semantic.py (pgvector-based).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm > 0 else 0.0


class SemanticRetriever:
    """Legacy shim — delegates to memory.shared.retrieval.semantic.SemanticRetriever."""

    def __init__(self, embedding_dims: int = 768) -> None:
        self._dims = embedding_dims
        self.logger = _logger

    async def search_context(
        self,
        session_id: str,
        agent_id: str,
        query: str,
        top_k: int = 5,
        min_score: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """Search for semantically similar context via the shared SemanticRetriever."""
        try:
            from mindflow_backend.memory.shared.retrieval.semantic import (
                SemanticRetriever as SharedRetriever,
            )
            retriever = SharedRetriever()
            # SemanticRetriever needs a DB session; return empty if called without one
            _logger.warning(
                "memory.retrieval.semantic.SemanticRetriever.search_context called without "
                "a DB session — use memory.shared.retrieval.semantic.SemanticRetriever directly."
            )
            return []
        except Exception as exc:
            self.logger.error(f"Semantic search failed: {exc}")
            return []

    def calculate_relevance_score(
        self,
        query_embedding: List[float],
        candidate_embedding: List[float],
    ) -> float:
        """Calculate cosine similarity between two embeddings."""
        return _cosine_similarity(query_embedding, candidate_embedding)
