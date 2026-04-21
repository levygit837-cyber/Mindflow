"""Unit tests for Phase 2 query/ layers: hooks, persistence, streaming.

All tests use fakes/stubs — no real DB, no real message bus, no real hook
handlers. The goal is to verify the pure-function contracts, not integration.
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# query/streaming
# ---------------------------------------------------------------------------
from mindflow_backend.query.streaming import (
    custom_event,
    done_event,
    error_event,
    next_seq,
)


class TestNextSeq:
    def test_increments_counter_and_returns_new_value(self):
        counter = [0]
        assert next_seq(counter) == 1
        assert next_seq(counter) == 2
        assert counter[0] == 2

    def test_is_independent_for_different_counter_objects(self):
        c1, c2 = [0], [10]
        next_seq(c1)
        assert c1[0] == 1
        assert c2[0] == 10


class TestStreamEventBuilders:
    def _counter(self):
        return [0]

    def test_error_event_type_and_seq(self):
        ev = error_event(
            exc=RuntimeError("boom"),
            counter=self._counter(),
            provider="anthropic",
            model="claude-4",
            run_id="r1",
            session_id="s1",
        )
        assert ev.type == "error"
        assert ev.seq == 1
        assert ev.id == "evt-1"
        assert "boom" in ev.data

    def test_done_event_type_and_empty_data(self):
        ev = done_event(
            counter=self._counter(),
            provider="anthropic",
            model="claude-4",
            run_id="r1",
            session_id="s1",
        )
        assert ev.type == "done"
        assert ev.data == ""
        assert ev.meta.provider == "anthropic"
        assert ev.meta.model == "claude-4"

    def test_custom_event_uses_provided_type(self):
        ev = custom_event(
            counter=self._counter(),
            run_id="r1",
            session_id="s1",
            event_type="orchestrator_thinking",
            data="analyzing...",
        )
        assert ev.type == "orchestrator_thinking"
        assert ev.data == "analyzing..."
        assert ev.mode == "custom"

    def test_custom_event_sets_agent_on_meta(self):
        ev = custom_event(
            counter=self._counter(),
            run_id="r1",
            session_id="s1",
            event_type="agent_delegation_start",
            agent="analyst",
        )
        assert ev.meta.agent == "analyst"

    def test_seq_increments_across_builder_calls(self):
        counter = [0]
        ev1 = done_event(counter=counter, provider="anthropic", model="m", run_id="r", session_id="s")
        ev2 = error_event(
            exc=Exception("x"),
            counter=counter,
            provider="anthropic",
            model="m",
            run_id="r",
            session_id="s",
        )
        assert ev1.seq == 1
        assert ev2.seq == 2


# ---------------------------------------------------------------------------
# query/persistence — snapshot_json
# ---------------------------------------------------------------------------
from mindflow_backend.query.persistence import snapshot_json


class TestSnapshotJson:
    def test_primitives_pass_through(self):
        assert snapshot_json(None) is None
        assert snapshot_json(42) == 42
        assert snapshot_json("hello") == "hello"
        assert snapshot_json(True) is True

    def test_list_is_recursed(self):
        assert snapshot_json([1, "two", None]) == [1, "two", None]

    def test_tuple_becomes_list(self):
        assert snapshot_json((1, 2, 3)) == [1, 2, 3]

    def test_dict_string_keys(self):
        result = snapshot_json({1: "a", "b": 2})
        assert result == {"1": "a", "b": 2}

    def test_model_dump_objects(self):
        class FakeModel:
            def model_dump(self, mode="python"):
                return {"x": 1}

        assert snapshot_json(FakeModel()) == {"x": 1}

    def test_enum_like_via_value_attr(self):
        class FakeEnum:
            value = "running"

        assert snapshot_json(FakeEnum()) == "running"

    def test_unknown_object_to_str(self):
        class Blob:
            def __str__(self):
                return "blob-repr"

        assert snapshot_json(Blob()) == "blob-repr"


# ---------------------------------------------------------------------------
# query/persistence — sync_session_runtime_state (no-op paths)
# ---------------------------------------------------------------------------
from mindflow_backend.query.persistence import sync_session_runtime_state


@pytest.mark.asyncio
async def test_sync_session_runtime_state_noop_without_memory():
    await sync_session_runtime_state(
        execution_memory=None,
        session_id="s",
        execution_id="e",
    )  # must not raise


@pytest.mark.asyncio
async def test_sync_session_runtime_state_noop_without_session_id():
    await sync_session_runtime_state(
        execution_memory=object(),
        session_id=None,
        execution_id="e",
    )  # must not raise


@pytest.mark.asyncio
async def test_sync_session_runtime_state_persists_state():
    from dataclasses import dataclass, field

    @dataclass
    class _FakeExec:
        id: str = "exec-1"
        root_execution_id: str | None = None
        status: str = "running"
        current_stage: str = "routing"
        progress: float = 0.5
        metadata: dict = field(default_factory=dict)
        created_at: str = "2026-01-01"
        updated_at: str | None = None

    class _FakeMemory:
        def __init__(self, exec_obj):
            self._exec = exec_obj
            self.saved = []

        async def get_execution(self, exec_id):
            return self._exec

        async def save_session_runtime_state(self, *, session_id, execution_id, state):
            self.saved.append({"session_id": session_id, "execution_id": execution_id, "state": state})

    mem = _FakeMemory(_FakeExec())
    await sync_session_runtime_state(
        execution_memory=mem,
        session_id="sess-42",
        execution_id="exec-1",
    )
    assert len(mem.saved) == 1
    saved = mem.saved[0]
    assert saved["session_id"] == "sess-42"
    ar = saved["state"]["agent_runtime"]
    assert ar["status"] == "running"
    assert ar["active"] is True
    assert ar["stage"] == "routing"


# ---------------------------------------------------------------------------
# query/persistence — start_execution (no-op / success paths)
# ---------------------------------------------------------------------------
from mindflow_backend.query.persistence import start_execution


@pytest.mark.asyncio
async def test_start_execution_returns_none_without_memory():
    class _FakePayload:
        message = "hi"
        orchestrate = False
        agent_type = None
        execution_id = None
        folder_path = None

    result = await start_execution(
        execution_memory=None,
        payload=_FakePayload(),
        session_id="s",
        run_id=None,
        provider="anthropic",
        model="claude-4",
        execution_mode="legacy",
    )
    assert result is None


@pytest.mark.asyncio
async def test_start_execution_calls_memory_start_execution():
    from dataclasses import dataclass

    @dataclass
    class _FakePayload:
        message: str = "task"
        orchestrate: bool = False
        agent_type: str | None = None
        execution_id: str | None = None
        folder_path: str | None = None

    class _FakeMemory:
        def __init__(self):
            self.calls = []

        async def start_execution(self, **kwargs):
            self.calls.append(kwargs)
            return object()

    mem = _FakeMemory()
    result = await start_execution(
        execution_memory=mem,
        payload=_FakePayload(),
        session_id="sess",
        run_id="run-1",
        provider="anthropic",
        model="claude-4",
        execution_mode="direct",
        execution_id="exec-99",
        status="running",
    )
    assert result is not None
    assert len(mem.calls) == 1
    call = mem.calls[0]
    assert call["session_id"] == "sess"
    assert call["run_id"] == "run-1"
    assert call["mode"] == "direct"
    assert call["provider"] == "anthropic"
    assert call["status"] == "running"


# ---------------------------------------------------------------------------
# query/persistence — snapshot_json recursion guard
# ---------------------------------------------------------------------------
from mindflow_backend.query.persistence import snapshot_json


class _SelfReferential:
    """Fake pydantic-like object that model_dump returns a reference to itself."""

    def model_dump(self, mode: str = "json"):
        return {"self": self}


def test_snapshot_json_recursion_guard():
    obj = _SelfReferential()
    result = snapshot_json(obj)
    # Must not raise RecursionError; should cap at max_depth.
    # Result is a nested dict chain ending in <max-depth-exceeded>.
    assert "<max-depth-exceeded>" in str(result)
    assert isinstance(result, dict)


def test_snapshot_json_max_depth_custom():
    nested = {}
    current = nested
    for _ in range(30):
        current["child"] = {}
        current = current["child"]
    result = snapshot_json(nested)
    # default max_depth=20, so should hit the cap
    assert "<max-depth-exceeded>" in str(result)
