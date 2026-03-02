from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.orm import Session

from omnimind_backend.infra.config import get_settings
from omnimind_backend.storage.models import (
    AgentMemoryCursor,
    AgentMemoryEmbedding,
    AgentMemoryEvent,
    AgentMemoryFact,
    AgentMemoryWindow,
)


def estimate_token_count(text: str) -> int:
    """Fast token estimate (~4 chars per token)."""
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9_]+", text.lower())


def _embed_text(text: str, dims: int) -> list[float]:
    vector = [0.0] * dims
    tokens = _tokenize(text)
    if not tokens:
        return vector

    for token in tokens:
        digest = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
        idx = digest % dims
        sign = -1.0 if ((digest >> 1) & 1) else 1.0
        vector[idx] += sign

    norm = math.sqrt(sum(v * v for v in vector))
    if norm <= 0:
        return vector
    return [v / norm for v in vector]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


@dataclass(slots=True)
class MemoryRetrievalResult:
    context: str
    references: list[str]


class AgentMemoryService:
    """Per-agent rolling memory with summary windows and retrieval."""

    def __init__(
        self,
        *,
        summary_window_tokens: int | None = None,
        retrieval_top_k: int | None = None,
        embedding_dims: int | None = None,
    ) -> None:
        settings = get_settings()
        self.summary_window_tokens = summary_window_tokens or settings.memory_summary_window_tokens
        self.retrieval_top_k = retrieval_top_k or settings.memory_retrieval_top_k
        self.embedding_dims = embedding_dims or settings.memory_embedding_dims

    def record_message(
        self,
        db: Session,
        *,
        session_id: str,
        agent_id: str,
        role: str,
        content: str,
        source_message_id: int | None = None,
    ) -> None:
        token_count = estimate_token_count(content)
        if token_count <= 0:
            return

        event = AgentMemoryEvent(
            session_id=session_id,
            agent_id=agent_id,
            role=role,
            content=content,
            token_count=token_count,
            source_message_id=source_message_id,
        )
        db.add(event)
        db.flush()

        cursor = self._get_or_create_cursor(db, session_id=session_id, agent_id=agent_id)
        cursor.token_total += token_count
        cursor.tokens_since_summary += token_count

        if cursor.tokens_since_summary >= self.summary_window_tokens:
            self._summarize_pending_window(
                db,
                session_id=session_id,
                agent_id=agent_id,
                cursor=cursor,
                event_end_id=event.id,
            )

    def retrieve_context_for_query(
        self,
        *,
        db: Session,
        session_id: str,
        agent_id: str,
        query: str,
    ) -> MemoryRetrievalResult:
        return self.retrieve_context(db, session_id=session_id, agent_id=agent_id, query=query)

    def retrieve_context(
        self,
        db: Session,
        *,
        session_id: str,
        agent_id: str,
        query: str,
    ) -> MemoryRetrievalResult:
        query_vec = _embed_text(query, self.embedding_dims)

        embeddings = list(
            db.scalars(
                select(AgentMemoryEmbedding)
                .where(
                    AgentMemoryEmbedding.session_id == session_id,
                    AgentMemoryEmbedding.agent_id == agent_id,
                )
                .order_by(AgentMemoryEmbedding.id.desc())
                .limit(512)
            )
        )

        ranked: list[tuple[float, AgentMemoryEmbedding]] = []
        for row in embeddings:
            score = _cosine_similarity(query_vec, row.vector)
            ranked.append((score, row))

        ranked.sort(key=lambda item: item[0], reverse=True)
        selected = [row for _, row in ranked[: self.retrieval_top_k] if row.content_excerpt.strip()]

        if not selected:
            windows = list(
                db.scalars(
                    select(AgentMemoryWindow)
                    .where(
                        AgentMemoryWindow.session_id == session_id,
                        AgentMemoryWindow.agent_id == agent_id,
                    )
                    .order_by(AgentMemoryWindow.id.desc())
                    .limit(self.retrieval_top_k)
                )
            )
            context = "\n\n".join(
                f"[window:{w.window_index}] {w.summary_md}" for w in windows if w.summary_md.strip()
            )
            refs = [f"window:{w.window_index}" for w in windows]
            return MemoryRetrievalResult(context=context, references=refs)

        blocks: list[str] = []
        refs: list[str] = []
        for item in selected:
            refs.append(f"{item.source_type}:{item.source_id}")
            blocks.append(f"[{item.source_type}:{item.source_id}] {item.content_excerpt}")

        return MemoryRetrievalResult(context="\n\n".join(blocks), references=refs)

    def _get_or_create_cursor(self, db: Session, *, session_id: str, agent_id: str) -> AgentMemoryCursor:
        cursor = db.scalar(
            select(AgentMemoryCursor).where(
                AgentMemoryCursor.session_id == session_id,
                AgentMemoryCursor.agent_id == agent_id,
            )
        )
        if cursor:
            return cursor

        cursor = AgentMemoryCursor(
            session_id=session_id,
            agent_id=agent_id,
            token_total=0,
            tokens_since_summary=0,
            window_index=0,
            last_summarized_event_id=None,
        )
        db.add(cursor)
        db.flush()
        return cursor

    def _summarize_pending_window(
        self,
        db: Session,
        *,
        session_id: str,
        agent_id: str,
        cursor: AgentMemoryCursor,
        event_end_id: int,
    ) -> None:
        start_event_id = (cursor.last_summarized_event_id or 0) + 1
        events = list(
            db.scalars(
                select(AgentMemoryEvent)
                .where(
                    AgentMemoryEvent.session_id == session_id,
                    AgentMemoryEvent.agent_id == agent_id,
                    AgentMemoryEvent.id >= start_event_id,
                    AgentMemoryEvent.id <= event_end_id,
                )
                .order_by(AgentMemoryEvent.id.asc())
            )
        )
        if not events:
            return

        summary_md, key_points = self._build_structured_summary(events)
        checksum_input = "\n".join(f"{e.id}:{e.content}" for e in events).encode("utf-8")
        checksum = hashlib.sha256(checksum_input).hexdigest()

        window = AgentMemoryWindow(
            session_id=session_id,
            agent_id=agent_id,
            window_index=cursor.window_index + 1,
            token_start=cursor.token_total - cursor.tokens_since_summary + 1,
            token_end=cursor.token_total,
            event_start_id=events[0].id,
            event_end_id=events[-1].id,
            summary_md=summary_md,
            key_points=key_points,
            coverage_ratio=1.0,
            checksum=checksum,
        )
        db.add(window)
        db.flush()

        self._store_embedding(
            db,
            session_id=session_id,
            agent_id=agent_id,
            source_type="window",
            source_id=window.id,
            content_excerpt=summary_md,
        )

        for point in key_points[:8]:
            fact = AgentMemoryFact(
                session_id=session_id,
                agent_id=agent_id,
                window_id=window.id,
                fact_type="insight",
                content=point,
                weight=1.0,
            )
            db.add(fact)
            db.flush()
            self._store_embedding(
                db,
                session_id=session_id,
                agent_id=agent_id,
                source_type="fact",
                source_id=fact.id,
                content_excerpt=point,
            )

        cursor.window_index += 1
        cursor.tokens_since_summary = 0
        cursor.last_summarized_event_id = event_end_id

    def _build_structured_summary(self, events: list[AgentMemoryEvent]) -> tuple[str, list[str]]:
        timeline: list[str] = []
        for event in events[:18]:
            compact = re.sub(r"\s+", " ", event.content).strip()
            compact = compact[:280]
            timeline.append(f"- [{event.role}] {compact}")

        candidate_sentences: list[str] = []
        for event in events:
            for sentence in re.split(r"[\n\.;:!?]", event.content):
                compact = re.sub(r"\s+", " ", sentence).strip()
                if len(compact) >= 24:
                    candidate_sentences.append(compact)

        key_points: list[str] = []
        seen: set[str] = set()
        for sentence in candidate_sentences:
            key = sentence.lower()
            if key in seen:
                continue
            seen.add(key)
            key_points.append(sentence[:240])
            if len(key_points) >= 10:
                break

        if not key_points and timeline:
            key_points = [line[11:] for line in timeline[:3]]

        summary_lines = [
            "Resumo consolidado da janela de contexto do agente:",
            f"- Total de eventos: {len(events)}",
            "- Linha do tempo principal:",
            *timeline,
        ]
        if key_points:
            summary_lines.append("- Pontos importantes:")
            summary_lines.extend(f"  - {item}" for item in key_points[:8])

        return "\n".join(summary_lines), key_points

    def _store_embedding(
        self,
        db: Session,
        *,
        session_id: str,
        agent_id: str,
        source_type: str,
        source_id: int,
        content_excerpt: str,
    ) -> None:
        embedding = AgentMemoryEmbedding(
            session_id=session_id,
            agent_id=agent_id,
            source_type=source_type,
            source_id=source_id,
            content_excerpt=content_excerpt[:1500],
            vector=_embed_text(content_excerpt, self.embedding_dims),
        )
        db.add(embedding)


@lru_cache(maxsize=1)
def get_memory_service() -> AgentMemoryService:
    return AgentMemoryService()
