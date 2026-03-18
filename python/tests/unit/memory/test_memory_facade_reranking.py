from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from mindflow_backend.memory.facade import MemoryFacade
from mindflow_backend.schemas.memory.contracts import MemoryRecallRequest


@asynccontextmanager
async def _fake_db_context():
    yield object()


def _message_hit(
    *,
    session_id: str,
    content: str,
    score: float,
    role: str = "assistant",
    content_kind: str = "answer",
    source_status: str = "final",
    quality_flags: list[str] | None = None,
    derived_from_recall: bool = False,
    source_id: int = 1,
):
    return SimpleNamespace(
        source_type="session_message",
        source_id=source_id,
        session_id=session_id,
        agent_id="analyst",
        role=role,
        content_excerpt=content,
        score=score,
        content_kind=content_kind,
        quality_flags=quality_flags or [],
        source_status=source_status,
        derived_from_recall=derived_from_recall,
    )


def _block_hit(
    *,
    session_id: str,
    content: str,
    score: float,
    source_id: int = 11,
):
    return SimpleNamespace(
        source_type="session_block",
        source_id=source_id,
        session_id=session_id,
        agent_id="orchestrator",
        role="assistant",
        content_excerpt=content,
        summary_md=content,
        title="Resumo do bloco",
        category="implementation",
        topic_tags=["memory"],
        score=score,
        content_kind="answer",
        quality_flags=[],
        source_status="final",
        derived_from_recall=False,
    )


@pytest.mark.asyncio
async def test_recall_filters_prompt_echo_and_limits_cross_session_per_session() -> None:
    facade = MemoryFacade()
    request = MemoryRecallRequest(
        session_id="sess-current",
        agent_id="orchestrator",
        query="Retome a sessão anterior e continue a implementação do recall.",
        cross_session=True,
        exclude_session_id="sess-current",
        top_k_messages=4,
        top_k_blocks=2,
    )

    message_hits = [
        _message_hit(
            session_id="sess-bad",
            content="Retome a sessão anterior e continue a implementação do recall.",
            score=0.99,
            role="user",
            content_kind="continuation_prompt",
            derived_from_recall=True,
            source_id=1,
        ),
        _message_hit(
            session_id="sess-good",
            content="O marcador correto é MEMORIA-OMEGA-1779F714.",
            score=0.82,
            source_id=2,
        ),
        _message_hit(
            session_id="sess-good",
            content="A sessão também definiu o uso de Ollama para embeddings.",
            score=0.8,
            source_id=3,
        ),
        _message_hit(
            session_id="sess-good",
            content="Outro detalhe da mesma sessão que deve ser penalizado.",
            score=0.79,
            source_id=4,
        ),
    ]
    block_hits = [_block_hit(session_id="sess-good", content="Resumo: usamos o marcador MEMORIA-OMEGA-1779F714.", score=0.76)]

    with patch("mindflow_backend.memory.facade._get_db_session_factory", return_value=_fake_db_context), \
         patch.object(facade, "_recall_message_hits", AsyncMock(return_value=message_hits)), \
         patch.object(facade, "_recall_block_hits", AsyncMock(return_value=block_hits)):
        response = await facade.recall(request)

    assert response.filtered_hits_count == 1
    assert response.grounding_recommended is True
    assert response.hits[0].source_type == "session_block"
    assert response.hits[0].final_score > response.hits[1].final_score
    assert all("Retome a sessão anterior" not in hit.content for hit in response.hits)
    assert sum(1 for hit in response.hits if hit.session_id == "sess-good") <= 2


@pytest.mark.asyncio
async def test_recall_penalizes_placeholder_hits() -> None:
    facade = MemoryFacade()
    request = MemoryRecallRequest(
        session_id="sess-current",
        agent_id="orchestrator",
        query="Qual marcador salvamos?",
        cross_session=True,
        exclude_session_id="sess-current",
        top_k_messages=3,
        top_k_blocks=0,
    )

    message_hits = [
        _message_hit(
            session_id="sess-bad",
            content="<marker>sess-live-memory-b</marker>",
            score=0.95,
            quality_flags=["placeholder"],
            content_kind="placeholder",
            source_status="final",
            source_id=1,
        ),
        _message_hit(
            session_id="sess-good",
            content="O marcador salvo foi MEMORIA-OMEGA-1779F714.",
            score=0.82,
            source_id=2,
        ),
    ]

    with patch("mindflow_backend.memory.facade._get_db_session_factory", return_value=_fake_db_context), \
         patch.object(facade, "_recall_message_hits", AsyncMock(return_value=message_hits)), \
         patch.object(facade, "_recall_block_hits", AsyncMock(return_value=[])):
        response = await facade.recall(request)

    assert response.hits[0].session_id == "sess-good"
    assert response.hits[0].final_score > response.hits[1].final_score
