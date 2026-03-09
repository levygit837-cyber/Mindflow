from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.orm import Session

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.memory.shared.embeddings.factory import get_embedding_provider
from mindflow_backend.memory.shared.retrieval.semantic import SemanticRetriever
from mindflow_backend.memory.storage.models import (
    AgentMemoryCursor,
    AgentMemoryEmbedding,
    AgentMemoryEvent,
    AgentMemoryWindow,
    SessionEmbedding,
)
from mindflow_backend.schemas.session.contracts import RetrievedContext
from mindflow_backend.utils.core import estimate_token_count

_logger = get_logger(__name__)


@dataclass(slots=True)
class MemoryRetrievalResult:
    context: str
    references: list[str]


class AgentMemoryService:
    """Per-agent rolling memory with real-time embedding and pgvector retrieval.

    Every message is embedded immediately upon recording. Window summaries are
    generated extractively (no LLM) when the token threshold is crossed.
    """

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
        self._retriever = SemanticRetriever()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

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
        """Record a message and immediately store its embedding."""
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
        db.flush()  # assigns event.id

        # Real-time embedding — every message, not on a threshold
        self._store_event_embedding(db, event=event)

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
        """Synchronous retrieval — embeds query and runs pgvector search."""
        import asyncio

        async def _run():
            return await self._retriever.retrieve_agent_context(
                db,
                session_id=session_id,
                agent_id=agent_id,
                query=query,
                top_k=self.retrieval_top_k,
            )

        try:
            loop = asyncio.get_event_loop()
            hits = loop.run_until_complete(_run())
        except RuntimeError:
            # Already inside an event loop — use a new thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                hits = pool.submit(asyncio.run, _run()).result()

        if not hits:
            return self._fallback_to_windows(db, session_id=session_id, agent_id=agent_id)

        blocks: list[str] = []
        refs: list[str] = []
        for hit in hits:
            refs.append(f"{hit.source_type}:{hit.source_id}")
            blocks.append(f"[{hit.source_type}:{hit.source_id}] {hit.content_excerpt}")

        return MemoryRetrievalResult(context="\n\n".join(blocks), references=refs)

    async def retrieve_context_for_query_async(
        self,
        db: Session,
        *,
        session_id: str,
        agent_id: str,
        query: str,
        top_k: int = 4,
        min_score: float = 0.3,
    ) -> RetrievedContext:
        """Async retrieval via pgvector — returns a RetrievedContext contract."""
        _logger.info(
            "vector_context_retrieval_started",
            session_id=session_id,
            agent_id=agent_id,
            query=query,
            top_k=top_k,
        )

        hits = await self._retriever.retrieve_agent_context(
            db,
            session_id=session_id,
            agent_id=agent_id,
            query=query,
            top_k=top_k,
            min_score=min_score,
        )

        context_parts = [f"Context for query: {query}"]
        for hit in hits:
            context_parts.append(f"- {hit.content_excerpt}")

        avg_score = sum(h.score for h in hits) / len(hits) if hits else 0.0

        return RetrievedContext(
            context_id=self._generate_context_id(),
            session_id=session_id,
            query=query,
            context_windows=[(0, 0)],
            content="\n\n".join(context_parts),
            relevance_score=avg_score,
            source_sessions=[session_id],
            metadata={
                "agent_id": agent_id,
                "retrieval_method": "pgvector_cosine",
                "results_count": len(hits),
            },
        )

    async def store_session_embedding(
        self,
        db: Session,
        *,
        session_id: str,
        content: str,
        metadata: dict | None = None,
    ) -> str:
        """Store a content embedding for the session (used by external callers)."""
        provider = get_embedding_provider()
        vector = await provider.embed(content)

        session_embedding = SessionEmbedding(
            session_id=session_id,
            content=content,
            embedding=vector,
            session_metadata=metadata or {},
        )
        db.add(session_embedding)
        db.flush()
        return str(session_embedding.id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _store_event_embedding(self, db: Session, *, event: AgentMemoryEvent) -> None:
        """Embed an event and persist to agent_memory_embeddings immediately."""
        import asyncio

        async def _embed():
            provider = get_embedding_provider()
            return await provider.embed(event.content)

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Schedule as a task without blocking — embedding is best-effort
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    vector = pool.submit(asyncio.run, _embed()).result()
            else:
                vector = loop.run_until_complete(_embed())
        except Exception as exc:
            _logger.warning("event_embedding_failed", event_id=event.id, error=str(exc))
            return

        embedding = AgentMemoryEmbedding(
            session_id=event.session_id,
            agent_id=event.agent_id,
            source_type="event",
            source_id=event.id,
            content_excerpt=event.content[:1500],
            vector=vector,
        )
        db.add(embedding)

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
        """Embed arbitrary content and persist to agent_memory_embeddings."""
        import asyncio

        async def _embed():
            provider = get_embedding_provider()
            return await provider.embed(content_excerpt)

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    vector = pool.submit(asyncio.run, _embed()).result()
            else:
                vector = loop.run_until_complete(_embed())
        except Exception as exc:
            _logger.warning("embedding_failed", source_type=source_type, source_id=source_id, error=str(exc))
            return

        db.add(AgentMemoryEmbedding(
            session_id=session_id,
            agent_id=agent_id,
            source_type=source_type,
            source_id=source_id,
            content_excerpt=content_excerpt[:1500],
            vector=vector,
        ))

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

        cursor.window_index += 1
        cursor.tokens_since_summary = 0
        cursor.last_summarized_event_id = event_end_id

    def _build_structured_summary(self, events: list[AgentMemoryEvent]) -> tuple[str, list[str]]:
        """Extractive summary — no LLM calls. Uses first N events as timeline
        and key-sentence extraction by deduplication."""
        timeline: list[str] = []
        for event in events[:18]:
            compact = re.sub(r"\s+", " ", event.content).strip()[:280]
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
            "Consolidated summary of the agent context window:",
            f"- Total events: {len(events)}",
            "- Main timeline:",
            *timeline,
        ]
        if key_points:
            summary_lines.append("- Key points:")
            summary_lines.extend(f"  - {item}" for item in key_points[:8])

        return "\n".join(summary_lines), key_points

    def _fallback_to_windows(
        self,
        db: Session,
        *,
        session_id: str,
        agent_id: str,
    ) -> MemoryRetrievalResult:
        """Fallback when no embedding results found — return latest windows."""
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

    def _generate_context_id(self) -> str:
        import os
        return f"context_{abs(hash(os.urandom(16)))}"


@lru_cache(maxsize=1)
def get_memory_service() -> AgentMemoryService:
    return AgentMemoryService()
