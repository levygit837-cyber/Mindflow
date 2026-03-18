"""Unit tests for Phase 4: adaptive recall policy.

Tests:
- OrchestratorDecision carries memory_recall with correct defaults
- MemoryIntegration shim exposes recall() / get_agent_snapshot()
- Adaptive recall: session-first → cross-session fallback when hits < 2 or best_score < 0.55
- Empty context block is never injected
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# OrchestratorDecision memory_recall defaults
# ---------------------------------------------------------------------------


def test_orchestrator_decision_has_memory_recall_field():
    from mindflow_backend.schemas.orchestration.orchestrator import OrchestratorDecision

    decision = OrchestratorDecision()
    assert hasattr(decision, "memory_recall"), "OrchestratorDecision must have memory_recall field"


def test_memory_recall_default_values():
    from mindflow_backend.schemas.orchestration.orchestrator import OrchestratorDecision

    d = OrchestratorDecision()
    mr = d.memory_recall
    assert mr.enabled is True
    assert mr.policy == "adaptive"
    assert mr.scope == "current_then_cross"
    assert mr.max_results == 4
    assert mr.top_k == 4
    assert mr.min_score == 0.35
    assert mr.fallback_score_threshold == 0.55
    assert mr.cross_session_fallback is True
    assert mr.cross_session_min_hits == 2
    assert mr.cross_session_min_score == 0.55


def test_memory_recall_can_be_overridden():
    from mindflow_backend.schemas.orchestration.orchestrator import OrchestratorDecision, MemoryRecallConfig

    d = OrchestratorDecision(
        memory_recall=MemoryRecallConfig(
            enabled=False,
            max_results=3,
            policy="session_only",
            scope="current_session",
        )
    )
    assert d.memory_recall.enabled is False
    assert d.memory_recall.top_k == 3
    assert d.memory_recall.max_results == 3
    assert d.memory_recall.policy == "session_only"
    assert d.memory_recall.scope == "current_session"


# ---------------------------------------------------------------------------
# MemoryIntegration shim types
# ---------------------------------------------------------------------------


def test_memory_integration_shim_exposes_required_types():
    from mindflow_backend.orchestrator import memory_integration as mi

    assert hasattr(mi, "MemoryPersistResult")
    assert hasattr(mi, "MemoryRecallRequest")
    assert hasattr(mi, "MemoryRecallResponse")
    assert hasattr(mi, "AgentMemorySnapshot")


def test_memory_recall_request_fields():
    from mindflow_backend.orchestrator.memory_integration import MemoryRecallRequest

    req = MemoryRecallRequest(session_id="s1", query="test query", agent_id="coder")
    assert req.session_id == "s1"
    assert req.query == "test query"
    assert req.agent_id == "coder"
    assert req.cross_session is False
    assert req.top_k == 4
    assert req.max_results == 4
    assert req.min_score == 0.35


def test_memory_recall_response_fields():
    from mindflow_backend.orchestrator.memory_integration import MemoryRecallResponse

    resp = MemoryRecallResponse(hits=[], best_score=0.0, fallback_used=False)
    assert resp.hits == []
    assert resp.best_score == 0.0
    assert resp.fallback_used is False
    assert resp.content == ""


def test_agent_memory_snapshot_fields():
    from mindflow_backend.orchestrator.memory_integration import AgentMemorySnapshot

    snap = AgentMemorySnapshot(session_id="s1", agent_id="coder", events=[], token_total=0)
    assert snap.session_id == "s1"
    assert snap.agent_id == "coder"
    assert snap.events == []
    assert snap.token_total == 0


# ---------------------------------------------------------------------------
# Adaptive recall: session-first, then cross-session fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recall_returns_session_hits_when_sufficient():
    """When session has ≥2 hits with best_score ≥ 0.55, no cross-session call is made."""
    from mindflow_backend.orchestrator.memory_integration import MemoryIntegration, MemoryRecallRequest

    mi = MemoryIntegration()

    session_hits = [
        {"content": "hit 1", "score": 0.8},
        {"content": "hit 2", "score": 0.7},
        {"content": "hit 3", "score": 0.6},
    ]

    cross_session_called = []

    async def fake_session_recall(*args, **kwargs):
        return session_hits

    async def fake_cross_recall(*args, **kwargs):
        cross_session_called.append(True)
        return []

    with patch.object(mi, "_recall_session", side_effect=fake_session_recall), \
         patch.object(mi, "_recall_cross_session", side_effect=fake_cross_recall):

        req = MemoryRecallRequest(session_id="s1", query="q", agent_id="coder")
        resp = await mi.recall(req)

    assert len(resp.hits) == 3
    assert resp.best_score == 0.8
    assert resp.crossed_session is False
    assert len(cross_session_called) == 0, "cross-session must NOT be called when session hits ≥ 2 and score ≥ 0.55"


@pytest.mark.asyncio
async def test_recall_falls_back_cross_session_when_too_few_hits():
    """When session has < 2 hits, cross-session fallback is triggered."""
    from mindflow_backend.orchestrator.memory_integration import MemoryIntegration, MemoryRecallRequest

    mi = MemoryIntegration()

    session_hits = [{"content": "one hit", "score": 0.9}]
    cross_hits = [{"content": "cross 1", "score": 0.6}, {"content": "cross 2", "score": 0.5}]

    async def fake_session_recall(*args, **kwargs):
        return session_hits

    async def fake_cross_recall(*args, **kwargs):
        return cross_hits

    with patch.object(mi, "_recall_session", side_effect=fake_session_recall), \
         patch.object(mi, "_recall_cross_session", side_effect=fake_cross_recall):

        req = MemoryRecallRequest(session_id="s1", query="q", agent_id="coder")
        resp = await mi.recall(req)

    assert resp.crossed_session is True
    assert len(resp.hits) == 2


@pytest.mark.asyncio
async def test_recall_falls_back_cross_session_when_score_below_threshold():
    """When session best_score < 0.55, cross-session fallback is triggered even with ≥2 hits."""
    from mindflow_backend.orchestrator.memory_integration import MemoryIntegration, MemoryRecallRequest

    mi = MemoryIntegration()

    session_hits = [
        {"content": "hit 1", "score": 0.4},
        {"content": "hit 2", "score": 0.3},
    ]
    cross_hits = [{"content": "cross strong", "score": 0.8}]

    async def fake_session_recall(*args, **kwargs):
        return session_hits

    async def fake_cross_recall(*args, **kwargs):
        return cross_hits

    with patch.object(mi, "_recall_session", side_effect=fake_session_recall), \
         patch.object(mi, "_recall_cross_session", side_effect=fake_cross_recall):

        req = MemoryRecallRequest(session_id="s1", query="q", agent_id="coder")
        resp = await mi.recall(req)

    assert resp.crossed_session is True


@pytest.mark.asyncio
async def test_recall_cross_session_true_executes_direct_cross_session_search():
    from mindflow_backend.orchestrator.memory_integration import MemoryIntegration, MemoryRecallRequest

    mi = MemoryIntegration()

    async def fake_session_recall(*args, **kwargs):
        raise AssertionError("session recall must not run for explicit cross-session requests")

    async def fake_cross_recall(*args, **kwargs):
        return [{"content": "cross hit", "score": 0.8, "session_id": "other"}]

    with patch.object(mi, "_recall_session", side_effect=fake_session_recall), \
         patch.object(mi, "_recall_cross_session", side_effect=fake_cross_recall):
        req = MemoryRecallRequest(
            session_id="s1",
            query="retome a sessão anterior",
            agent_id="coder",
            cross_session=True,
        )
        resp = await mi.recall(req)

    assert resp.crossed_session is True
    assert len(resp.hits) == 1


@pytest.mark.asyncio
async def test_recall_does_not_inject_empty_block():
    """When all recall paths return empty, context string must be empty (not a placeholder)."""
    from mindflow_backend.orchestrator.memory_integration import MemoryIntegration, MemoryRecallRequest

    mi = MemoryIntegration()

    async def fake_session_recall(*args, **kwargs):
        return []

    async def fake_cross_recall(*args, **kwargs):
        return []

    with patch.object(mi, "_recall_session", side_effect=fake_session_recall), \
         patch.object(mi, "_recall_cross_session", side_effect=fake_cross_recall):

        req = MemoryRecallRequest(session_id="s1", query="q", agent_id="coder")
        resp = await mi.recall(req)

    context = mi.format_context(resp)
    assert context.strip() == "", f"Expected empty context, got: {context!r}"


@pytest.mark.asyncio
async def test_recall_memory_helper_uses_canonical_facade_response():
    from mindflow_backend.orchestrator.memory_integration import recall_memory
    from mindflow_backend.schemas.memory.contracts import MemoryRecallResponse

    fake_service = MagicMock()
    fake_service.recall = AsyncMock(
        return_value=MemoryRecallResponse(
            context="Context for session s1:\n- remembered decision",
            hits=[{"content": "remembered decision", "score": 0.9}],
            best_score=0.9,
            fallback_used=False,
        )
    )

    with patch(
        "mindflow_backend.orchestrator.memory_integration.get_memory_service",
        return_value=fake_service,
    ):
        response = await recall_memory(
            session_id="s1",
            query="what did we decide?",
            agent_id="coder",
            limit=4,
            cross_session=False,
        )

    assert response.context.startswith("Context for session s1")
    assert response.best_score == 0.9
    fake_service.recall.assert_awaited_once()


@pytest.mark.asyncio
async def test_simple_flow_retrieve_uses_canonical_facade():
    """_retrieve_memory_context in simple_flow must call SessionMemoryService, not the SQLite path."""
    from mindflow_backend.graphs.implementations.orchestrator.simple_flow import SimpleOrchestratorGraph

    graph = SimpleOrchestratorGraph()

    # Patch the shim's recall method (the one simple_flow calls through memory_integration)
    recall_calls = []

    async def fake_recall(request):
        recall_calls.append(request)
        from mindflow_backend.orchestrator.memory_integration import MemoryRecallResponse
        return MemoryRecallResponse(hits=[], best_score=0.0, crossed_session=False)

    with patch(
        "mindflow_backend.orchestrator.memory_integration.MemoryIntegration.recall",
        side_effect=fake_recall,
    ):
        result = await graph._retrieve_memory_context(
            query="test query",
            session_id="session-123",
            agent_id="coder",
        )

    # _retrieve_memory_context must return a dict with 'context' key
    assert isinstance(result, dict)
    assert "context" in result
    # Empty hits → context must be empty
    assert result["context"].strip() == ""
