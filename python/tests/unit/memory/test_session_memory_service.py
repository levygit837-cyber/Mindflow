"""Write-path tests for session-first semantic memory."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from mindflow_backend.memory.facade import MemoryFacade
from mindflow_backend.memory.storage.models import (
    AgentMemoryEvent,
    Base,
    SessionBlock,
    SessionEmbedding,
)


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


@pytest.mark.asyncio
async def test_record_message_skips_zero_vector_persistence_when_embedding_fails() -> None:
    db = await _make_async_session()
    facade = MemoryFacade()

    fake_provider = AsyncMock()
    fake_provider.embed = AsyncMock(side_effect=RuntimeError("ollama unavailable"))
    fake_provider.dimension.return_value = 768
    fake_provider.backend.return_value = "ollama"

    with patch(
        "mindflow_backend.memory.shared.embeddings.factory.get_embedding_provider",
        return_value=fake_provider,
    ):
        result = await facade.record_message(
            db,
            session_id="sess-1",
            agent_id="orchestrator",
            role="user",
            content="Precisamos revisar a memoria semantica.",
            source_message_id=101,
            idempotency_key="memory:101",
        )

    assert result.embedding_stored is False
    assert result.agent_event_stored is True
    assert result.block_updated is True
    assert result.degraded_reason is not None

    embeddings = list((await db.execute(select(SessionEmbedding))).scalars())
    events = list((await db.execute(select(AgentMemoryEvent))).scalars())
    blocks = list((await db.execute(select(SessionBlock))).scalars())

    assert embeddings == []
    assert len(events) == 1
    assert len(blocks) == 1


@pytest.mark.asyncio
async def test_record_message_updates_session_block_and_persists_embedding() -> None:
    db = await _make_async_session()
    facade = MemoryFacade()

    fake_provider = AsyncMock()
    fake_provider.embed = AsyncMock(return_value=[0.1] * 768)
    fake_provider.dimension.return_value = 768
    fake_provider.backend.return_value = "ollama"

    with patch(
        "mindflow_backend.memory.shared.embeddings.factory.get_embedding_provider",
        return_value=fake_provider,
    ):
        first = await facade.record_message(
            db,
            session_id="sess-2",
            agent_id="orchestrator",
            role="user",
            content="Decidimos usar Ollama para embeddings locais.",
            source_message_id=201,
            idempotency_key="memory:201",
        )
        second = await facade.record_message(
            db,
            session_id="sess-2",
            agent_id="orchestrator",
            role="assistant",
            content="Tambem vamos recuperar blocos categoricos por decisao.",
            source_message_id=202,
            idempotency_key="memory:202",
        )

    assert first.embedding_stored is True
    assert second.block_updated is True

    blocks = list((await db.execute(select(SessionBlock).order_by(SessionBlock.sequence.asc()))).scalars())
    assert len(blocks) == 1
    assert blocks[0].category
    assert blocks[0].summary_md
    assert blocks[0].message_start_id == 201
    assert blocks[0].message_end_id == 202


@pytest.mark.asyncio
async def test_record_message_marks_continuation_prompt_without_creating_block() -> None:
    db = await _make_async_session()
    facade = MemoryFacade()

    fake_provider = AsyncMock()
    fake_provider.embed = AsyncMock(return_value=[0.1] * 768)
    fake_provider.dimension.return_value = 768
    fake_provider.backend.return_value = "ollama"

    with patch(
        "mindflow_backend.memory.shared.embeddings.factory.get_embedding_provider",
        return_value=fake_provider,
    ):
        result = await facade.record_message(
            db,
            session_id="sess-3",
            agent_id="orchestrator",
            role="user",
            content="Retome a sessão anterior e continue a implementação do recall.",
            source_message_id=301,
            idempotency_key="memory:301",
            source_status="final",
            derived_from_recall=True,
        )

    embeddings = list((await db.execute(select(SessionEmbedding))).scalars())
    blocks = list((await db.execute(select(SessionBlock))).scalars())

    assert result.embedding_stored is True
    assert result.block_updated is False
    assert result.indexable is True
    assert result.skipped_reasons == []
    assert len(embeddings) == 1
    assert embeddings[0].content_kind == "continuation_prompt"
    assert embeddings[0].derived_from_recall is True
    assert embeddings[0].indexable is True
    assert blocks == []


@pytest.mark.asyncio
async def test_record_message_skips_semantic_index_for_partial_assistant_response() -> None:
    db = await _make_async_session()
    facade = MemoryFacade()

    fake_provider = AsyncMock()
    fake_provider.embed = AsyncMock(return_value=[0.1] * 768)
    fake_provider.dimension.return_value = 768
    fake_provider.backend.return_value = "ollama"

    with patch(
        "mindflow_backend.memory.shared.embeddings.factory.get_embedding_provider",
        return_value=fake_provider,
    ):
        result = await facade.record_message(
            db,
            session_id="sess-4",
            agent_id="analyst",
            role="assistant",
            content="Estou consultando ferramentas para confirmar o marcador...",
            source_message_id=401,
            idempotency_key="memory:401",
            source_status="partial",
            derived_from_recall=True,
        )

    embeddings = list((await db.execute(select(SessionEmbedding))).scalars())
    events = list((await db.execute(select(AgentMemoryEvent))).scalars())
    blocks = list((await db.execute(select(SessionBlock))).scalars())

    assert result.agent_event_stored is True
    assert result.embedding_stored is False
    assert result.block_updated is False
    assert result.indexable is False
    assert "partial_stream" in result.skipped_reasons
    assert embeddings == []
    assert len(events) == 1
    assert blocks == []
