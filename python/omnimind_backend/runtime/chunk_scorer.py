"""Session chunk retrieval scoring.

Implements the retrieval ranking formula:
score = 0.4 * topic_relevance + 0.35 * freshness + 0.25 * confidence
"""

from __future__ import annotations

from omnimind_backend.schemas.session_chunk import ChunkMetadata

W_TOPIC = 0.40
W_FRESHNESS = 0.35
W_CONFIDENCE = 0.25

EXCLUSION_THRESHOLD = 0.3


def _compute_topic_relevance(chunk_tags: list[str], query_topics: list[str]) -> float:
    """Compute topic overlap between chunk tags and query topics."""
    if not query_topics or not chunk_tags:
        return 0.0
    chunk_set = {t.lower() for t in chunk_tags}
    query_set = {t.lower() for t in query_topics}
    overlap = len(chunk_set & query_set)
    return overlap / len(query_set)


def compute_chunk_score(chunk: ChunkMetadata, query_topics: list[str]) -> float:
    """Compute retrieval score for a session chunk.

    Args:
        chunk: Chunk metadata with topic_tags, freshness, confidence.
        query_topics: Topics from the retrieval query.

    Returns:
        Score (0-1). Below 0.3 should be excluded from results.
    """
    topic_relevance = _compute_topic_relevance(chunk.topic_tags, query_topics)

    score = (
        W_TOPIC * topic_relevance
        + W_FRESHNESS * chunk.freshness
        + W_CONFIDENCE * chunk.confidence
    )
    return round(min(max(score, 0.0), 1.0), 4)
