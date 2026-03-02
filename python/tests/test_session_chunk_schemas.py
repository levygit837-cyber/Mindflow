"""Tests for session chunk schemas."""

from uuid import uuid4

from omnimind_backend.schemas.session_chunk import (
    ChunkEdgeType,
    ChunkMetadata,
    ChunkRetrievalQuery,
    ChunkType,
)


def test_chunk_types() -> None:
    assert ChunkType.PLANNING == "planning"
    assert ChunkType.IMPLEMENTATION == "implementation"
    assert ChunkType.RESEARCH == "research"
    assert ChunkType.REVIEW == "review"
    assert ChunkType.DISCUSSION == "discussion"
    assert ChunkType.META == "meta"


def test_chunk_metadata_creation() -> None:
    meta = ChunkMetadata(
        chunk_id=uuid4(),
        session_id="sess-123",
        agent_id="analyst",
        sequence=0,
        token_count=1500,
        start_turn=0,
        end_turn=3,
        topic_tags=["authentication", "jwt"],
        summary="Analyzed the auth module",
        confidence=0.9,
        freshness=1.0,
        chunk_type=ChunkType.IMPLEMENTATION,
    )
    assert meta.token_count == 1500
    assert meta.chunk_type == ChunkType.IMPLEMENTATION


def test_chunk_edge_types() -> None:
    assert ChunkEdgeType.FOLLOWS == "follows"
    assert ChunkEdgeType.REFERENCES == "references"
    assert ChunkEdgeType.SUPERSEDES == "supersedes"
    assert ChunkEdgeType.DEPENDS_ON == "depends_on"


def test_retrieval_query() -> None:
    q = ChunkRetrievalQuery(session_id="sess-123", by_topic=["implementation"])
    assert q.by_topic == ["implementation"]
    assert q.by_agent is None
    assert q.limit == 10
