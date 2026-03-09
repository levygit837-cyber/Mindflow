"""Semantic retrieval using pgvector for all memory types."""

from __future__ import annotations

from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.memory.shared.embeddings.factory import IEmbeddingProvider, get_embedding_provider
from mindflow_backend.memory.storage.models import AgentMemoryEmbedding, SessionEmbedding

_logger = get_logger(__name__)


class RetrievalHit:
    """A single retrieval result from vector search."""

    __slots__ = ("source_type", "source_id", "content_excerpt", "score")

    def __init__(self, *, source_type: str, source_id: int, content_excerpt: str, score: float) -> None:
        self.source_type = source_type
        self.source_id = source_id
        self.content_excerpt = content_excerpt
        self.score = score

    def __repr__(self) -> str:
        return f"RetrievalHit(source={self.source_type}:{self.source_id}, score={self.score:.3f})"


class SemanticRetriever:
    """pgvector-backed semantic retrieval for agent and session memory.

    Replaces the previous in-Python cosine loop and the MemoryVectorDB abstraction.
    Uses SQLAlchemy ORM with pgvector's cosine_distance operator directly.
    """

    def __init__(self, embedding_provider: IEmbeddingProvider | None = None) -> None:
        self._provider = embedding_provider

    def _get_provider(self) -> IEmbeddingProvider:
        if self._provider is None:
            self._provider = get_embedding_provider()
        return self._provider

    async def retrieve_agent_context(
        self,
        db: Session,
        *,
        session_id: str,
        agent_id: str,
        query: str,
        top_k: int = 5,
        min_score: float = 0.3,
    ) -> list[RetrievalHit]:
        """Retrieve semantically relevant context from agent_memory_embeddings.

        Uses pgvector cosine distance — lower distance = higher similarity.
        Score returned is 1 - cosine_distance (similarity in [0, 1]).

        Args:
            db: SQLAlchemy synchronous session.
            session_id: Scope to this session.
            agent_id: Scope to this agent.
            query: Natural language query.
            top_k: Maximum number of results.
            min_score: Minimum cosine similarity (0.0–1.0).

        Returns:
            List of RetrievalHit ordered by score descending.
        """
        provider = self._get_provider()
        query_vec = await provider.embed(query)

        # pgvector <=> = cosine distance; 1 - distance = cosine similarity
        stmt = (
            select(AgentMemoryEmbedding)
            .where(
                AgentMemoryEmbedding.session_id == session_id,
                AgentMemoryEmbedding.agent_id == agent_id,
            )
            .order_by(AgentMemoryEmbedding.vector.cosine_distance(query_vec))
            .limit(top_k * 2)  # fetch extra to filter by min_score
        )

        rows = list(db.scalars(stmt))
        hits: list[RetrievalHit] = []

        for row in rows:
            try:
                distance = row.vector.cosine_distance(query_vec)
            except Exception:
                distance = 1.0  # fallback: treat as maximally dissimilar
            score = 1.0 - float(distance)
            if score < min_score:
                continue
            hits.append(
                RetrievalHit(
                    source_type=row.source_type,
                    source_id=row.source_id,
                    content_excerpt=row.content_excerpt,
                    score=score,
                )
            )
            if len(hits) >= top_k:
                break

        _logger.debug(
            "semantic_retrieval_agent",
            session_id=session_id,
            agent_id=agent_id,
            query_len=len(query),
            hits=len(hits),
        )
        return hits

    async def retrieve_session_context(
        self,
        db: Session,
        *,
        session_id: str,
        query: str,
        top_k: int = 5,
        min_score: float = 0.3,
    ) -> list[RetrievalHit]:
        """Retrieve context from session_embeddings (cross-agent within a session)."""
        provider = self._get_provider()
        query_vec = await provider.embed(query)

        stmt = (
            select(SessionEmbedding)
            .where(SessionEmbedding.session_id == session_id)
            .order_by(SessionEmbedding.embedding.cosine_distance(query_vec))
            .limit(top_k * 2)
        )

        rows = list(db.scalars(stmt))
        hits: list[RetrievalHit] = []

        for row in rows:
            try:
                distance = row.embedding.cosine_distance(query_vec)
            except Exception:
                distance = 1.0
            score = 1.0 - float(distance)
            if score < min_score:
                continue
            hits.append(
                RetrievalHit(
                    source_type="session_embedding",
                    source_id=row.id,
                    content_excerpt=row.content[:1500],
                    score=score,
                )
            )
            if len(hits) >= top_k:
                break

        return hits
