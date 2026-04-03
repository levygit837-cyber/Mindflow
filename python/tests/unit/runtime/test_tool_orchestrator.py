from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import pytest

from mindflow_backend.runtime.execution.tool_orchestrator import ToolOrchestrator


@dataclass
class _FakeStructuredTool:
    name: str
    handler: Any
    metadata: dict[str, Any] = field(default_factory=dict)

    async def ainvoke(self, tool_input: dict[str, Any]) -> Any:
        return await self.handler(tool_input)


@pytest.mark.asyncio
async def test_tool_orchestrator_runs_safe_batch_in_parallel_and_keeps_result_order() -> None:
    events: list[tuple[str, dict[str, Any]]] = []

    async def event_dispatcher(name: str, payload: dict[str, Any]) -> None:
        events.append((name, payload))

    async def slow_tool(_tool_input: dict[str, Any]) -> dict[str, str]:
        await asyncio.sleep(0.05)
        return {"tool": "slow"}

    async def fast_tool(_tool_input: dict[str, Any]) -> dict[str, str]:
        await asyncio.sleep(0.01)
        return {"tool": "fast"}

    orchestrator = ToolOrchestrator(
        lc_tools=[
            _FakeStructuredTool(
                name="slow_tool",
                handler=slow_tool,
                metadata={"is_concurrency_safe": True},
            ),
            _FakeStructuredTool(
                name="fast_tool",
                handler=fast_tool,
                metadata={"is_concurrency_safe": True},
            ),
        ],
        event_dispatcher=event_dispatcher,
        session_id="session-orchestrator",
        max_concurrent=5,
    )

    start = time.perf_counter()
    results = await orchestrator.execute_tool_calls(
        [
            {"id": "tool-1", "name": "slow_tool", "args": {}},
            {"id": "tool-2", "name": "fast_tool", "args": {}},
        ]
    )
    elapsed = time.perf_counter() - start

    assert elapsed < 0.09
    assert [result.tool_name for result in results] == ["slow_tool", "fast_tool"]
    assert ['slow"' in result.serialized_result for result in results] == [True, False]
    assert ['fast"' in result.serialized_result for result in results] == [False, True]
    assert [name for name, _payload in events if name == "tool_call"] == [
        "tool_call",
        "tool_call",
    ]
    assert [
        payload["tool"]
        for name, payload in events
        if name == "tool_call"
    ] == ["slow_tool", "fast_tool"]


@pytest.mark.asyncio
async def test_tool_orchestrator_does_not_parallelize_across_unsafe_boundaries() -> None:
    timeline: list[str] = []

    async def safe_tool(tool_input: dict[str, Any]) -> dict[str, str]:
        timeline.append(f"{tool_input['name']}:start")
        await asyncio.sleep(0.01)
        timeline.append(f"{tool_input['name']}:end")
        return {"tool": tool_input["name"]}

    async def unsafe_tool(tool_input: dict[str, Any]) -> dict[str, str]:
        timeline.append(f"{tool_input['name']}:start")
        await asyncio.sleep(0.01)
        timeline.append(f"{tool_input['name']}:end")
        return {"tool": tool_input["name"]}

    orchestrator = ToolOrchestrator(
        lc_tools=[
            _FakeStructuredTool(
                name="safe_tool",
                handler=safe_tool,
                metadata={"is_concurrency_safe": True},
            ),
            _FakeStructuredTool(
                name="unsafe_tool",
                handler=unsafe_tool,
                metadata={"is_concurrency_safe": False},
            ),
        ],
        session_id="session-batches",
    )

    await orchestrator.execute_tool_calls(
        [
            {"id": "tool-1", "name": "safe_tool", "args": {"name": "safe-1"}},
            {"id": "tool-2", "name": "unsafe_tool", "args": {"name": "unsafe"}},
            {"id": "tool-3", "name": "safe_tool", "args": {"name": "safe-2"}},
        ]
    )

    assert timeline == [
        "safe-1:start",
        "safe-1:end",
        "unsafe:start",
        "unsafe:end",
        "safe-2:start",
        "safe-2:end",
    ]


@pytest.mark.asyncio
async def test_tool_orchestrator_persists_large_batch_results_to_preview_files(tmp_path) -> None:
    large_payload = "A" * 130_000

    async def large_tool(_tool_input: dict[str, Any]) -> str:
        return large_payload

    orchestrator = ToolOrchestrator(
        lc_tools=[
            _FakeStructuredTool(
                name="large_one",
                handler=large_tool,
                metadata={"is_concurrency_safe": True, "max_result_size_chars": 200_000},
            ),
            _FakeStructuredTool(
                name="large_two",
                handler=large_tool,
                metadata={"is_concurrency_safe": True, "max_result_size_chars": 200_000},
            ),
        ],
        session_id="session-budget",
        result_store_dir=tmp_path,
        max_turn_result_chars=200_000,
    )

    results = await orchestrator.execute_tool_calls(
        [
            {"id": "tool-1", "name": "large_one", "args": {}},
            {"id": "tool-2", "name": "large_two", "args": {}},
        ]
    )

    assert any("Full output saved to:" in result.serialized_result for result in results)
    preview_paths = [
        result.persisted_output_path
        for result in results
        if result.persisted_output_path is not None
    ]
    assert preview_paths
    assert all(path.exists() for path in preview_paths)
