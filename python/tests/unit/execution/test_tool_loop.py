from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import pytest

from mindflow_backend.execution.loops.tool_loop import ToolExecutionLoop


@dataclass
class _FakeStructuredTool:
    name: str
    delay: float
    result: str
    metadata: dict[str, Any] = field(default_factory=lambda: {"is_concurrency_safe": True})

    async def ainvoke(self, _tool_input: dict[str, Any]) -> str:
        await asyncio.sleep(self.delay)
        return self.result


class _FakeLoopLLM:
    def __init__(self) -> None:
        self.calls = 0

    async def ainvoke(self, _messages):
        self.calls += 1
        if self.calls == 1:
            return SimpleNamespace(
                content="",
                tool_calls=[
                    {"id": "call-1", "name": "slow_tool", "args": {}},
                    {"id": "call-2", "name": "fast_tool", "args": {}},
                ],
            )
        return SimpleNamespace(content="final text", tool_calls=[])


@pytest.mark.asyncio
async def test_tool_execution_loop_executes_safe_batch_in_parallel() -> None:
    tool_loop = ToolExecutionLoop(max_iterations=5, session_id="session-loop")

    start = time.perf_counter()
    result = await tool_loop.run(
        llm=_FakeLoopLLM(),
        messages=[{"role": "system", "content": "system"}],
        lc_tools=[
            _FakeStructuredTool("slow_tool", delay=0.05, result="slow"),
            _FakeStructuredTool("fast_tool", delay=0.01, result="fast"),
        ],
        stream=False,
    )
    elapsed = time.perf_counter() - start

    assert elapsed < 0.09
    assert result.final_response == "final text"
