"""Canonical async facade for runtime memory operations."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.memory.indexing import (
    classify_memory_content,
    normalized_lexical_similarity,
)
from mindflow_backend.memory.shared.embeddings import factory as embedding_factory
from mindflow_backend.memory.shared.retrieval.semantic import SemanticRetriever
from mindflow_backend.memory.storage.models import (
    AgentMemoryEvent,
    AgentMemoryWindow,
    HierarchicalAnnotation,
    MemoryCategory,
    MemorySubCategory,
    ProjectMemory,
    SessionBlock,
    SessionEmbedding,
)
from mindflow_backend.schemas.memory.annotation import MemoryAnnotation
from mindflow_backend.schemas.memory.contracts import (
    AgentMemorySnapshot,
    MemoryPersistResult,
    MemoryRecallHit,
    MemoryRecallRequest,
    MemoryRecallResponse,
    MemoryRecallScope,
    MemorySourceType,
    SessionBlockSchema,
)
from mindflow_backend.utils.core import estimate_token_count

_logger = get_logger(__name__)


def _get_db_session_factory():
    from mindflow_backend.infra.database.connection import get_db_session

    return get_db_session



@dataclass(slots=True)
class _EmbeddingOutcome:
    vector: list[float] | None
    degraded_reason: str | None = None


class MemoryFacade:
    """Canonical async facade over session memory, block memory and agent trails."""

    def __init__(self) -> None:
        from mindflow_backend.memory.session_memory.service import SessionMemoryService

        self._session_service = SessionMemoryService()
        self._retriever = SemanticRetriever()

    async def record_message(
        self,
        db: Any,
        *,
        session_id: str,
        agent_id: str,
        role: str,
        content: str,
        source_message_id: int | None = None,
        idempotency_key: str | None = None,
        source_status: str = "final",
        derived_from_recall: bool = False,
    ) -> MemoryPersistResult:
        token_count = estimate_token_count(content)
        chat_stored = source_message_id is not None
        if token_count <= 0:
            return MemoryPersistResult(
                stored=False,
                chat_stored=chat_stored,
                indexable=False,
                skipped_reasons=["empty_content"],
                token_count=0,
            )

        indexing = classify_memory_content(
            role=role,
            content=content,
            source_status=source_status,
            derived_from_recall=derived_from_recall,
        )

        existing_embedding = await self._find_existing_session_embedding(
            db,
            session_id=session_id,
            source_message_id=source_message_id,
            idempotency_key=idempotency_key,
        )
        existing_event = await self._find_existing_agent_event(
            db,
            session_id=session_id,
            agent_id=agent_id,
            source_message_id=source_message_id,
        )
        if existing_embedding is not None or existing_event is not None:
            return MemoryPersistResult(
                embedding_id=str(existing_embedding.id) if existing_embedding is not None else None,
                event_id=existing_event.id if existing_event is not None else None,
                stored=True,
                chat_stored=chat_stored,
                embedding_stored=existing_embedding is not None,
                agent_event_stored=existing_event is not None,
                block_updated=False,
                indexable=indexing.indexable,
                skipped_reasons=indexing.skipped_reasons,
                was_deduplicated=True,
                token_count=0,
            )

        event = AgentMemoryEvent(
            session_id=session_id,
            agent_id=agent_id,
            role=role,
            content=content,
            token_count=token_count,
            source_message_id=source_message_id,
        )
        db.add(event)
        await db.flush()

        embedding_outcome = await self._embed_text(content)
        embedding_id: str | None = None
        embedding_stored = False
        if indexing.indexable and embedding_outcome.vector is not None:
            session_embedding = SessionEmbedding(
                session_id=session_id,
                content=content[:1500],
                embedding=embedding_outcome.vector,
                source_message_id=source_message_id,
                idempotency_key=idempotency_key,
                role=role,
                agent_id=agent_id,
                indexable=indexing.indexable,
                content_kind=indexing.content_kind,
                quality_flags=indexing.quality_flags,
                source_status=source_status,
                derived_from_recall=indexing.derived_from_recall,
                session_metadata={
                    "role": role,
                    "agent_id": agent_id,
                    "source_message_id": source_message_id,
                    "idempotency_key": idempotency_key,
                    "content_kind": indexing.content_kind,
                    "quality_flags": indexing.quality_flags,
                    "source_status": source_status,
                    "derived_from_recall": indexing.derived_from_recall,
                },
            )
            db.add(session_embedding)
            await db.flush()
            embedding_id = str(session_embedding.id)
            embedding_stored = True

        block_updated = False
        should_update_block = indexing.answer_bearing or (
            role == "user"
            and indexing.indexable
            and indexing.content_kind == "query"
        )
        if should_update_block:
            try:
                await self._update_session_block(
                    db,
                    session_id=session_id,
                    agent_id=agent_id,
                    role=role,
                    content=content,
                    source_message_id=source_message_id or event.id,
                    token_count=token_count,
                    message_vector=embedding_outcome.vector,
                    content_kind=indexing.content_kind,
                    quality_flags=indexing.quality_flags,
                    source_status=source_status,
                    derived_from_recall=indexing.derived_from_recall,
                )
                block_updated = True
            except Exception as exc:
                _logger.warning(
                    "session_block_update_failed",
                    session_id=session_id,
                    agent_id=agent_id,
                    error=str(exc),
                )

        await db.commit()
        return MemoryPersistResult(
            embedding_id=embedding_id,
            event_id=event.id,
            stored=True,
            chat_stored=chat_stored,
            embedding_stored=embedding_stored,
            agent_event_stored=True,
            block_updated=block_updated,
            degraded_reason=embedding_outcome.degraded_reason,
            indexable=indexing.indexable,
            skipped_reasons=indexing.skipped_reasons,
            was_deduplicated=False,
            token_count=token_count,
        )

    async def recall(self, request: MemoryRecallRequest) -> MemoryRecallResponse:
        try:
            async with _get_db_session_factory()() as db:
                message_hits = await self._recall_message_hits(db, request)
                block_hits = await self._recall_block_hits(db, request)

            candidate_hits = [
                *[self._to_memory_hit(hit) for hit in message_hits],
                *[self._to_memory_hit(hit) for hit in block_hits],
            ]
            all_hits, filtered_hits_count = self._filter_and_rerank_hits(
                candidate_hits,
                query=request.query,
                cross_session=(
                    request.cross_session or request.scope == MemoryRecallScope.CROSS_SESSION
                ),
            )
            block_candidates = [
                hit
                for hit in all_hits
                if str(hit.source_type) == MemorySourceType.SESSION_BLOCK.value
            ]
            message_candidates = [
                hit
                for hit in all_hits
                if str(hit.source_type) != MemorySourceType.SESSION_BLOCK.value
            ]
            selected_blocks = block_candidates[: request.top_k_blocks]
            selected_messages = message_candidates[: request.top_k_messages]
            selected_hits = [*selected_blocks, *selected_messages]
            context = self._format_context(
                selected_messages,
                selected_blocks,
            )
            best_score = max((hit.final_score for hit in selected_hits), default=0.0)
            grounding_recommended = (
                best_score >= 0.72
                or any(bool(hit.answer_bearing) for hit in selected_hits)
            )
            return MemoryRecallResponse(
                context=context,
                hits=selected_hits,
                best_score=best_score,
                grounding_recommended=grounding_recommended,
                filtered_hits_count=filtered_hits_count,
                scope_used=(
                    MemoryRecallScope.CROSS_SESSION
                    if request.cross_session or request.scope == MemoryRecallScope.CROSS_SESSION
                    else MemoryRecallScope.CURRENT_SESSION
                ),
                fallback_used=False,
                metadata={
                    "message_hits": len(selected_messages),
                    "block_hits": len(selected_blocks),
                    "include_messages": request.include_messages,
                    "include_blocks": request.include_blocks,
                    "candidate_hits": len(candidate_hits),
                },
            )
        except Exception as exc:
            _logger.warning(
                "memory_facade_recall_failed",
                session_id=request.session_id,
                agent_id=request.agent_id,
                error=str(exc),
            )
            return MemoryRecallResponse(metadata={"error": str(exc)})

    async def get_agent_snapshot(
        self,
        session_id: str,
        agent_id: str,
        token_limit: int | None = None,
    ) -> AgentMemorySnapshot:
        try:
            async with _get_db_session_factory()() as db:
                query = (
                    select(AgentMemoryEvent)
                    .where(
                        AgentMemoryEvent.session_id == session_id,
                        AgentMemoryEvent.agent_id == agent_id,
                    )
                    .order_by(AgentMemoryEvent.created_at.desc())
                )
                rows = list((await db.execute(query.limit(50))).scalars())
                windows = list((
                    await db.execute(
                        select(AgentMemoryWindow)
                        .where(
                            AgentMemoryWindow.session_id == session_id,
                            AgentMemoryWindow.agent_id == agent_id,
                        )
                        .order_by(AgentMemoryWindow.window_index.desc())
                        .limit(5)
                    )
                ).scalars())

            events: list[dict[str, Any]] = []
            total_tokens = 0
            for row in rows:
                if token_limit and total_tokens + row.token_count > token_limit:
                    break
                events.append(
                    {
                        "id": row.id,
                        "role": row.role,
                        "content": row.content,
                        "token_count": row.token_count,
                        "created_at": row.created_at.isoformat() if row.created_at else None,
                    }
                )
                total_tokens += row.token_count

            window_payload = [
                {
                    "window_index": row.window_index,
                    "summary_md": row.summary_md,
                    "key_points": row.key_points,
                }
                for row in windows
            ]
            context_summary = window_payload[0]["summary_md"] if window_payload else ""

            return AgentMemorySnapshot(
                session_id=session_id,
                agent_id=agent_id,
                event_count=len(events),
                window_count=len(window_payload),
                total_tokens=total_tokens,
                context_summary=context_summary,
                events=list(reversed(events)),
                windows=window_payload,
            )
        except Exception as exc:
            _logger.warning(
                "memory_facade_snapshot_failed",
                session_id=session_id,
                agent_id=agent_id,
                error=str(exc),
            )
            return AgentMemorySnapshot(session_id=session_id, agent_id=agent_id)

    async def list_session_blocks(
        self,
        session_id: str,
        categories: list[str] | None = None,
        limit: int = 10,
    ) -> list[SessionBlockSchema]:
        async with _get_db_session_factory()() as db:
            query = select(SessionBlock).where(SessionBlock.session_id == session_id)
            if categories:
                query = query.where(SessionBlock.category.in_(categories))
            query = query.order_by(SessionBlock.sequence.desc()).limit(limit)
            rows = list((await db.execute(query)).scalars())
        return [self._to_session_block_schema(row) for row in rows]

    async def save_annotation(self, annotation: MemoryAnnotation) -> None:
        """
        Salva anotação de observer na memória universal.

        Usa o sistema de memória existente com tags especiais para
        identificação de anotações de observers.

        Fase 3B — SPADE Memory Observer Protocol
        """
        if not annotation.is_significant():
            return

        content = annotation.to_memory_content()
        token_count = estimate_token_count(content)
        if token_count <= 0:
            return

        try:
            async with _get_db_session_factory()() as db:
                event = AgentMemoryEvent(
                    session_id=annotation.session_id,
                    agent_id=annotation.observer_agent_id,
                    role="observer",
                    content=content,
                    token_count=token_count,
                )
                db.add(event)
                await db.flush()

                embedding_outcome = await self._embed_text(content)
                if embedding_outcome.vector is not None:
                    session_embedding = SessionEmbedding(
                        session_id=annotation.session_id,
                        content=content[:1500],
                        embedding=embedding_outcome.vector,
                        role="observer",
                        agent_id=annotation.observer_agent_id,
                        indexable=True,
                        content_kind="annotation",
                        quality_flags=[f"type:{annotation.annotation_type}"],
                        source_status="observer",
                        session_metadata={
                            "annotation_id": annotation.annotation_id,
                            "source_agent": annotation.source_agent_id,
                            "mission_id": annotation.mission_id,
                            "importance": annotation.importance,
                            "annotation_type": annotation.annotation_type,
                            "tags": annotation.tags,
                        },
                    )
                    db.add(session_embedding)
                await db.commit()

                _logger.debug(
                    "annotation_saved",
                    extra={
                        "annotation_id": annotation.annotation_id,
                        "observer": annotation.observer_agent_id,
                        "source": annotation.source_agent_id,
                        "mission_id": annotation.mission_id,
                        "importance": annotation.importance,
                        "type": annotation.annotation_type,
                    },
                )
        except Exception as exc:
            _logger.warning(
                "annotation_save_failed",
                extra={
                    "annotation_id": annotation.annotation_id,
                    "error": str(exc),
                },
            )

    async def _find_existing_session_embedding(
        self,
        db: Any,
        *,
        session_id: str,
        source_message_id: int | None,
        idempotency_key: str | None,
    ) -> SessionEmbedding | None:
        if source_message_id is not None:
            result = await db.execute(
                select(SessionEmbedding).where(
                    SessionEmbedding.session_id == session_id,
                    SessionEmbedding.source_message_id == source_message_id,
                )
            )
            row = result.scalar_one_or_none()
            if row is not None:
                return row
        if idempotency_key:
            result = await db.execute(
                select(SessionEmbedding).where(
                    SessionEmbedding.session_id == session_id,
                    SessionEmbedding.idempotency_key == idempotency_key,
                )
            )
            return result.scalar_one_or_none()
        return None

    async def _find_existing_agent_event(
        self,
        db: Any,
        *,
        session_id: str,
        agent_id: str,
        source_message_id: int | None,
    ) -> AgentMemoryEvent | None:
        if source_message_id is None:
            return None
        result = await db.execute(
            select(AgentMemoryEvent).where(
                AgentMemoryEvent.session_id == session_id,
                AgentMemoryEvent.agent_id == agent_id,
                AgentMemoryEvent.source_message_id == source_message_id,
            )
        )
        return result.scalar_one_or_none()

    async def _embed_text(self, text: str) -> _EmbeddingOutcome:
        health = embedding_factory.get_embedding_provider_health()
        if health is not None and not health.is_healthy:
            return _EmbeddingOutcome(vector=None, degraded_reason=health.reason or "embedding_provider_degraded")

        try:
            provider = embedding_factory.get_embedding_provider()
            vector = await provider.embed(text)
            normalized_vector = self._normalize_vector(vector)
            if normalized_vector is None:
                return _EmbeddingOutcome(vector=None, degraded_reason="empty_embedding_vector")
            return _EmbeddingOutcome(vector=normalized_vector)
        except Exception as exc:
            _logger.warning("memory_embed_failed", error=str(exc))
            return _EmbeddingOutcome(vector=None, degraded_reason=str(exc))

    async def _update_session_block(
        self,
        db: Any,
        *,
        session_id: str,
        agent_id: str,
        role: str,
        content: str,
        source_message_id: int,
        token_count: int,
        message_vector: list[float] | None,
        content_kind: str,
        quality_flags: list[str],
        source_status: str,
        derived_from_recall: bool,
    ) -> None:
        settings = get_settings()
        category = self._infer_category(content, agent_id=agent_id, role=role)
        tags = self._extract_tags(content, category=category)
        title = self._derive_title(content, category=category)

        current = await self._get_open_block(db, session_id=session_id)
        should_rotate = False
        if current is not None:
            current_count = await self._count_block_messages(
                db,
                session_id=session_id,
                message_start_id=current.message_start_id,
                message_end_id=current.message_end_id,
            )
            similarity = self._cosine_similarity(message_vector, current.embedding)
            should_rotate = (
                current_count >= settings.memory_block_max_messages
                or (current.token_count + token_count) > settings.memory_block_max_tokens
                or (
                    current.category != category
                    and similarity < settings.memory_block_topic_shift_threshold
                )
            )
            if should_rotate:
                current.closed_at = func.now()
                current.updated_at = func.now()
                current = None

        if current is None:
            current = SessionBlock(
                session_id=session_id,
                sequence=await self._next_block_sequence(db, session_id=session_id),
                category=category,
                title=title,
                summary_md=self._build_summary(title=title, category=category, excerpts=[content]),
                content_excerpt=self._build_excerpt("", content),
                topic_tags=tags,
                message_start_id=source_message_id,
                message_end_id=source_message_id,
                token_count=token_count,
                confidence=0.85 if agent_id == "orchestrator" else 0.7,
                source="orchestrator" if agent_id == "orchestrator" else "inferred",
                indexable=True,
                content_kind=content_kind,
                quality_flags=quality_flags,
                source_status=source_status,
                derived_from_recall=derived_from_recall,
                embedding=message_vector,
            )
            db.add(current)
            await db.flush()
            return

        current.message_end_id = source_message_id
        current.token_count += token_count
        existing_tags = list(current.topic_tags or [])
        current.topic_tags = list(dict.fromkeys([*existing_tags, *tags]))[:8]
        current.content_excerpt = self._build_excerpt(current.content_excerpt, content)
        current.summary_md = self._build_summary(
            title=current.title,
            category=current.category,
            excerpts=current.content_excerpt.split(" | "),
        )
        current.content_kind = content_kind
        current.quality_flags = list(dict.fromkeys([*(current.quality_flags or []), *quality_flags]))
        current.source_status = source_status
        current.derived_from_recall = bool(current.derived_from_recall or derived_from_recall)
        if message_vector is not None:
            block_embedding = await self._embed_text(f"{current.summary_md}\n{current.content_excerpt}")
            if block_embedding.vector is not None:
                current.embedding = block_embedding.vector
        await db.flush()

    async def _get_open_block(self, db: Any, *, session_id: str) -> SessionBlock | None:
        result = await db.execute(
            select(SessionBlock)
            .where(
                SessionBlock.session_id == session_id,
                SessionBlock.closed_at.is_(None),
            )
            .order_by(SessionBlock.sequence.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _next_block_sequence(self, db: Any, *, session_id: str) -> int:
        result = await db.execute(
            select(func.max(SessionBlock.sequence)).where(SessionBlock.session_id == session_id)
        )
        return int(result.scalar() or 0) + 1

    async def _count_block_messages(
        self,
        db: Any,
        *,
        session_id: str,
        message_start_id: int,
        message_end_id: int,
    ) -> int:
        from mindflow_backend.memory.storage.models import ChatMessage

        result = await db.execute(
            select(func.count(ChatMessage.id)).where(
                ChatMessage.session_id == session_id,
                ChatMessage.id >= message_start_id,
                ChatMessage.id <= message_end_id,
            )
        )
        return int(result.scalar() or 0)

    async def _recall_message_hits(self, db: Any, request: MemoryRecallRequest):
        if not request.include_messages or request.top_k_messages <= 0:
            return []
        if request.cross_session or request.scope == MemoryRecallScope.CROSS_SESSION:
            return await self._retriever.retrieve_cross_session_context(
                db,
                query=request.query,
                top_k=request.top_k_messages,
                min_score=request.min_score,
                exclude_session_id=request.exclude_session_id,
            )
        return await self._retriever.retrieve_session_context(
            db,
            session_id=request.session_id,
            query=request.query,
            top_k=request.top_k_messages,
            min_score=request.min_score,
        )

    async def _recall_block_hits(self, db: Any, request: MemoryRecallRequest):
        if not request.include_blocks or request.top_k_blocks <= 0:
            return []

        if request.cross_session or request.scope == MemoryRecallScope.CROSS_SESSION:
            hits = await self._retriever.retrieve_cross_session_blocks(
                db,
                query=request.query,
                top_k=request.top_k_blocks,
                min_score=request.min_score,
                exclude_session_id=request.exclude_session_id,
                category_filters=request.category_filters,
            )
        else:
            hits = await self._retriever.retrieve_session_blocks(
                db,
                session_id=request.session_id,
                query=request.query,
                top_k=request.top_k_blocks,
                min_score=request.min_score,
                category_filters=request.category_filters,
            )

        if hits or not request.category_filters:
            return hits

        query = select(SessionBlock)
        if request.cross_session or request.scope == MemoryRecallScope.CROSS_SESSION:
            if request.exclude_session_id:
                query = query.where(SessionBlock.session_id != request.exclude_session_id)
        else:
            query = query.where(SessionBlock.session_id == request.session_id)
        query = (
            query.where(
                SessionBlock.category.in_(request.category_filters),
                SessionBlock.indexable.is_(True),
            )
            .order_by(SessionBlock.updated_at.desc())
            .limit(request.top_k_blocks)
        )
        rows = list((await db.execute(query)).scalars())
        return [
            self._row_to_retrieval_hit(
                row,
                score=normalized_lexical_similarity(
                    request.query,
                    f"{row.summary_md}\n{row.content_excerpt}",
                ),
            )
            for row in rows
            if normalized_lexical_similarity(
                request.query,
                f"{row.summary_md}\n{row.content_excerpt}",
            ) >= request.min_score
        ]

    def _to_memory_hit(self, hit: Any) -> MemoryRecallHit:
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

    def _format_context(
        self,
        message_hits: list[MemoryRecallHit],
        block_hits: list[MemoryRecallHit],
    ) -> str:
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

    def _to_session_block_schema(self, row: SessionBlock) -> SessionBlockSchema:
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

    def _row_to_retrieval_hit(self, row: SessionBlock, *, score: float) -> Any:
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

    def _filter_and_rerank_hits(
        self,
        hits: list[MemoryRecallHit],
        *,
        query: str,
        cross_session: bool,
    ) -> tuple[list[MemoryRecallHit], int]:
        filtered_hits = 0
        kept: list[MemoryRecallHit] = []

        for hit in sorted(hits, key=lambda item: item.score, reverse=True):
            lexical_similarity = normalized_lexical_similarity(query, hit.content or hit.summary_md or "")
            answer_bearing = self._is_answer_bearing(hit)
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

    def _is_answer_bearing(self, hit: MemoryRecallHit) -> bool:
        if str(hit.source_type) == MemorySourceType.SESSION_BLOCK.value:
            return True
        if hit.content_kind != "answer":
            return False
        if hit.source_status != "final":
            return False
        return not any(flag in {"placeholder", "tool_error", "partial_stream"} for flag in hit.quality_flags)

    def _infer_category(self, content: str, *, agent_id: str, role: str) -> str:
        lowered = content.lower()
        for category, markers in _CATEGORY_RULES:
            if any(marker in lowered for marker in markers):
                return category
        if role == "assistant" and agent_id == "orchestrator":
            return "decision"
        return "discussion"

    def _derive_title(self, content: str, *, category: str) -> str:
        cleaned = re.sub(r"\s+", " ", content).strip(" .:-")
        snippet = cleaned[:72].strip()
        if not snippet:
            return category.replace("_", " ").title()
        return f"{category.replace('_', ' ').title()}: {snippet}"

    def _extract_tags(self, content: str, *, category: str) -> list[str]:
        tokens = re.findall(r"[a-zA-ZÀ-ÿ0-9_-]{4,}", content.lower())
        counts = Counter(token for token in tokens if token not in _STOPWORDS)
        tags = [category]
        tags.extend(token for token, _ in counts.most_common(4) if token != category)
        return list(dict.fromkeys(tags))[:5]

    def _build_excerpt(self, existing: str, content: str) -> str:
        parts = [part.strip() for part in existing.split(" | ") if part.strip()]
        compact = re.sub(r"\s+", " ", content).strip()[:220]
        if compact:
            parts.append(compact)
        unique_parts = list(dict.fromkeys(parts))
        return " | ".join(unique_parts[-3:])

    def _build_summary(self, *, title: str, category: str, excerpts: list[str]) -> str:
        snippets = [snippet.strip() for snippet in excerpts if snippet and snippet.strip()]
        compact = "; ".join(list(dict.fromkeys(snippets))[:2])
        if compact:
            return f"{title}. Categoria: {category}. Resumo: {compact}"
        return f"{title}. Categoria: {category}."

    def _normalize_vector(self, vector: Any) -> list[float] | None:
        if vector is None:
            return None
        normalized = list(vector)
        if len(normalized) == 0:
            return None
        return [float(value) for value in normalized]

    def _cosine_similarity(self, left: list[float] | None, right: list[float] | None) -> float:
        left_vector = self._normalize_vector(left)
        right_vector = self._normalize_vector(right)
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

    # ========================================================================
    # Phase 3: Hierarchical Memory Save
    # ========================================================================

    async def save_hierarchical_annotation(
        self,
        db: Any,
        *,
        annotation: MemoryAnnotation,
        project_name: str,
        project_root: str,
        category_name: str | None = None,
        subcategory_name: str | None = None,
        file_path: str | None = None,
        lines_modified: dict[str, Any] | None = None,
        diff_summary: str | None = None,
    ) -> int:
        """Save a hierarchical annotation to the database.

        Automatically creates ProjectMemory, MemoryCategory, and MemorySubCategory
        if they don't exist.

        Args:
            db: Database session
            annotation: MemoryAnnotation with basic info
            project_name: Name of the project (e.g., "MindFlow")
            project_root: Root path of the project
            category_name: Optional category name (e.g., "API")
            subcategory_name: Optional subcategory name (e.g., "Controllers")
            file_path: Optional file path for code changes
            lines_modified: Optional dict with line change info
            diff_summary: Optional diff summary

        Returns:
            ID of the created HierarchicalAnnotation
        """
        # Get or create ProjectMemory
        project_result = await db.execute(
            select(ProjectMemory).where(
                ProjectMemory.project_name == project_name,
                ProjectMemory.root_path == project_root,
            )
        )
        project = project_result.scalar_one_or_none()

        if not project:
            project = ProjectMemory(
                project_name=project_name,
                root_path=project_root,
            )
            db.add(project)
            await db.flush()  # Get project.id

        # Get or create MemoryCategory (if category_name provided)
        category_id = None
        if category_name:
            category_result = await db.execute(
                select(MemoryCategory).where(
                    MemoryCategory.project_id == project.id,
                    MemoryCategory.name == category_name,
                )
            )
            category = category_result.scalar_one_or_none()

            if not category:
                category = MemoryCategory(
                    project_id=project.id,
                    name=category_name,
                )
                db.add(category)
                await db.flush()  # Get category.id

            category_id = category.id

        # Get or create MemorySubCategory (if subcategory_name provided)
        subcategory_id = None
        if subcategory_name and category_id:
            subcategory_result = await db.execute(
                select(MemorySubCategory).where(
                    MemorySubCategory.category_id == category_id,
                    MemorySubCategory.name == subcategory_name,
                )
            )
            subcategory = subcategory_result.scalar_one_or_none()

            if not subcategory:
                subcategory = MemorySubCategory(
                    category_id=category_id,
                    name=subcategory_name,
                )
                db.add(subcategory)
                await db.flush()  # Get subcategory.id

            subcategory_id = subcategory.id

        # Create HierarchicalAnnotation
        hierarchical_annotation = HierarchicalAnnotation(
            project_id=project.id,
            category_id=category_id,
            subcategory_id=subcategory_id,
            observer_agent_id=annotation.observer_agent_id,
            source_agent_id=annotation.source_agent_id,
            mission_id=annotation.mission_id,
            session_id=annotation.session_id,
            file_path=file_path,
            lines_modified=lines_modified,
            diff_summary=diff_summary,
            content=annotation.content,
            annotation_type=annotation.annotation_type,
            importance=annotation.importance,
            tags=annotation.tags,
            raw_event_type=annotation.raw_event_type,
        )

        db.add(hierarchical_annotation)
        await db.flush()

        _logger.info(
            "hierarchical_annotation_saved",
            extra={
                "annotation_id": hierarchical_annotation.id,
                "project": project_name,
                "category": category_name,
                "subcategory": subcategory_name,
                "file_path": file_path,
            },
        )

        return hierarchical_annotation.id
