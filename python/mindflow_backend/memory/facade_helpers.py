"""Helper utilities for MemoryFacade.

Provides text processing, scoring, and conversion utilities
used by the main MemoryFacade class.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from mindflow_backend.memory.indexing import normalized_lexical_similarity
from mindflow_backend.memory.storage.models import SessionBlock
from mindflow_backend.schemas.memory.contracts import (
    MemoryRecallHit,
    MemorySourceType,
    SessionBlockSchema,
)

_STOPWORDS = {
    "a", "ao", "as", "como", "com", "da", "das", "de", "do", "dos", "e",
    "em", "essa", "esse", "foi", "o", "os", "para", "por", "que", "se",
    "um", "uma", "the", "and", "for", "with", "from",
}

_CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("decision", ("decid", "defin", "escolh", "opt", "adot", "vamos usar")),
    ("debugging", ("erro", "bug", "falha", "debug", "corrig", "fix", "exception")),
    ("implementation", ("implement", "codigo", "refactor", "schema", "migration", "endpoint", "api")),
    ("testing", ("teste", "pytest", "assert", "valid", "verification")),
    ("research", ("pesquis", "research", "benchmark", "compar", "investig")),
    ("planning", ("planej", "roadmap", "fases", "next step", "estrateg", "plan")),
]


def to_memory_hit(hit: Any) -> MemoryRecallHit:
    """Convert a raw hit to MemoryRecallHit."""
    if isinstance(hit, MemoryRecallHit):
        return hit
    return MemoryRecallHit(
        source_type=getattr(hit, "source_type", MemorySourceType.SESSION_MESSAGE.value),
        source_id=getattr(hit, "source_id", None),
        session_id=getattr(hit, "session_id", None),
        agent_id=getattr(hit, "agent_id", None),
        content=getattr(hit, "content_excerpt", "") or getattr(hit, "content", ""),
        content_excerpt=getattr(hit, "content_excerpt", None),
        score=float(getattr(hit, "score", 0.0)),
        final_score=float(getattr(hit, "final_score", getattr(hit, "score", 0.0))),
        category=getattr(hit, "category", None),
        title=getattr(hit, "title", None),
        summary_md=getattr(hit, "summary_md", None),
        topic_tags=list(getattr(hit, "topic_tags", []) or []),
        role=getattr(hit, "role", None),
        content_kind=str(getattr(hit, "content_kind", "query")),
        quality_flags=list(getattr(hit, "quality_flags", []) or []),
        source_status=str(getattr(hit, "source_status", "final")),
        derived_from_recall=bool(getattr(hit, "derived_from_recall", False)),
    )


def format_context(
    message_hits: list[MemoryRecallHit],
    block_hits: list[MemoryRecallHit],
) -> str:
    """Format memory hits into context string."""
    if not message_hits and not block_hits:
        return ""

    lines = ["Memory Context:"]
    for hit in block_hits[:2]:
        summary = (hit.summary_md or hit.content or "").strip()
        title = hit.title or "Session block"
        category = hit.category or "general"
        if summary:
            lines.append(f"- [session_block:{category}] {title}: {summary}")
    assistant_hits = [hit for hit in message_hits if hit.answer_bearing]
    framing_hits = [hit for hit in message_hits if not hit.answer_bearing]
    for hit in assistant_hits[:4]:
        if hit.content.strip():
            lines.append(f"- [session_message:answer] {hit.content.strip()}")
    for hit in framing_hits[:2]:
        if hit.content.strip():
            lines.append(f"- [session_message:query] {hit.content.strip()}")
    return "\n".join(lines)


def to_session_block_schema(row: SessionBlock) -> SessionBlockSchema:
    """Convert SessionBlock ORM to schema."""
    return SessionBlockSchema(
        id=row.id,
        session_id=row.session_id,
        sequence=row.sequence,
        category=row.category,
        title=row.title,
        summary_md=row.summary_md,
        content_excerpt=row.content_excerpt,
        topic_tags=row.topic_tags or [],
        message_start_id=row.message_start_id,
        message_end_id=row.message_end_id,
        token_count=row.token_count,
        confidence=row.confidence,
        source=row.source,
        indexable=row.indexable,
        content_kind=row.content_kind,
        quality_flags=row.quality_flags or [],
        source_status=row.source_status,
        derived_from_recall=row.derived_from_recall,
        created_at=row.created_at,
        updated_at=row.updated_at,
        closed_at=row.closed_at,
    )


def row_to_retrieval_hit(row: SessionBlock, *, score: float) -> Any:
    """Convert a SessionBlock row to a retrieval hit."""
    return type(
        "BlockHit",
        (),
        {
            "source_type": MemorySourceType.SESSION_BLOCK.value,
            "source_id": row.id,
            "content_excerpt": row.content_excerpt,
            "score": score,
            "final_score": score,
            "session_id": row.session_id,
            "category": row.category,
            "title": row.title,
            "summary_md": row.summary_md,
            "topic_tags": row.topic_tags or [],
            "role": "assistant",
            "content_kind": row.content_kind,
            "quality_flags": row.quality_flags or [],
            "source_status": row.source_status,
            "derived_from_recall": row.derived_from_recall,
        },
    )()


def filter_and_rerank_hits(
    hits: list[MemoryRecallHit],
    *,
    query: str,
    cross_session: bool,
) -> tuple[list[MemoryRecallHit], int]:
    """Filter and rerank memory hits."""
    filtered_hits = 0
    kept: list[MemoryRecallHit] = []

    for hit in sorted(hits, key=lambda item: item.score, reverse=True):
        lexical_similarity = normalized_lexical_similarity(
            query, hit.content or hit.summary_md or ""
        )
        answer_bearing = is_answer_bearing(hit)
        if lexical_similarity > 0.92 and not answer_bearing:
            filtered_hits += 1
            continue

        base_score = float(hit.score)
        if str(hit.source_type) == MemorySourceType.SESSION_BLOCK.value:
            base_score += 0.10
        if hit.content_kind == "answer":
            base_score += 0.08
        if hit.role == "assistant" and hit.source_status == "final":
            base_score += 0.04
        if hit.content_kind == "continuation_prompt":
            base_score -= 0.20
        if any(flag in {"placeholder", "tool_error", "partial_stream"} for flag in hit.quality_flags):
            base_score -= 0.25

        hit.answer_bearing = answer_bearing
        hit.final_score = base_score
        hit.metadata["lexical_similarity"] = lexical_similarity
        hit.metadata["base_score"] = base_score
        kept.append(hit)

    kept.sort(
        key=lambda item: (
            float(item.metadata.get("base_score", item.final_score)),
            item.score,
        ),
        reverse=True,
    )

    session_penalties: Counter[str] = Counter()
    for hit in kept:
        penalty_count = session_penalties[hit.session_id or ""]
        if penalty_count > 0:
            hit.final_score = float(hit.metadata.get("base_score", hit.final_score)) - (0.10 * penalty_count)
        session_penalties[hit.session_id or ""] += 1

    kept.sort(key=lambda item: (item.final_score, item.score), reverse=True)

    if not cross_session:
        return kept, filtered_hits

    limited: list[MemoryRecallHit] = []
    per_session: Counter[str] = Counter()
    for hit in kept:
        session_key = hit.session_id or ""
        if session_key and per_session[session_key] >= 2:
            continue
        limited.append(hit)
        if session_key:
            per_session[session_key] += 1
    return limited, filtered_hits


def is_answer_bearing(hit: MemoryRecallHit) -> bool:
    """Check if a hit is answer-bearing."""
    if str(hit.source_type) == MemorySourceType.SESSION_BLOCK.value:
        return True
    if hit.content_kind != "answer":
        return False
    if hit.source_status != "final":
        return False
    return not any(flag in {"placeholder", "tool_error", "partial_stream"} for flag in hit.quality_flags)


def infer_category(content: str, *, agent_id: str, role: str) -> str:
    """Infer content category from text."""
    lowered = content.lower()
    for category, markers in _CATEGORY_RULES:
        if any(marker in lowered for marker in markers):
            return category
    if role == "assistant" and agent_id == "orchestrator":
        return "decision"
    return "discussion"


def derive_title(content: str, *, category: str) -> str:
    """Derive a title from content."""
    cleaned = re.sub(r"\s+", " ", content).strip(" .:-")
    snippet = cleaned[:72].strip()
    if not snippet:
        return category.replace("_", " ").title()
    return f"{category.replace('_', ' ').title()}: {snippet}"


def extract_tags(content: str, *, category: str) -> list[str]:
    """Extract tags from content."""
    tokens = re.findall(r"[a-zA-ZÀ-ÿ0-9_-]{4,}", content.lower())
    counts = Counter(token for token in tokens if token not in _STOPWORDS)
    tags = [category]
    tags.extend(token for token, _ in counts.most_common(4) if token != category)
    return list(dict.fromkeys(tags))[:5]


def build_excerpt(existing: str, content: str) -> str:
    """Build content excerpt."""
    parts = [part.strip() for part in existing.split(" | ") if part.strip()]
    compact = re.sub(r"\s+", " ", content).strip()[:220]
    if compact:
        parts.append(compact)
    unique_parts = list(dict.fromkeys(parts))
    return " | ".join(unique_parts[-3:])


def build_summary(*, title: str, category: str, excerpts: list[str]) -> str:
    """Build summary from excerpts."""
    snippets = [snippet.strip() for snippet in excerpts if snippet and snippet.strip()]
    compact = "; ".join(list(dict.fromkeys(snippets))[:2])
    if compact:
        return f"{title}. Categoria: {category}. Resumo: {compact}"
    return f"{title}. Categoria: {category}."


def normalize_vector(vector: Any) -> list[float] | None:
    """Normalize a vector to list of floats."""
    if vector is None:
        return None
    normalized = list(vector)
    if len(normalized) == 0:
        return None
    return [float(value) for value in normalized]


def cosine_similarity(left: list[float] | None, right: list[float] | None) -> float:
    """Calculate cosine similarity between two vectors."""
    left_vector = normalize_vector(left)
    right_vector = normalize_vector(right)
    if left_vector is None or right_vector is None:
        return 0.0
    size = min(len(left_vector), len(right_vector))
    if size == 0:
        return 0.0
    left_slice = left_vector[:size]
    right_slice = right_vector[:size]
    numerator = sum(a * b for a, b in zip(left_slice, right_slice, strict=False))
    left_norm = sum(a * a for a in left_slice) ** 0.5
    right_norm = sum(b * b for b in right_slice) ** 0.5
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return numerator / (left_norm * right_norm)