"""Cleanup and backfill helpers for semantic session memory."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, select

from mindflow_backend.infra.config import get_settings
from mindflow_backend.memory.facade import MemoryFacade
from mindflow_backend.memory.indexing import classify_memory_content, is_continuation_prompt
from mindflow_backend.memory.storage.models import ChatMessage, SessionBlock, SessionEmbedding
from mindflow_backend.utils.core import estimate_token_count


@dataclass(slots=True)
class SessionMemoryCleanupReport:
    sessions_processed: int = 0
    embeddings_reclassified: int = 0
    embeddings_disabled: int = 0
    blocks_deleted: int = 0
    blocks_rebuilt: int = 0


class SessionMemoryCleanupService:
    """Soft-clean contaminated semantic memory and rebuild session blocks."""

    def __init__(self, facade: MemoryFacade | None = None) -> None:
        self._facade = facade or MemoryFacade()

    async def cleanup(
        self,
        db: Any,
        *,
        session_id: str | None = None,
        rebuild_blocks: bool = True,
    ) -> SessionMemoryCleanupReport:
        report = SessionMemoryCleanupReport()
        session_ids = [session_id] if session_id else await self._discover_session_ids(db)

        for current_session_id in session_ids:
            if not current_session_id:
                continue
            report.sessions_processed += 1
            report.embeddings_reclassified += await self._reclassify_embeddings(
                db,
                session_id=current_session_id,
                report=report,
            )
            if rebuild_blocks:
                deleted, rebuilt = await self._rebuild_blocks(db, session_id=current_session_id)
                report.blocks_deleted += deleted
                report.blocks_rebuilt += rebuilt

        await db.commit()
        return report

    async def _discover_session_ids(self, db: Any) -> list[str]:
        session_ids: set[str] = set()
        for model in (ChatMessage, SessionEmbedding, SessionBlock):
            rows = await db.execute(select(model.session_id).distinct())
            session_ids.update(value for value in rows.scalars() if value)
        return sorted(session_ids)

    async def _reclassify_embeddings(
        self,
        db: Any,
        *,
        session_id: str,
        report: SessionMemoryCleanupReport,
    ) -> int:
        messages = await db.execute(
            select(ChatMessage).where(ChatMessage.session_id == session_id)
        )
        message_by_id = {row.id: row for row in messages.scalars()}

        result = await db.execute(
            select(SessionEmbedding)
            .where(SessionEmbedding.session_id == session_id)
            .order_by(SessionEmbedding.created_at.asc(), SessionEmbedding.id.asc())
        )
        changed = 0
        for row in result.scalars():
            message = message_by_id.get(row.source_message_id) if row.source_message_id is not None else None
            role = row.role or (message.role if message else "assistant")
            content = row.content or (message.content if message else "")
            derived_from_recall = bool(
                row.derived_from_recall
                or (role == "user" and is_continuation_prompt(content))
            )
            source_status = row.source_status or "final"
            decision = classify_memory_content(
                role=role,
                content=content,
                source_status=source_status,
                derived_from_recall=derived_from_recall,
            )

            previous = (
                row.indexable,
                row.content_kind,
                tuple(row.quality_flags or []),
                row.source_status,
                row.derived_from_recall,
            )
            row.indexable = decision.indexable
            row.content_kind = decision.content_kind
            row.quality_flags = list(decision.quality_flags)
            row.source_status = source_status
            row.derived_from_recall = decision.derived_from_recall
            row.role = role

            current = (
                row.indexable,
                row.content_kind,
                tuple(row.quality_flags or []),
                row.source_status,
                row.derived_from_recall,
            )
            if current != previous:
                changed += 1
            if previous[0] and not row.indexable:
                report.embeddings_disabled += 1

        return changed

    async def _rebuild_blocks(self, db: Any, *, session_id: str) -> tuple[int, int]:
        existing_rows = await db.execute(
            select(SessionBlock.id).where(SessionBlock.session_id == session_id)
        )
        existing_ids = list(existing_rows.scalars())
        await db.execute(delete(SessionBlock).where(SessionBlock.session_id == session_id))

        messages_result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id.asc())
        )
        messages = list(messages_result.scalars())

        embeddings_result = await db.execute(
            select(SessionEmbedding)
            .where(SessionEmbedding.session_id == session_id)
            .order_by(SessionEmbedding.created_at.asc(), SessionEmbedding.id.asc())
        )
        embedding_by_message = {
            row.source_message_id: row
            for row in embeddings_result.scalars()
            if row.source_message_id is not None
        }

        rebuilt_count = 0
        sequence = 0
        current_block: SessionBlock | None = None
        current_message_count = 0
        settings = get_settings()

        for message in messages:
            embedding = embedding_by_message.get(message.id)
            agent_id = (embedding.agent_id if embedding and embedding.agent_id else "orchestrator")
            derived_from_recall = bool(
                (embedding.derived_from_recall if embedding else False)
                or (message.role == "user" and is_continuation_prompt(message.content))
            )
            source_status = embedding.source_status if embedding else "final"
            decision = classify_memory_content(
                role=message.role,
                content=message.content,
                source_status=source_status,
                derived_from_recall=derived_from_recall,
            )
            should_update_block = decision.answer_bearing or (
                message.role == "user"
                and decision.indexable
                and decision.content_kind == "query"
            )
            if not should_update_block:
                continue

            token_count = estimate_token_count(message.content)
            category = self._facade._infer_category(message.content, agent_id=agent_id, role=message.role)
            title = self._facade._derive_title(message.content, category=category)
            tags = self._facade._extract_tags(message.content, category=category)
            vector = None
            if embedding is not None and embedding.indexable:
                vector = embedding.embedding

            should_rotate = False
            if current_block is not None:
                similarity = self._facade._cosine_similarity(vector, current_block.embedding)
                should_rotate = (
                    current_message_count >= settings.memory_block_max_messages
                    or (current_block.token_count + token_count) > settings.memory_block_max_tokens
                    or (
                        current_block.category != category
                        and similarity < settings.memory_block_topic_shift_threshold
                    )
                )

            if current_block is None or should_rotate:
                if current_block is not None:
                    current_block.closed_at = current_block.updated_at
                sequence += 1
                current_message_count = 0
                current_block = SessionBlock(
                    session_id=session_id,
                    sequence=sequence,
                    category=category,
                    title=title,
                    summary_md=self._facade._build_summary(
                        title=title,
                        category=category,
                        excerpts=[message.content],
                    ),
                    content_excerpt=self._facade._build_excerpt("", message.content),
                    topic_tags=tags,
                    message_start_id=message.id,
                    message_end_id=message.id,
                    token_count=token_count,
                    confidence=0.85 if agent_id == "orchestrator" else 0.7,
                    source="orchestrator" if agent_id == "orchestrator" else "inferred",
                    indexable=decision.indexable,
                    content_kind=decision.content_kind,
                    quality_flags=list(decision.quality_flags),
                    source_status=source_status,
                    derived_from_recall=decision.derived_from_recall,
                    embedding=vector,
                )
                db.add(current_block)
                rebuilt_count += 1
            else:
                current_block.message_end_id = message.id
                current_block.token_count += token_count
                current_block.topic_tags = list(dict.fromkeys([*(current_block.topic_tags or []), *tags]))[:8]
                current_block.content_excerpt = self._facade._build_excerpt(current_block.content_excerpt, message.content)
                current_block.summary_md = self._facade._build_summary(
                    title=current_block.title,
                    category=current_block.category,
                    excerpts=current_block.content_excerpt.split(" | "),
                )
                current_block.content_kind = decision.content_kind
                current_block.quality_flags = list(
                    dict.fromkeys([*(current_block.quality_flags or []), *decision.quality_flags])
                )
                current_block.source_status = source_status
                current_block.derived_from_recall = bool(
                    current_block.derived_from_recall or decision.derived_from_recall
                )
                if current_block.embedding is None and vector is not None:
                    current_block.embedding = vector

            current_message_count += 1

        await db.flush()
        return len(existing_ids), rebuilt_count
