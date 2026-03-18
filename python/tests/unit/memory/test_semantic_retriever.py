"""Unit tests for SemanticRetriever — no DB, no pgvector, no network.

Verifies:
- CANONICAL_EMBEDDING_DIMS constant is 768
- RetrievalResult exposes hits, best_score, references
- _cosine_similarity static method is correct
- Non-postgres path computes scores via Python cosine similarity (not .cosine_distance())
- pgvector path uses DB-labeled distance, not materialized attribute call
"""
from __future__ import annotations

import math
from unittest.mock import AsyncMock, MagicMock

import pytest

from mindflow_backend.memory.shared.retrieval.semantic import (
    CANONICAL_EMBEDDING_DIMS,
    RetrievalHit,
    RetrievalResult,
    SemanticRetriever,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _norm_vec(dim: int, seed: int = 1) -> list[float]:
    raw = [float((seed + i) % 7 - 3) for i in range(dim)]
    norm = math.sqrt(sum(v * v for v in raw))
    return [v / norm if norm > 0 else 0.0 for v in raw]


# ---------------------------------------------------------------------------
# CANONICAL_EMBEDDING_DIMS
# ---------------------------------------------------------------------------

def test_canonical_embedding_dims_is_768() -> None:
    assert CANONICAL_EMBEDDING_DIMS == 768


# ---------------------------------------------------------------------------
# RetrievalResult
# ---------------------------------------------------------------------------

def test_retrieval_result_exposes_hits_best_score_references() -> None:
    hits = [
        RetrievalHit(source_type="event", source_id=1, content_excerpt="hello", score=0.9),
        RetrievalHit(source_type="event", source_id=2, content_excerpt="world", score=0.7),
    ]
    result = RetrievalResult(hits=hits)
    assert result.hits is hits
    assert result.best_score == pytest.approx(0.9, rel=1e-5)
    assert isinstance(result.references, list)
    assert len(result.references) == 2


def test_retrieval_result_empty_has_zero_best_score() -> None:
    result = RetrievalResult(hits=[])
    assert result.best_score == 0.0
    assert result.references == []


def test_retrieval_result_references_contain_source_info() -> None:
    hits = [RetrievalHit(source_type="window", source_id=5, content_excerpt="ctx", score=0.8)]
    result = RetrievalResult(hits=hits)
    ref = result.references[0]
    assert ref["source_type"] == "window"
    assert ref["source_id"] == 5
    assert ref["score"] == pytest.approx(0.8, rel=1e-4)


def test_retrieval_result_references_ordered_by_score_desc() -> None:
    hits = [
        RetrievalHit(source_type="e", source_id=1, content_excerpt="a", score=0.5),
        RetrievalHit(source_type="e", source_id=2, content_excerpt="b", score=0.9),
        RetrievalHit(source_type="e", source_id=3, content_excerpt="c", score=0.7),
    ]
    result = RetrievalResult(hits=hits)
    scores = [r["score"] for r in result.references]
    # references must reflect the order of hits (preserving caller's order)
    assert scores == pytest.approx([0.5, 0.9, 0.7], rel=1e-4)


def test_retrieval_result_best_score_uses_max_not_first() -> None:
    hits = [
        RetrievalHit(source_type="e", source_id=1, content_excerpt="a", score=0.4),
        RetrievalHit(source_type="e", source_id=2, content_excerpt="b", score=0.95),
    ]
    result = RetrievalResult(hits=hits)
    assert result.best_score == pytest.approx(0.95, rel=1e-5)


# ---------------------------------------------------------------------------
# _cosine_similarity
# ---------------------------------------------------------------------------

def test_cosine_similarity_identical_vectors() -> None:
    v = _norm_vec(768, seed=3)
    score = SemanticRetriever._cosine_similarity(v, v)
    assert score == pytest.approx(1.0, rel=1e-5)


def test_cosine_similarity_orthogonal_vectors() -> None:
    v1 = [1.0, 0.0, 0.0]
    v2 = [0.0, 1.0, 0.0]
    score = SemanticRetriever._cosine_similarity(v1, v2)
    assert score == pytest.approx(0.0, abs=1e-9)


def test_cosine_similarity_known_value() -> None:
    v1 = [1.0, 1.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    # cos(45°) = 1/sqrt(2) ≈ 0.7071
    expected = 1.0 / math.sqrt(2)
    assert SemanticRetriever._cosine_similarity(v1, v2) == pytest.approx(expected, rel=1e-5)


def test_cosine_similarity_empty_returns_zero() -> None:
    assert SemanticRetriever._cosine_similarity([], []) == 0.0
    assert SemanticRetriever._cosine_similarity([1.0], []) == 0.0


def test_cosine_similarity_zero_norm_returns_zero() -> None:
    assert SemanticRetriever._cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


# ---------------------------------------------------------------------------
# Non-postgres path — retrieve_agent_context
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retrieve_agent_context_non_postgres_path_computes_score() -> None:
    """Non-postgres path uses _cosine_similarity, NOT .cosine_distance() on ORM obj."""
    query_vec = _norm_vec(768, seed=1)

    from mindflow_backend.memory.storage.models import AgentMemoryEmbedding

    row = MagicMock(spec=AgentMemoryEmbedding)
    row.source_type = "event"
    row.source_id = 42
    row.content_excerpt = "relevant content"
    row.vector = query_vec  # identical → similarity ≈ 1.0

    mock_db = MagicMock()
    mock_db.get_bind.return_value = None  # → non-postgres branch

    scalars_result = MagicMock()
    scalars_result.__iter__ = MagicMock(return_value=iter([row]))
    mock_db.scalars.return_value = scalars_result

    provider = MagicMock()
    provider.embed = AsyncMock(return_value=query_vec)
    provider.dimension.return_value = 768

    retriever = SemanticRetriever(embedding_provider=provider)
    hits = await retriever.retrieve_agent_context(
        mock_db,
        session_id="sess-1",
        agent_id="agent-1",
        query="test query",
        top_k=5,
        min_score=0.3,
    )

    assert len(hits) == 1
    assert hits[0].score == pytest.approx(1.0, rel=1e-5)
    assert hits[0].source_id == 42


@pytest.mark.asyncio
async def test_retrieve_agent_context_below_min_score_excluded() -> None:
    query_vec = _norm_vec(768, seed=1)
    # Anti-parallel vector → cosine similarity ≈ -1.0, guaranteed below any positive min_score
    anti_parallel = [-x for x in query_vec]

    from mindflow_backend.memory.storage.models import AgentMemoryEmbedding

    row = MagicMock(spec=AgentMemoryEmbedding)
    row.source_type = "event"
    row.source_id = 1
    row.content_excerpt = "irrelevant"
    row.vector = anti_parallel

    mock_db = MagicMock()
    mock_db.get_bind.return_value = None

    scalars_result = MagicMock()
    scalars_result.__iter__ = MagicMock(return_value=iter([row]))
    mock_db.scalars.return_value = scalars_result

    provider = MagicMock()
    provider.embed = AsyncMock(return_value=query_vec)
    provider.dimension.return_value = 768

    retriever = SemanticRetriever(embedding_provider=provider)
    hits = await retriever.retrieve_agent_context(
        mock_db,
        session_id="s",
        agent_id="a",
        query="q",
        top_k=5,
        min_score=0.3,  # anti-parallel has score ≈ -1.0, will be excluded
    )

    assert hits == []


# ---------------------------------------------------------------------------
# pgvector path — score computed from labeled DB column, not materialized obj
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retrieve_agent_context_postgres_path_uses_labeled_distance() -> None:
    """Postgres path must NOT call .cosine_distance() on the materialized ORM object.

    The fix: use db.execute() with a labeled distance column and extract score
    from the result tuple — so score is always a plain float, never a SQL element.
    """
    query_vec = _norm_vec(768, seed=1)

    from mindflow_backend.memory.storage.models import AgentMemoryEmbedding

    row_obj = MagicMock(spec=AgentMemoryEmbedding)
    row_obj.source_type = "event"
    row_obj.source_id = 7
    row_obj.content_excerpt = "pg hit"
    # vector must NOT have a callable .cosine_distance — to catch the old bug
    row_obj.vector = query_vec  # plain list, no .cosine_distance()

    # Simulate db.execute().all() returning (row, distance) tuples
    distance_value = 0.1  # cosine distance → score = 0.9
    mock_result = MagicMock()
    mock_result.all.return_value = [(row_obj, distance_value)]

    mock_db = MagicMock()
    # get_bind returns a dialect with name="postgresql" → postgres branch
    mock_bind = MagicMock()
    mock_bind.dialect.name = "postgresql"
    mock_db.get_bind.return_value = mock_bind
    mock_db.execute.return_value = mock_result

    provider = MagicMock()
    provider.embed = AsyncMock(return_value=query_vec)
    provider.dimension.return_value = 768

    retriever = SemanticRetriever(embedding_provider=provider)
    hits = await retriever.retrieve_agent_context(
        mock_db,
        session_id="sess-pg",
        agent_id="agent-pg",
        query="test",
        top_k=5,
        min_score=0.3,
    )

    assert len(hits) == 1
    assert hits[0].score == pytest.approx(0.9, rel=1e-4)
    assert hits[0].source_id == 7


@pytest.mark.asyncio
async def test_retrieve_session_context_postgres_path_supports_async_session_execute() -> None:
    """AsyncSession.execute() returns an awaitable, so the retriever must await it."""
    query_vec = _norm_vec(768, seed=2)

    from mindflow_backend.memory.storage.models import SessionEmbedding

    row_obj = MagicMock(spec=SessionEmbedding)
    row_obj.id = 11
    row_obj.content = "marker content"
    row_obj.session_id = "sess-async"
    row_obj.agent_id = "analyst"
    row_obj.embedding = query_vec

    mock_result = MagicMock()
    mock_result.all.return_value = [(row_obj, 0.08)]  # score = 0.92

    mock_db = MagicMock()
    mock_bind = MagicMock()
    mock_bind.dialect.name = "postgresql"
    mock_db.get_bind.return_value = mock_bind
    mock_db.execute = AsyncMock(return_value=mock_result)

    provider = MagicMock()
    provider.embed = AsyncMock(return_value=query_vec)
    provider.dimension.return_value = 768

    retriever = SemanticRetriever(embedding_provider=provider)
    hits = await retriever.retrieve_session_context(
        mock_db,
        session_id="sess-async",
        query="marker",
        top_k=4,
        min_score=0.3,
    )

    assert len(hits) == 1
    assert hits[0].score == pytest.approx(0.92, rel=1e-4)
    assert hits[0].source_id == 11


@pytest.mark.asyncio
async def test_retrieve_session_context_skips_nan_scores() -> None:
    query_vec = _norm_vec(768, seed=2)

    from mindflow_backend.memory.storage.models import SessionEmbedding

    row_obj = MagicMock(spec=SessionEmbedding)
    row_obj.id = 12
    row_obj.content = "bad hit"
    row_obj.session_id = "sess-async"
    row_obj.agent_id = "analyst"
    row_obj.embedding = query_vec

    mock_result = MagicMock()
    mock_result.all.return_value = [(row_obj, float("nan"))]

    mock_db = MagicMock()
    mock_bind = MagicMock()
    mock_bind.dialect.name = "postgresql"
    mock_db.get_bind.return_value = mock_bind
    mock_db.execute = AsyncMock(return_value=mock_result)

    provider = MagicMock()
    provider.embed = AsyncMock(return_value=query_vec)
    provider.dimension.return_value = 768

    retriever = SemanticRetriever(embedding_provider=provider)
    hits = await retriever.retrieve_session_context(
        mock_db,
        session_id="sess-async",
        query="marker",
        top_k=4,
        min_score=0.3,
    )

    assert hits == []
    # Verify execute() was used (not scalars()) in postgres branch
    mock_db.execute.assert_called_once()
