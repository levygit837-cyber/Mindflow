"""Unit tests for Phase 3 routing: selector and adapter.

No real LLM calls, no DB, no feature-flag config needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import patch

import pytest

from mindflow_backend.query.selector import (
    QueryStrategy,
    build_strategy_context,
    select_strategy,
)

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


@dataclass
class _FakePayload:
    message: str = "hello"
    orchestrate: bool = False
    agent_type: str | None = None
    provider: str | None = None
    model: str | None = None
    folder_path: str | None = None


# ---------------------------------------------------------------------------
# select_strategy
# ---------------------------------------------------------------------------


class TestSelectStrategy:
    def test_orchestrate_flag_maps_to_decomposition(self):
        payload = _FakePayload(orchestrate=True)
        assert select_strategy(payload) is QueryStrategy.DECOMPOSITION

    def test_agent_type_maps_to_direct(self):
        payload = _FakePayload(agent_type="coder")
        assert select_strategy(payload) is QueryStrategy.DIRECT

    def test_no_flags_maps_to_react(self):
        payload = _FakePayload()
        assert select_strategy(payload) is QueryStrategy.REACT

    def test_analyst_with_folder_maps_to_decomposition(self):
        payload = _FakePayload(agent_type="analyst", folder_path="/project")
        assert select_strategy(payload) is QueryStrategy.DECOMPOSITION

    def test_analyst_with_keyword_maps_to_decomposition(self):
        payload = _FakePayload(agent_type="analyst", message="Please review this code")
        assert select_strategy(payload) is QueryStrategy.DECOMPOSITION

    def test_strategy_override_env_var(self):
        class _FakeSettings:
            queryengine_strategy_override = "deep_work"
            default_provider = "anthropic"
            default_model = "claude-4"
            max_agent_iterations = 50
            max_deep_work_depth = 1000

        with patch(
            "mindflow_backend.query.selector.get_settings",
            return_value=_FakeSettings(),
        ):
            payload = _FakePayload(orchestrate=True)
            assert select_strategy(payload) is QueryStrategy.DEEP_WORK


# ---------------------------------------------------------------------------
# build_strategy_context
# ---------------------------------------------------------------------------


class TestBuildStrategyContext:
    def test_basic_context_fields(self):
        payload = _FakePayload(message="do stuff", provider="anthropic", model="claude-4")
        ctx = build_strategy_context(
            payload,
            session_id="sess-1",
            execution_id="exec-1",
            run_id="run-1",
        )
        assert ctx.message == "do stuff"
        assert ctx.session_id == "sess-1"
        assert ctx.execution_id == "exec-1"
        assert ctx.provider == "anthropic"
        assert ctx.model == "claude-4"
        assert ctx.metadata["run_id"] == "run-1"

    def test_metadata_merge(self):
        payload = _FakePayload()
        ctx = build_strategy_context(
            payload,
            session_id="s",
            metadata={"complexity_score": 0.8},
        )
        assert ctx.metadata["complexity_score"] == 0.8
        assert "orchestrate" in ctx.metadata

    def test_services_passthrough(self):
        payload = _FakePayload()
        fake_agent = object()
        ctx = build_strategy_context(
            payload,
            session_id="s",
            services={"agent": fake_agent},
        )
        assert ctx.services["agent"] is fake_agent

    def test_tools_default_to_empty_list(self):
        payload = _FakePayload()
        ctx = build_strategy_context(payload, session_id="s")
        assert ctx.tools == []


# ---------------------------------------------------------------------------
# adapt_strategy_events
# ---------------------------------------------------------------------------
from mindflow_backend.query.adapter import adapt_strategy_events


class _FakeNormalizer:
    """Minimal normalizer stub that records calls and returns minimal StreamEvent."""

    def __init__(self):
        self.calls: list[dict] = []

    def _make_event(self, kind: str, **kwargs) -> Any:
        from dataclasses import dataclass as _dc

        @_dc
        class _Ev:
            type: str
            data: str = ""
            seq: int = 0
            id: str = ""
            mode: str = "messages"
            meta: Any = None

        self.calls.append({"kind": kind, **kwargs})
        return _Ev(type=kind, data=kwargs.get("data", kwargs.get("content", "")))

    def response_event(self, seq, *, data, run_id):
        return self._make_event("response", seq=seq, data=data)

    def tool_result_event(self, seq, *, tool_call_id, content, is_error, run_id):
        return self._make_event("tool_result", seq=seq, content=content, is_error=is_error)


async def _gen(*events):
    for ev in events:
        yield ev


@pytest.mark.asyncio
async def test_adapt_assistant_event_yields_response():
    norm = _FakeNormalizer()
    counter = [0]
    out = [
        ev
        async for ev in adapt_strategy_events(
            _gen({"type": "assistant", "content": "hello"}),
            provider="anthropic",
            model="m",
            run_id="r",
            session_id="s",
            normalizer=norm,
            counter=counter,
        )
    ]
    assert any(ev.type == "response" for ev in out)
    assert out[-1].type == "done"  # auto-appended


@pytest.mark.asyncio
async def test_adapt_done_event_not_doubled():
    norm = _FakeNormalizer()
    counter = [0]
    out = [
        ev
        async for ev in adapt_strategy_events(
            _gen({"type": "done"}),
            provider="anthropic",
            model="m",
            run_id="r",
            session_id="s",
            normalizer=norm,
            counter=counter,
        )
    ]
    done_events = [ev for ev in out if ev.type == "done"]
    assert len(done_events) == 1  # must not duplicate


@pytest.mark.asyncio
async def test_adapt_system_error_yields_error_event():
    norm = _FakeNormalizer()
    counter = [0]
    out = [
        ev
        async for ev in adapt_strategy_events(
            _gen({"type": "system", "content": "boom", "is_error": True}),
            provider="anthropic",
            model="m",
            run_id="r",
            session_id="s",
            normalizer=norm,
            counter=counter,
        )
    ]
    assert any(ev.type == "error" for ev in out)


@pytest.mark.asyncio
async def test_adapt_no_events_still_yields_done():
    norm = _FakeNormalizer()
    counter = [0]
    out = [
        ev
        async for ev in adapt_strategy_events(
            _gen(),
            provider="anthropic",
            model="m",
            run_id="r",
            session_id="s",
            normalizer=norm,
            counter=counter,
        )
    ]
    assert len(out) == 1
    assert out[0].type == "done"
