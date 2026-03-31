"""Semantic retrieval using pgvector for all memory types."""

from __future__ import annotations

import inspect
import math
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.memory.shared.embeddings.factory import (
    HashFallbackProvider,
    IEmbeddingProvider,
    get_embedding_provider,
)
from mindflow_backend.memory.storage.models import (
    AgentMemoryEmbedding,
    SessionBlock,
    SessionEmbedding,
)

_logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Canonical dimension — single source of truth for memory vector storage
# ---------------------------------------------------------------------------
CANONICAL_EMBEDDING_DIMS: int = 768


class RetrievalHit:
    """A single retrieval result from vector search."""

    __slots__ = (
        "source_type",
        "source_id",
        "content_excerpt",
        "score",
        "role",
        "content_kind",
        "quality_flags",
        "source_status",
        "derived_from_recall",
        "indexable",
        "session_id",
        "agent_id",
        "category",
        "title",
        "summary_md",
        "topic_tags",
    )

    def __init__(
        self,
        *,
        source_type: str,
        source_id: int,
        content_excerpt: str,
        score: float,
        role: str | None = None,
        content_kind: str = "query",
        quality_flags: list[str] | None = None,
        source_status: str = "final",
        derived_from_recall: bool = False,
        indexable: bool = True,
        session_id: str | None = None,
        agent_id: str | None = None,
        category: str | None = None,
        title: str | None = None,
        summary_md: str | None = None,
        topic_tags: list[str] | None = None,
    ) -> None:
        self.source_type = source_type
        self.source_id = source_id
        self.content_excerpt = content_excerpt
        self.score = score
        self.role = role
        self.content_kind = content_kind
        self.quality_flags = quality_flags or []
        self.source_status = source_status
        self.derived_from_recall = derived_from_recall
        self.indexable = indexable
        self.session_id = session_id
        self.agent_id = agent_id
        self.category = category
        self.title = title
        self.summary_md = summary_md
        self.topic_tags = topic_tags or []

    def __repr__(self) -> str:
        return f"RetrievalHit(source={self.source_type}:{self.source_id}, score={self.score:.3f})"


@dataclass
class RetrievalResult:
    """Aggregated result from a semantic retrieval operation.

    Attributes:
        hits: Ordered list of RetrievalHit objects (caller's ordering preserved).
        best_score: Maximum score across all hits; 0.0 if hits is empty.
        references: List of dicts with {source_type, source_id, score} metadata.
    """

    hits: list[RetrievalHit] = field(default_factory=list)

    @property
    def best_score(self) -> float:
        return max((h.score for h in self.hits), default=0.0)

    @property
    def references(self) -> list[dict]:
        return [
            {"source_type": h.source_type, "source_id": h.source_id, "score": h.score}
            for h in self.hits
        ]


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

    async def _embed_query(self, query: str) -> list[float]:
        provider = self._get_provider()
        try:
            return await provider.embed(query)
        except Exception as exc:
            dims = provider.dimension() if hasattr(provider, "dimension") else 768
            _logger.warning("semantic_retrieval_embedding_fallback", error=str(exc), dims=dims)
            return await HashFallbackProvider(dims=dims).embed(query)

    @staticmethod
    def _uses_postgres_vectors(db: Session) -> bool:
        bind = db.get_bind()
        return bool(bind is not None and bind.dialect.name == "postgresql")

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float:
        if not left or not right:
            return 0.0
        size = min(len(left), len(right))
        if size == 0:
            return 0.0
        left_slice = left[:size]
        right_slice = right[:size]
        numerator = sum(a * b for a, b in zip(left_slice, right_slice, strict=False))
        left_norm = math.sqrt(sum(a * a for a in left_slice))
        right_norm = math.sqrt(sum(b * b for b in right_slice))
        if left_norm == 0.0 or right_norm == 0.0:
            return 0.0
        return numerator / (left_norm * right_norm)

    @staticmethod
    def _vector_values(raw: object) -> list[float]:
        if raw is None:
            return []
        if hasattr(raw, "tolist"):
            raw = raw.tolist()
        return list(raw)

    @staticmethod
    def _distance_to_score(dist: object) -> float | None:
        try:
            score = 1.0 - float(dist)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(score):
            return None
        return score

    @staticmethod
    def _message_candidate_pool(top_k: int) -> int:
        return max(top_k * 5, 20)

    @staticmethod
    def _block_candidate_pool(top_k: int) -> int:
        return max(top_k * 4, 8)

    @staticmethod
    async def _scalars_list(db: Session, stmt) -> list:
        result = db.scalars(stmt)
        if inspect.isawaitable(result):
            result = await result
        try:
            return list(result)
        except TypeError:
            pass
        rows = result.all() if hasattr(result, "all") else []
        if inspect.isawaitable(rows):
            rows = await rows
        return list(rows)

    @staticmethod
    async def _execute_all(db: Session, stmt) -> list:
        result = db.execute(stmt)
        if inspect.isawaitable(result):
            result = await result
        rows = result.all()
        if inspect.isawaitable(rows):
            rows = await rows
        return list(rows)

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
        query_vec = await self._embed_query(query)

        if not self._uses_postgres_vectors(db):
            rows = await self._scalars_list(
                db,
                select(AgentMemoryEmbedding).where(
                    AgentMemoryEmbedding.session_id == session_id,
                    AgentMemoryEmbedding.agent_id == agent_id,
                ),
            )
            hits = [
                RetrievalHit(
                    source_type=row.source_type,
                    source_id=row.source_id,
                    content_excerpt=row.content_excerpt,
                    score=score,
                    session_id=row.session_id,
                    agent_id=row.agent_id,
                )
                for row in rows
                if (score := self._cosine_similarity(self._vector_values(row.vector), query_vec)) >= min_score
            ]
            hits.sort(key=lambda hit: hit.score, reverse=True)
            return hits[:top_k]

        # pgvector <=> = cosine distance; 1 - distance = cosine similarity.
        # Use db.execute() with a labeled distance column so the score is a plain
        # float extracted from the DB result — never call .cosine_distance() on the
        # materialized ORM object (it is not a callable Python method).
        dist_col = AgentMemoryEmbedding.vector.cosine_distance(query_vec).label("_dist")
        stmt = (
            select(AgentMemoryEmbedding, dist_col)
            .where(
                AgentMemoryEmbedding.session_id == session_id,
                AgentMemoryEmbedding.agent_id == agent_id,
            )
            .order_by(dist_col)
            .limit(top_k * 2)  # fetch extra to filter by min_score
        )

        result_rows = await self._execute_all(db, stmt)
        hits: list[RetrievalHit] = []

        for row, dist in result_rows:
            score = self._distance_to_score(dist)
            if score is None or score < min_score:
                continue
            hits.append(
                RetrievalHit(
                    source_type=row.source_type,
                    source_id=row.source_id,
                    content_excerpt=row.content_excerpt,
                    score=score,
                    session_id=row.session_id,
                    agent_id=row.agent_id,
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
        query_vec = await self._embed_query(query)

        if not self._uses_postgres_vectors(db):
            rows = await self._scalars_list(
                db,
                select(SessionEmbedding).where(SessionEmbedding.session_id == session_id),
            )
            hits = [
                RetrievalHit(
                    source_type="session_message",
                    source_id=row.id,
                    content_excerpt=row.content[:1500],
                    score=score,
                    role=getattr(row, "role", None),
                    content_kind=getattr(row, "content_kind", "query"),
                    quality_flags=list(getattr(row, "quality_flags", []) or []),
                    source_status=getattr(row, "source_status", "final"),
                    derived_from_recall=bool(getattr(row, "derived_from_recall", False)),
                    indexable=bool(getattr(row, "indexable", True)),
                    session_id=row.session_id,
                    agent_id=row.agent_id,
                )
                for row in rows
                if getattr(row, "indexable", True)
                and (score := self._cosine_similarity(self._vector_values(row.embedding), query_vec)) >= min_score
            ]
            hits.sort(key=lambda hit: hit.score, reverse=True)
            return hits[:top_k]

        dist_col = SessionEmbedding.embedding.cosine_distance(query_vec).label("_dist")
        stmt = (
            select(SessionEmbedding, dist_col)
            .where(
                SessionEmbedding.session_id == session_id,
                SessionEmbedding.indexable.is_(True),
            )
            .order_by(dist_col)
            .limit(self._message_candidate_pool(top_k))
        )

        result_rows = await self._execute_all(db, stmt)
        hits: list[RetrievalHit] = []

        for row, dist in result_rows:
            score = self._distance_to_score(dist)
            if score is None or score < min_score:
                continue
            hits.append(
                RetrievalHit(
                    source_type="session_message",
                    source_id=row.id,
                    content_excerpt=row.content[:1500],
                    score=score,
                    role=getattr(row, "role", None),
                    content_kind=getattr(row, "content_kind", "query"),
                    quality_flags=list(getattr(row, "quality_flags", []) or []),
                    source_status=getattr(row, "source_status", "final"),
                    derived_from_recall=bool(getattr(row, "derived_from_recall", False)),
                    indexable=bool(getattr(row, "indexable", True)),
                    session_id=row.session_id,
                    agent_id=row.agent_id,
                )
            )
            if len(hits) >= top_k:
                break

        return hits

    async def retrieve_cross_session_context(
        self,
        db: Session,
        *,
        query: str,
        top_k: int = 5,
        min_score: float = 0.3,
        exclude_session_id: str | None = None,
    ) -> list[RetrievalHit]:
        """Retrieve context across ALL sessions (cross-session retrieval).

        Searches session_embeddings without any session_id filter,
        allowing agents to retrieve memories from any previous session.

        Args:
            db: SQLAlchemy synchronous session.
            query: Natural language query.
            top_k: Maximum number of results.
            min_score: Minimum cosine similarity (0.0–1.0).
            exclude_session_id: Optionally exclude a specific session from results.

        Returns:
            List of RetrievalHit ordered by score descending.
        """
        query_vec = await self._embed_query(query)

        if not self._uses_postgres_vectors(db):
            stmt = select(SessionEmbedding)
            if exclude_session_id:
                stmt = stmt.where(SessionEmbedding.session_id != exclude_session_id)
            stmt = stmt.where(SessionEmbedding.indexable.is_(True))
            rows = await self._scalars_list(db, stmt)
            hits = [
                RetrievalHit(
                    source_type="session_message",
                    source_id=row.id,
                    content_excerpt=row.content[:1500],
                    score=score,
                    role=getattr(row, "role", None),
                    content_kind=getattr(row, "content_kind", "query"),
                    quality_flags=list(getattr(row, "quality_flags", []) or []),
                    source_status=getattr(row, "source_status", "final"),
                    derived_from_recall=bool(getattr(row, "derived_from_recall", False)),
                    indexable=bool(getattr(row, "indexable", True)),
                    session_id=row.session_id,
                    agent_id=row.agent_id,
                )
                for row in rows
                if getattr(row, "indexable", True)
                and (score := self._cosine_similarity(self._vector_values(row.embedding), query_vec)) >= min_score
            ]
            hits.sort(key=lambda hit: hit.score, reverse=True)
            return hits[:top_k]

        dist_col = SessionEmbedding.embedding.cosine_distance(query_vec).label("_dist")
        stmt = (
            select(SessionEmbedding, dist_col)
            .where(SessionEmbedding.indexable.is_(True))
            .order_by(dist_col)
            .limit(self._message_candidate_pool(top_k))
        )

        if exclude_session_id:
            stmt = stmt.where(SessionEmbedding.session_id != exclude_session_id)

        result_rows = await self._execute_all(db, stmt)
        hits: list[RetrievalHit] = []

        for row, dist in result_rows:
            score = self._distance_to_score(dist)
            if score is None or score < min_score:
                continue
            hits.append(
                RetrievalHit(
                    source_type="session_message",
                    source_id=row.id,
                    content_excerpt=row.content[:1500],
                    score=score,
                    role=getattr(row, "role", None),
                    content_kind=getattr(row, "content_kind", "query"),
                    quality_flags=list(getattr(row, "quality_flags", []) or []),
                    source_status=getattr(row, "source_status", "final"),
                    derived_from_recall=bool(getattr(row, "derived_from_recall", False)),
                    indexable=bool(getattr(row, "indexable", True)),
                    session_id=row.session_id,
                    agent_id=row.agent_id,
                )
            )
            if len(hits) >= top_k:
                break

        _logger.debug(
            "semantic_retrieval_cross_session",
            query_len=len(query),
            hits=len(hits),
        )
        return hits

    async def retrieve_session_blocks(
        self,
        db: Session,
        *,
        session_id: str,
        query: str,
        top_k: int = 2,
        min_score: float = 0.3,
        category_filters: list[str] | None = None,
    ) -> list[RetrievalHit]:
        query_vec = await self._embed_query(query)
        filters = set(category_filters or [])

        if not self._uses_postgres_vectors(db):
            stmt = select(SessionBlock).where(SessionBlock.session_id == session_id)
            if filters:
                stmt = stmt.where(SessionBlock.category.in_(filters))
            rows = await self._scalars_list(db, stmt)
            hits = [
                RetrievalHit(
                    source_type="session_block",
                    source_id=row.id,
                    content_excerpt=row.content_excerpt or row.summary_md,
                    score=score,
                    role="assistant",
                    content_kind=getattr(row, "content_kind", "answer"),
                    quality_flags=list(getattr(row, "quality_flags", []) or []),
                    source_status=getattr(row, "source_status", "final"),
                    derived_from_recall=bool(getattr(row, "derived_from_recall", False)),
                    indexable=bool(getattr(row, "indexable", True)),
                    session_id=row.session_id,
                    category=row.category,
                    title=row.title,
                    summary_md=row.summary_md,
                    topic_tags=row.topic_tags or [],
                )
                for row in rows
                if getattr(row, "indexable", True)
                and row.embedding is not None
                and (score := self._cosine_similarity(self._vector_values(row.embedding), query_vec)) >= min_score
            ]
            hits.sort(key=lambda hit: hit.score, reverse=True)
            return hits[:top_k]

        dist_col = SessionBlock.embedding.cosine_distance(query_vec).label("_dist")
        stmt = (
            select(SessionBlock, dist_col)
            .where(
                SessionBlock.session_id == session_id,
                SessionBlock.embedding.is_not(None),
                SessionBlock.indexable.is_(True),
            )
            .order_by(dist_col)
            .limit(self._block_candidate_pool(top_k))
        )
        if filters:
            stmt = stmt.where(SessionBlock.category.in_(filters))

        result_rows = await self._execute_all(db, stmt)
        hits: list[RetrievalHit] = []
        for row, dist in result_rows:
            score = self._distance_to_score(dist)
            if score is None or score < min_score:
                continue
            hits.append(
                RetrievalHit(
                    source_type="session_block",
                    source_id=row.id,
                    content_excerpt=row.content_excerpt or row.summary_md,
                    score=score,
                    role="assistant",
                    content_kind=getattr(row, "content_kind", "answer"),
                    quality_flags=list(getattr(row, "quality_flags", []) or []),
                    source_status=getattr(row, "source_status", "final"),
                    derived_from_recall=bool(getattr(row, "derived_from_recall", False)),
                    indexable=bool(getattr(row, "indexable", True)),
                    session_id=row.session_id,
                    category=row.category,
                    title=row.title,
                    summary_md=row.summary_md,
                    topic_tags=row.topic_tags or [],
                )
            )
            if len(hits) >= top_k:
                break
        return hits

    async def retrieve_cross_session_blocks(
        self,
        db: Session,
        *,
        query: str,
        top_k: int = 2,
        min_score: float = 0.3,
        exclude_session_id: str | None = None,
        category_filters: list[str] | None = None,
    ) -> list[RetrievalHit]:
        query_vec = await self._embed_query(query)
        filters = set(category_filters or [])

        if not self._uses_postgres_vectors(db):
            stmt = select(SessionBlock)
            if exclude_session_id:
                stmt = stmt.where(SessionBlock.session_id != exclude_session_id)
            stmt = stmt.where(SessionBlock.indexable.is_(True))
            if filters:
                stmt = stmt.where(SessionBlock.category.in_(filters))
            rows = await self._scalars_list(db, stmt)
            hits = [
                RetrievalHit(
                    source_type="session_block",
                    source_id=row.id,
                    content_excerpt=row.content_excerpt or row.summary_md,
                    score=score,
                    role="assistant",
                    content_kind=getattr(row, "content_kind", "answer"),
                    quality_flags=list(getattr(row, "quality_flags", []) or []),
                    source_status=getattr(row, "source_status", "final"),
                    derived_from_recall=bool(getattr(row, "derived_from_recall", False)),
                    indexable=bool(getattr(row, "indexable", True)),
                    session_id=row.session_id,
                    category=row.category,
                    title=row.title,
                    summary_md=row.summary_md,
                    topic_tags=row.topic_tags or [],
                )
                for row in rows
                if getattr(row, "indexable", True)
                and row.embedding is not None
                and (score := self._cosine_similarity(self._vector_values(row.embedding), query_vec)) >= min_score
            ]
            hits.sort(key=lambda hit: hit.score, reverse=True)
            return hits[:top_k]

        dist_col = SessionBlock.embedding.cosine_distance(query_vec).label("_dist")
        stmt = (
            select(SessionBlock, dist_col)
            .where(
                SessionBlock.embedding.is_not(None),
                SessionBlock.indexable.is_(True),
            )
            .order_by(dist_col)
            .limit(self._block_candidate_pool(top_k))
        )
        if exclude_session_id:
            stmt = stmt.where(SessionBlock.session_id != exclude_session_id)
        if filters:
            stmt = stmt.where(SessionBlock.category.in_(filters))

        result_rows = await self._execute_all(db, stmt)
        hits: list[RetrievalHit] = []
        for row, dist in result_rows:
            score = self._distance_to_score(dist)
            if score is None or score < min_score:
                continue
            hits.append(
                RetrievalHit(
                    source_type="session_block",
                    source_id=row.id,
                    content_excerpt=row.content_excerpt or row.summary_md,
                    score=score,
                    role="assistant",
                    content_kind=getattr(row, "content_kind", "answer"),
                    quality_flags=list(getattr(row, "quality_flags", []) or []),
                    source_status=getattr(row, "source_status", "final"),
                    derived_from_recall=bool(getattr(row, "derived_from_recall", False)),
                    indexable=bool(getattr(row, "indexable", True)),
                    session_id=row.session_id,
                    category=row.category,
                    title=row.title,
                    summary_md=row.summary_md,
                    topic_tags=row.topic_tags or [],
                )
            )
            if len(hits) >= top_k:
                break
        return hits
