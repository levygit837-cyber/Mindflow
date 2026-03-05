"""Tests for chunk retrieval scoring."""

from uuid import uuid4

from omnimind_backend.runtime.chunk_scorer import compute_chunk_score
from omnimind_backend.schemas.session_chunk import ChunkMetadata, ChunkType


def test_high_relevance_fresh_confident() -> None:
    chunk = ChunkMetadata(
        chunk_id=uuid4(),
        session_id="s1",
        agent_id="coder",
        sequence=0,
        topic_tags=["auth"],
        confidence=0.9,
        freshness=1.0,
        chunk_type=ChunkType.IMPLEMENTATION,
    )
    score = compute_chunk_score(chunk, query_topics=["auth"])
    assert score > 0.7


def test_low_freshness_reduces_score() -> None:
    chunk = ChunkMetadata(
        chunk_id=uuid4(),
        session_id="s1",
        agent_id="coder",
        sequence=0,
        topic_tags=["auth"],
        confidence=0.9,
        freshness=0.1,
        chunk_type=ChunkType.IMPLEMENTATION,
    )
    score = compute_chunk_score(chunk, query_topics=["auth"])
    # 0.4*1.0 + 0.35*0.1 + 0.25*0.9 = 0.66
    assert score < 0.7


def test_no_topic_match_low_score() -> None:
    chunk = ChunkMetadata(
        chunk_id=uuid4(),
        session_id="s1",
        agent_id="coder",
        sequence=0,
        topic_tags=["database"],
        confidence=0.9,
        freshness=1.0,
        chunk_type=ChunkType.IMPLEMENTATION,
    )
    score = compute_chunk_score(chunk, query_topics=["auth"])
    # 0.4*0.0 + 0.35*1.0 + 0.25*0.9 = 0.575
    assert score < 0.6


def test_below_threshold_excluded() -> None:
    chunk = ChunkMetadata(
        chunk_id=uuid4(),
        session_id="s1",
        agent_id="coder",
        sequence=0,
        topic_tags=["old"],
        confidence=0.1,
        freshness=0.1,
        chunk_type=ChunkType.META,
    )
    score = compute_chunk_score(chunk, query_topics=["auth"])
    assert score < 0.3
