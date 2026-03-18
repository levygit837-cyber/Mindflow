from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
import pytest

from mindflow_backend.memory.cleanup import SessionMemoryCleanupService
from mindflow_backend.memory.storage.models import Base, ChatMessage, ChatSession, SessionBlock, SessionEmbedding


class _AsyncSessionAdapter:
    def __init__(self, sync_session: Session) -> None:
        self._sync = sync_session

    def add(self, obj) -> None:
        self._sync.add(obj)

    async def flush(self) -> None:
        self._sync.flush()

    async def commit(self) -> None:
        self._sync.commit()

    async def execute(self, statement):
        return self._sync.execute(statement)


async def _make_async_session() -> _AsyncSessionAdapter:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    sync_session = Session(bind=engine)
    return _AsyncSessionAdapter(sync_session)


async def _seed_contaminated_session(db: _AsyncSessionAdapter) -> None:
    db.add(ChatSession(id="sess-cleanup", title="cleanup"))
    for message in (
        ChatMessage(id=1, session_id="sess-cleanup", role="user", content="Precisamos salvar o marcador correto."),
        ChatMessage(id=2, session_id="sess-cleanup", role="assistant", content="O marcador correto é MEMORIA-OMEGA-1779F714."),
        ChatMessage(
            id=3,
            session_id="sess-cleanup",
            role="user",
            content="Retome a sessão anterior e continue a implementação do recall.",
        ),
        ChatMessage(id=4, session_id="sess-cleanup", role="assistant", content="<marker>sess-live-memory-b</marker>"),
    ):
        db.add(message)

    for embedding in (
        SessionEmbedding(
            session_id="sess-cleanup",
            content="Precisamos salvar o marcador correto.",
            embedding=[0.1] * 768,
            source_message_id=1,
            idempotency_key="memory:1",
            role="user",
            agent_id="orchestrator",
            indexable=True,
            content_kind="query",
            quality_flags=[],
            source_status="final",
            derived_from_recall=False,
            session_metadata={},
        ),
        SessionEmbedding(
            session_id="sess-cleanup",
            content="O marcador correto é MEMORIA-OMEGA-1779F714.",
            embedding=[0.2] * 768,
            source_message_id=2,
            idempotency_key="memory:2",
            role="assistant",
            agent_id="orchestrator",
            indexable=True,
            content_kind="answer",
            quality_flags=[],
            source_status="final",
            derived_from_recall=False,
            session_metadata={},
        ),
        SessionEmbedding(
            session_id="sess-cleanup",
            content="Retome a sessão anterior e continue a implementação do recall.",
            embedding=[0.3] * 768,
            source_message_id=3,
            idempotency_key="memory:3",
            role="user",
            agent_id="orchestrator",
            indexable=True,
            content_kind="query",
            quality_flags=[],
            source_status="final",
            derived_from_recall=False,
            session_metadata={},
        ),
        SessionEmbedding(
            session_id="sess-cleanup",
            content="<marker>sess-live-memory-b</marker>",
            embedding=[0.4] * 768,
            source_message_id=4,
            idempotency_key="memory:4",
            role="assistant",
            agent_id="analyst",
            indexable=True,
            content_kind="answer",
            quality_flags=[],
            source_status="final",
            derived_from_recall=True,
            session_metadata={},
        ),
    ):
        db.add(embedding)

    db.add(
        SessionBlock(
            session_id="sess-cleanup",
            sequence=1,
            category="discussion",
            title="Contaminado",
            summary_md="Resumo contaminado com placeholder",
            content_excerpt="<marker>sess-live-memory-b</marker>",
            topic_tags=["placeholder"],
            message_start_id=3,
            message_end_id=4,
            token_count=15,
            confidence=0.1,
            source="inferred",
            indexable=True,
            content_kind="answer",
            quality_flags=[],
            source_status="final",
            derived_from_recall=True,
            embedding=[0.5] * 768,
        )
    )
    await db.commit()


@pytest.mark.asyncio
async def test_cleanup_service_reclassifies_embeddings_and_rebuilds_blocks() -> None:
    db = await _make_async_session()
    await _seed_contaminated_session(db)

    service = SessionMemoryCleanupService()
    report = await service.cleanup(db, session_id="sess-cleanup", rebuild_blocks=True)

    embeddings = list(
        (await db.execute(select(SessionEmbedding).order_by(SessionEmbedding.source_message_id.asc()))).scalars()
    )
    blocks = list((await db.execute(select(SessionBlock).order_by(SessionBlock.sequence.asc()))).scalars())

    assert report.sessions_processed == 1
    assert report.embeddings_reclassified >= 2
    assert report.embeddings_disabled == 1
    assert report.blocks_deleted == 1
    assert report.blocks_rebuilt == 1

    assert embeddings[2].content_kind == "continuation_prompt"
    assert embeddings[2].indexable is True
    assert embeddings[2].derived_from_recall is True

    assert embeddings[3].indexable is False
    assert embeddings[3].content_kind == "placeholder"
    assert "placeholder" in embeddings[3].quality_flags

    assert len(blocks) == 1
    assert blocks[0].message_start_id == 1
    assert blocks[0].message_end_id == 2
    assert "MEMORIA-OMEGA-1779F714" in blocks[0].summary_md
    assert "Retome a sessão anterior" not in blocks[0].content_excerpt
    assert "<marker>" not in blocks[0].content_excerpt
