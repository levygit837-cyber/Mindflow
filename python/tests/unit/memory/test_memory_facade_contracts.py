"""TDD tests for memory facade public surface — Phase 1.

Verifies:
- New schema contracts exist and are constructible.
- MemoryFacade is returned by get_memory_service().
- Facade exposes the three canonical methods with correct signatures.
- workers/system/interfaces MemoryRecorder aligns with MemoryPersistResult.
- RetrievedContext backward-compat alias is still importable.
"""

from __future__ import annotations

import inspect

# ---------------------------------------------------------------------------
# Schema contract tests
# ---------------------------------------------------------------------------


def test_memory_persist_result_importable():
    from mindflow_backend.schemas.memory.contracts import MemoryPersistResult

    result = MemoryPersistResult()
    assert result.was_deduplicated is False
    assert result.token_count == 0
    assert result.indexable is True
    assert result.skipped_reasons == []
    assert result.chat_stored is False
    assert result.embedding_stored is False
    assert result.agent_event_stored is False
    assert result.block_updated is False
    assert result.degraded_reason is None


def test_memory_persist_result_fields():
    from mindflow_backend.schemas.memory.contracts import MemoryPersistResult

    r = MemoryPersistResult(
        embedding_id="emb-123",
        event_id=42,
        chat_stored=True,
        embedding_stored=True,
        agent_event_stored=True,
        block_updated=True,
        degraded_reason="embedding_backend_unavailable",
        indexable=False,
        skipped_reasons=["partial_stream"],
        was_deduplicated=True,
        token_count=17,
    )
    assert r.embedding_id == "emb-123"
    assert r.event_id == 42
    assert r.chat_stored is True
    assert r.embedding_stored is True
    assert r.agent_event_stored is True
    assert r.block_updated is True
    assert r.degraded_reason == "embedding_backend_unavailable"
    assert r.indexable is False
    assert r.skipped_reasons == ["partial_stream"]
    assert r.was_deduplicated is True
    assert r.token_count == 17


def test_memory_recall_request_importable():
    from mindflow_backend.schemas.memory.contracts import MemoryRecallRequest

    req = MemoryRecallRequest(session_id="s1", agent_id="a1", query="what happened?")
    assert req.session_id == "s1"
    assert req.agent_id == "a1"
    assert req.top_k == 4
    assert req.cross_session is False
    assert req.include_messages is True
    assert req.include_blocks is True
    assert req.top_k_messages == 4
    assert req.top_k_blocks == 2
    assert req.category_filters == []


def test_memory_recall_request_accepts_max_results_alias():
    from mindflow_backend.schemas.memory.contracts import MemoryRecallRequest

    req = MemoryRecallRequest(
        session_id="s1",
        agent_id="a1",
        query="what happened?",
        max_results=4,
    )

    assert req.top_k == 4


def test_memory_recall_request_accepts_block_controls():
    from mindflow_backend.schemas.memory.contracts import MemoryRecallRequest

    req = MemoryRecallRequest(
        session_id="s1",
        agent_id="a1",
        query="retome as decisoes",
        include_messages=False,
        include_blocks=True,
        top_k_messages=1,
        top_k_blocks=3,
        category_filters=["decision"],
        exclude_session_id="s0",
    )

    assert req.include_messages is False
    assert req.include_blocks is True
    assert req.top_k_messages == 1
    assert req.top_k_blocks == 3
    assert req.category_filters == ["decision"]
    assert req.exclude_session_id == "s0"


def test_memory_recall_response_importable():
    from mindflow_backend.schemas.memory.contracts import MemoryRecallResponse

    resp = MemoryRecallResponse(context="some context")
    assert resp.context == "some context"
    assert resp.references == []
    assert resp.hit_count == 0


def test_memory_recall_response_exposes_content_alias_and_best_score():
    from mindflow_backend.schemas.memory.contracts import MemoryRecallResponse

    resp = MemoryRecallResponse(
        context="some context",
        hit_count=1,
        hits=[{"reference": "event:1", "score": 0.8, "final_score": 0.84, "content": "remembered detail"}],
        best_score=0.8,
        grounding_recommended=True,
        filtered_hits_count=2,
    )

    assert resp.content == "some context"
    assert resp.best_score == 0.8
    assert resp.grounding_recommended is True
    assert resp.filtered_hits_count == 2
    assert len(resp.hits) == 1
    assert resp.references == ["event:1"]


def test_memory_recall_response_supports_session_block_hits():
    from mindflow_backend.schemas.memory.contracts import MemoryRecallResponse

    resp = MemoryRecallResponse(
        hits=[
            {
                "source_type": "session_block",
                "source_id": 9,
                "reference": "session_block:9",
                "score": 0.91,
                "final_score": 1.01,
                "category": "decision",
                "title": "Memory pipeline decisions",
                "summary_md": "Decidimos usar Ollama com nomic-embed-text-v2-moe.",
                "content_excerpt": "Persistencia em session_embeddings e session_blocks.",
                "topic_tags": ["memory", "ollama"],
                "content_kind": "answer",
                "answer_bearing": True,
            }
        ]
    )

    assert resp.hit_count == 1
    assert resp.best_score == 0.91
    assert resp.references == ["session_block:9"]
    assert resp.hits[0].final_score == 1.01
    assert resp.hits[0].answer_bearing is True


def test_agent_memory_snapshot_importable():
    from mindflow_backend.schemas.memory.contracts import AgentMemorySnapshot

    snap = AgentMemorySnapshot(session_id="s1", agent_id="a1")
    assert snap.event_count == 0
    assert snap.window_count == 0
    assert snap.total_tokens == 0
    assert snap.context_summary == ""


def test_session_block_schema_importable():
    from mindflow_backend.schemas.memory.contracts import SessionBlockSchema

    block = SessionBlockSchema(
        id=1,
        session_id="s1",
        sequence=1,
        category="decision",
        title="Memory decisions",
        summary_md="Definimos a estrategia de embeddings.",
        content_excerpt="Ollama + session blocks.",
        topic_tags=["memory", "ollama"],
        message_start_id=10,
        message_end_id=12,
        token_count=320,
        confidence=0.82,
        source="inferred",
        indexable=True,
        content_kind="answer",
        source_status="final",
        derived_from_recall=False,
    )

    assert block.sequence == 1
    assert block.category == "decision"
    assert block.topic_tags == ["memory", "ollama"]
    assert block.indexable is True
    assert block.content_kind == "answer"


def test_memory_recall_hit_exposes_grounding_metadata():
    from mindflow_backend.schemas.memory.contracts import MemoryRecallHit

    hit = MemoryRecallHit(
        source_type="session_message",
        source_id=1,
        content_excerpt="O marcador salvo foi MEMORIA-123",
        score=0.8,
        final_score=0.94,
        content_kind="answer",
        quality_flags=[],
        source_status="final",
        answer_bearing=True,
    )

    assert hit.final_score == 0.94
    assert hit.content_kind == "answer"
    assert hit.source_status == "final"
    assert hit.answer_bearing is True


def test_all_new_contracts_in_all():
    from mindflow_backend.schemas.memory import contracts

    for name in (
        "MemoryPersistResult",
        "MemoryRecallRequest",
        "MemoryRecallResponse",
        "AgentMemorySnapshot",
        "SessionBlockSchema",
        "SessionBlockHit",
        "MemoryRecallHit",
    ):
        assert name in contracts.__all__, f"{name} missing from __all__"


# ---------------------------------------------------------------------------
# RetrievedContext backward-compat alias
# ---------------------------------------------------------------------------


def test_retrieved_context_still_importable():
    """RetrievedContext must remain importable from schemas.session.contracts."""
    from mindflow_backend.schemas.session.contracts import RetrievedContext

    assert RetrievedContext is not None


def test_retrieved_context_is_compat_alias():
    """RetrievedContext must now be a type alias pointing to MemoryRecallResponse."""
    from mindflow_backend.schemas.memory.contracts import MemoryRecallResponse
    from mindflow_backend.schemas.session import contracts as sc

    assert sc.RetrievedContext is MemoryRecallResponse


# ---------------------------------------------------------------------------
# interfaces/services/memory.py — facade interface
# ---------------------------------------------------------------------------


def test_memory_facade_interface_importable():
    from mindflow_backend.interfaces.services.memory import MemoryFacadeInterface

    assert MemoryFacadeInterface is not None


def test_memory_facade_interface_has_three_methods():
    from mindflow_backend.interfaces.services.memory import MemoryFacadeInterface

    for method in ("record_message", "recall", "get_agent_snapshot", "list_session_blocks"):
        assert hasattr(MemoryFacadeInterface, method), f"MemoryFacadeInterface missing {method}"


# ---------------------------------------------------------------------------
# workers/system/interfaces/memory.py — MemoryRecorder return type
# ---------------------------------------------------------------------------


def test_worker_memory_recorder_returns_persist_result():
    """MemoryRecorder.record_message return annotation must be MemoryPersistResult."""
    import typing

    from mindflow_backend.schemas.memory.contracts import MemoryPersistResult
    from mindflow_backend.workers.system.interfaces.memory import MemoryRecorder

    hints = typing.get_type_hints(MemoryRecorder.record_message)
    assert hints.get("return") is MemoryPersistResult


# ---------------------------------------------------------------------------
# get_memory_service() returns MemoryFacade
# ---------------------------------------------------------------------------


def test_get_memory_service_returns_facade():
    from mindflow_backend.memory import get_memory_service
    from mindflow_backend.memory.facade import MemoryFacade

    svc = get_memory_service()
    assert isinstance(svc, MemoryFacade)


def test_get_memory_service_returns_singleton():
    from mindflow_backend.memory import get_memory_service

    assert get_memory_service() is get_memory_service()


def test_facade_exposes_record_message():
    from mindflow_backend.memory.facade import MemoryFacade

    assert callable(MemoryFacade.record_message)
    sig = inspect.signature(MemoryFacade.record_message)
    params = list(sig.parameters)
    assert "db" in params
    assert "session_id" in params
    assert "agent_id" in params
    assert "role" in params
    assert "content" in params
    assert "source_message_id" in params
    assert "idempotency_key" in params
    assert "source_status" in params
    assert "derived_from_recall" in params


def test_facade_exposes_recall():
    from mindflow_backend.memory.facade import MemoryFacade

    assert callable(MemoryFacade.recall)
    sig = inspect.signature(MemoryFacade.recall)
    assert "request" in sig.parameters


def test_facade_exposes_get_agent_snapshot():
    from mindflow_backend.memory.facade import MemoryFacade

    assert callable(MemoryFacade.get_agent_snapshot)
    sig = inspect.signature(MemoryFacade.get_agent_snapshot)
    params = list(sig.parameters)
    assert "session_id" in params
    assert "agent_id" in params
    assert "token_limit" in params


def test_facade_exposes_list_session_blocks():
    from mindflow_backend.memory.facade import MemoryFacade

    assert callable(MemoryFacade.list_session_blocks)
    sig = inspect.signature(MemoryFacade.list_session_blocks)
    params = list(sig.parameters)
    assert "session_id" in params
    assert "categories" in params
    assert "limit" in params
