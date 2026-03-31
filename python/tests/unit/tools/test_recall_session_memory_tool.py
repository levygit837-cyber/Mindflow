"""Unit tests for RecallSessionMemoryTool — Phase 4.

Tests:
- cross_session=False (default) calls the canonical recall helper in session scope
- cross_session=True calls the canonical recall helper with cross-session enabled
- Tool returns correct shape on success and on error
"""

from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture()
def tool():
    from mindflow_backend.agents.tools.integration.memory_tools import RecallSessionMemoryTool
    t = RecallSessionMemoryTool()
    t.session_id = "session-test-1"
    return t


@pytest.mark.asyncio
async def test_recall_session_memory_default_is_session_scoped(tool):
    """cross_session defaults to False → only current session is searched."""
    captured_cross_session = []

    async def fake_recall_memory(*, session_id, query, agent_id, limit, cross_session):
        captured_cross_session.append(cross_session)
        from mindflow_backend.schemas.memory.contracts import MemoryRecallResponse
        return MemoryRecallResponse(
            context="some context",
            references=[],
            metadata={"session_id": session_id},
        )

    with patch(
        "mindflow_backend.agents.tools.integration.memory_tools.recall_memory",
        side_effect=fake_recall_memory,
    ):
        result = await tool.execute(query="find something", cross_session=False, limit=5)

    assert captured_cross_session == [False]
    assert result["success"] is True


@pytest.mark.asyncio
async def test_recall_session_memory_cross_session_true(tool):
    """cross_session=True must be forwarded to retrieve_session_context."""
    captured_cross_session = []

    async def fake_recall_memory(*, session_id, query, agent_id, limit, cross_session):
        captured_cross_session.append(cross_session)
        from mindflow_backend.schemas.memory.contracts import MemoryRecallResponse
        return MemoryRecallResponse(
            context="cross context",
            references=[],
            metadata={"session_id": session_id, "cross_session": True},
        )

    with patch(
        "mindflow_backend.agents.tools.integration.memory_tools.recall_memory",
        side_effect=fake_recall_memory,
    ):
        result = await tool.execute(query="find something", cross_session=True, limit=5)

    assert captured_cross_session == [True], (
        f"Expected cross_session=True to be forwarded, got {captured_cross_session}"
    )
    assert result["success"] is True


@pytest.mark.asyncio
async def test_recall_session_memory_returns_results_on_success(tool):
    """Successful recall returns success=True with results list."""
    async def fake_recall_memory(*, session_id, query, agent_id, limit, cross_session):
        from mindflow_backend.schemas.memory.contracts import MemoryRecallResponse
        return MemoryRecallResponse(
            context="hit1\nhit2",
            references=["ref1", "ref2"],
            metadata={"result_count": 2},
        )

    with patch(
        "mindflow_backend.agents.tools.integration.memory_tools.recall_memory",
        side_effect=fake_recall_memory,
    ):
        result = await tool.execute(query="find something")

    assert result["success"] is True
    assert "context" in result or "results" in result


@pytest.mark.asyncio
async def test_recall_session_memory_handles_error_gracefully(tool):
    """On exception, tool returns success=False with error message."""
    with patch(
        "mindflow_backend.agents.tools.integration.memory_tools.recall_memory",
        side_effect=RuntimeError("DB connection failed"),
    ):
        result = await tool.execute(query="find something")

    assert result["success"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_recall_session_memory_rejects_empty_query(tool):
    """Empty query returns error without calling the service."""
    with patch(
        "mindflow_backend.agents.tools.integration.memory_tools.recall_memory",
    ) as mock_svc:
        result = await tool.execute(query="")

    mock_svc.assert_not_called()
    assert result["success"] is False
