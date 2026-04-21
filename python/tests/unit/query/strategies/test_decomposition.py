"""Unit tests for DecompositionStrategy.

These tests use a fake engine injected via ``services["decomposition_engine"]``
so the real Tasker/Scheduler/Resolver/Synthesizer wiring is not exercised here
(integration covered elsewhere).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from mindflow_backend.query.strategies import StrategyContext
from mindflow_backend.query.strategies.decomposition import DecompositionStrategy


@dataclass
class _FakeSynthesis:
    final_response: str


class _FakeDecompositionEngine:
    def __init__(self, result: dict | None = None, raises: Exception | None = None):
        self._result = result
        self._raises = raises
        self.calls: list[dict] = []

    async def execute(self, **kwargs: Any) -> dict:
        self.calls.append(kwargs)
        if self._raises is not None:
            raise self._raises
        return self._result or {
            "main_contract": None,
            "components": [1, 2, 3],
            "validated": [{"result": "a"}, {"result": "b"}],
            "synthesis": _FakeSynthesis(final_response="unified answer"),
        }


@pytest.mark.asyncio
async def test_decomposition_yields_start_assistant_and_final_events():
    engine = _FakeDecompositionEngine()
    ctx = StrategyContext(
        message="decompose this complex task",
        session_id="sess-42",
        provider="openai",
        model="gpt-4",
        services={"decomposition_engine": engine},
        metadata={"complexity_score": 0.8, "memory_context": "ctx"},
    )

    events = [ev async for ev in DecompositionStrategy().run(ctx)]

    kinds = [ev["type"] for ev in events]
    assert "system" in kinds  # start marker
    assert "assistant" in kinds
    assert events[-1]["type"] == "final"
    assert events[-1]["content"] == "unified answer"

    assistant = next(ev for ev in events if ev["type"] == "assistant")
    assert assistant["content"] == "unified answer"
    assert assistant["metadata"]["components_count"] == 3
    assert assistant["metadata"]["validated_count"] == 2


@pytest.mark.asyncio
async def test_decomposition_forwards_context_to_engine_execute():
    engine = _FakeDecompositionEngine()
    ctx = StrategyContext(
        message="payload",
        session_id="sess-9",
        provider="anthropic",
        model="claude-4",
        services={"decomposition_engine": engine},
        metadata={"complexity_score": 0.42, "memory_context": "memory-string"},
    )

    async for _ in DecompositionStrategy().run(ctx):
        pass

    assert len(engine.calls) == 1
    call = engine.calls[0]
    assert call == {
        "message": "payload",
        "session_id": "sess-9",
        "complexity_score": 0.42,
        "provider": "anthropic",
        "model": "claude-4",
        "memory_context": "memory-string",
    }


@pytest.mark.asyncio
async def test_decomposition_surfaces_engine_error_as_error_event():
    engine = _FakeDecompositionEngine(raises=RuntimeError("pipeline blew up"))
    ctx = StrategyContext(
        message="x",
        session_id="s",
        services={"decomposition_engine": engine},
    )

    events = [ev async for ev in DecompositionStrategy().run(ctx)]

    errors = [ev for ev in events if ev.get("is_error")]
    assert len(errors) == 1
    assert "pipeline blew up" in errors[0]["content"]
