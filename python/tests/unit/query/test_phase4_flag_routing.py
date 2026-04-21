"""Phase 4 — integration test for UNIFIED_ENGINE_ENABLED routing gate.

Validates that when the flag is True, AgentRuntime.stream_chat delegates
to QueryEngine instead of calling the legacy _stream_chat_* paths.
The test uses deep mocking to avoid DB, Redis, RabbitMQ and LLM calls.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


@dataclass
class _FakePayload:
    message: str = "hello unified"
    orchestrate: bool = False
    agent_type: str | None = None
    provider: str | None = "anthropic"
    model: str | None = "claude-4"
    sessionId: str | None = None
    folder_path: str | None = None
    workspace_policy: Any = "auto"
    workspace_binding: Any = None
    execution_id: str | None = None


@dataclass
class _FakeExecution:
    id: str = "exec-1"
    status: str = "queued"
    root_execution_id: str | None = None
    current_stage: str | None = None
    progress: float | None = None
    metadata: dict = field(default_factory=dict)


class _FakeExecutionMemory:
    def __init__(self):
        self._exec = _FakeExecution()
        self.events: list = []
        self.statuses: list = []

    async def get_execution(self, eid):
        return self._exec

    async def start_execution(self, **kw):
        return self._exec

    async def mark_status(self, eid, status, **kw):
        self.statuses.append(status)

    async def append_event(self, eid, kind, data, **kw):
        self.events.append(kind)

    async def save_session_runtime_state(self, **kw):
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PATCHED_SETTINGS_BASE = {
    "unified_engine_enabled": False,
    "default_provider": "anthropic",
    "default_model": "claude-4",
    "queryengine_strategy_override": None,
    "memory_enabled": False,
    "working_path": "/tmp",
    "max_agent_iterations": 50,
    "max_deep_work_depth": 1000,
}


def _make_settings(**overrides):
    vals = {**_PATCHED_SETTINGS_BASE, **overrides}

    class S:
        pass

    for k, v in vals.items():
        setattr(S, k, v)

    def get_feature_flag(name, default=False):
        return default

    S.get_feature_flag = get_feature_flag
    return S()


async def _collect_stream(runtime, payload, session_id):
    events = []
    async for ev in runtime.stream_chat(payload, session_id):
        events.append(ev)
        if ev.type == "done":
            break
    return events


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_flag_false_calls_legacy_path():
    """With flag=False the legacy path (_stream_chat_legacy / _stream_chat_direct_agent
    / _stream_chat_orchestrated) should be called, not QueryEngine.execute."""
    from mindflow_backend.runtime.streaming.stream import AgentRuntime

    rt = AgentRuntime.__new__(AgentRuntime)
    rt._execution_memory = _FakeExecutionMemory()
    rt._memory_service = None
    rt._memory_publisher = None
    rt._worktree_service = None
    rt._orchestrator_graph = None
    rt._execution_cache = {}

    payload = _FakePayload()
    settings = _make_settings(unified_engine_enabled=False)

    legacy_called = []

    async def _fake_legacy(p, sid, rid=None):
        legacy_called.append(True)
        from mindflow_backend.schemas.chat.agent import StreamEvent, StreamEventMeta

        yield StreamEvent(
            id="e1",
            seq=1,
            type="done",
            mode="messages",
            data="",
            meta=StreamEventMeta(
                provider="anthropic", model="claude-4", runId="r", turnRunId="s"
            ),
        )

    with (
        patch("mindflow_backend.runtime.streaming.stream.get_settings", return_value=settings),
        patch("mindflow_backend.runtime.streaming.stream.is_continuation_prompt", return_value=False),
        patch.object(rt, "_prepare_workspace_binding", AsyncMock(return_value=None)),
        patch.object(rt, "_attach_hook_event_bridge", AsyncMock(return_value=None)),
        patch.object(rt, "handle_user_prompt", AsyncMock()),
        patch.object(rt, "_save_message_bg", AsyncMock()),
        patch.object(rt, "_stream_chat_legacy", _fake_legacy),
    ):
        events = await _collect_stream(rt, payload, "sess-1")

    assert legacy_called, "legacy path must be called when flag is False"
    assert any(ev.type == "done" for ev in events)


@pytest.mark.asyncio
async def test_flag_true_calls_query_engine():
    """With flag=True, QueryEngine.execute() is called and NOT the legacy paths."""
    from mindflow_backend.runtime.streaming.stream import AgentRuntime

    rt = AgentRuntime.__new__(AgentRuntime)
    rt._execution_memory = _FakeExecutionMemory()
    rt._memory_service = None
    rt._memory_publisher = None
    rt._worktree_service = None
    rt._orchestrator_graph = None
    rt._execution_cache = {}

    payload = _FakePayload()
    settings = _make_settings(unified_engine_enabled=True)

    legacy_called = []
    engine_execute_called = []

    from mindflow_backend.schemas.chat.agent import StreamEvent, StreamEventMeta

    def _make_done():
        return StreamEvent(
            id="e1",
            seq=1,
            type="done",
            mode="messages",
            data="",
            meta=StreamEventMeta(
                provider="anthropic", model="claude-4", runId="r", turnRunId="s"
            ),
        )

    async def _fake_adapt(events_gen, **kw):
        engine_execute_called.append(True)
        # drain the real generator (it won't yield because QueryEngine has no real agent)
        try:
            async for _ in events_gen:
                pass
        except Exception:
            pass
        yield _make_done()

    async def _fake_legacy(*a, **kw):
        legacy_called.append(True)
        yield _make_done()

    with (
        patch("mindflow_backend.runtime.streaming.stream.get_settings", return_value=settings),
        patch("mindflow_backend.runtime.streaming.stream.is_continuation_prompt", return_value=False),
        patch.object(rt, "_prepare_workspace_binding", AsyncMock(return_value=None)),
        patch.object(rt, "_attach_hook_event_bridge", AsyncMock(return_value=None)),
        patch.object(rt, "handle_user_prompt", AsyncMock()),
        patch.object(rt, "_save_message_bg", AsyncMock()),
        patch("mindflow_backend.runtime.streaming.stream._adapt_strategy_events", _fake_adapt),
        patch.object(rt, "_stream_chat_legacy", _fake_legacy),
    ):
        events = await _collect_stream(rt, payload, "sess-2")

    assert not legacy_called, "legacy path must NOT be called when flag is True"
    assert engine_execute_called, "QueryEngine adapter must be called when flag is True"
    assert any(ev.type == "done" for ev in events)
