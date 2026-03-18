"""Live GitNexus repository-analysis tests.

These tests make real calls against the current repository's GitNexus index and,
optionally, a real Analyst runtime invocation that should inspect this same
repository with GitNexus-first behavior.

Run with::

    RUN_LIVE_GITNEXUS_REPO_TESTS=1 pytest tests/live/test_gitnexus_repo_analysis_live.py -v -s
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from mindflow_backend.agents._registry import get_registry, register_all_specialists
from mindflow_backend.agents.tools.code.gitnexus import (
    GitNexusContextTool,
    GitNexusImpactTool,
    GitNexusQueryTool,
    GitNexusStatusTool,
)
from mindflow_backend.runtime.stream import AgentRuntime
from mindflow_backend.schemas.chat.agent import AgentChatRequest

REPO_ROOT = Path(__file__).resolve().parents[3]
STREAMING_RUNTIME_FILE = "python/mindflow_backend/runtime/streaming/stream.py"
AGENT_RUNTIME_UID = f"Class:{STREAMING_RUNTIME_FILE}:AgentRuntime"


def _live_enabled() -> bool:
    return os.getenv("RUN_LIVE_GITNEXUS_REPO_TESTS", "").strip() == "1"


def _configure_tool(tool) -> None:
    tool.root_dir = str(REPO_ROOT)


pytestmark = pytest.mark.skipif(
    not _live_enabled(),
    reason="Set RUN_LIVE_GITNEXUS_REPO_TESTS=1 to run live GitNexus repository-analysis tests",
)


@pytest.mark.asyncio
async def test_live_gitnexus_status_and_query_against_current_repo() -> None:
    status_tool = GitNexusStatusTool()
    _configure_tool(status_tool)

    status_result = await status_tool.execute()

    assert status_result["success"] is True, status_result
    assert status_result["repo"]["name"], status_result
    assert status_result["gitnexus_status"]["state"] in {"up_to_date", "indexed"}, status_result

    repo_path = status_result["repo"]["path"] or status_result["gitnexus_status"]["repository_path"]
    assert repo_path is not None, status_result
    assert Path(repo_path).resolve() == REPO_ROOT

    query_tool = GitNexusQueryTool()
    _configure_tool(query_tool)

    query_result = await query_tool.execute(
        query="AgentRuntime stream_chat notifier tool_call",
        goal="find runtime notifier handling",
        limit=5,
    )

    assert query_result["success"] is True, query_result
    definitions = query_result["result"].get("definitions", [])
    assert any(item.get("name") == "AgentRuntime" for item in definitions), query_result
    assert any(item.get("filePath") == STREAMING_RUNTIME_FILE for item in definitions), query_result


@pytest.mark.asyncio
async def test_live_gitnexus_context_and_impact_for_agent_runtime() -> None:
    context_tool = GitNexusContextTool()
    _configure_tool(context_tool)

    context_result = await context_tool.execute(
        name="AgentRuntime",
        file_path=STREAMING_RUNTIME_FILE,
    )

    assert context_result["success"] is True, context_result
    assert context_result["result"]["status"] == "found", context_result
    assert context_result["result"]["symbol"]["uid"] == AGENT_RUNTIME_UID, context_result
    assert context_result["result"]["symbol"]["filePath"] == STREAMING_RUNTIME_FILE, context_result

    incoming_calls = context_result["result"].get("incoming", {}).get("calls", [])
    assert any(
        call.get("filePath") == "python/mindflow_backend/services/communication/agent_runtime_service.py"
        for call in incoming_calls
    ), context_result

    impact_tool = GitNexusImpactTool()
    _configure_tool(impact_tool)

    impact_result = await impact_tool.execute(
        target="AgentRuntime",
        depth=2,
        include_tests=True,
    )

    assert impact_result["success"] is True, impact_result
    assert "error" not in impact_result["result"], impact_result
    assert impact_result["result"]["target"]["name"] == "AgentRuntime", impact_result
    assert impact_result["result"]["target"]["filePath"] == STREAMING_RUNTIME_FILE, impact_result
    assert impact_result["result"]["impactedCount"] >= 1, impact_result


@pytest.mark.asyncio
async def test_live_analyst_uses_gitnexus_to_analyze_current_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(AgentRuntime, "_save_message_bg", AsyncMock(return_value=None))
    get_registry().clear()
    register_all_specialists()

    runtime = AgentRuntime()
    payload = AgentChatRequest(
        message=(
            "Analise este repositório local usando GitNexus primeiro. "
            "Responda objetivamente: em qual arquivo AgentRuntime trata tool_call/notifier, "
            "qual é o símbolo principal, e cite a ferramenta de análise usada."
        ),
        agent_type="analyst",
        folder_path=str(REPO_ROOT),
    )

    events = [
        event
        async for event in runtime.stream_chat(
            payload,
            session_id="live-gitnexus-session",
            run_id="live-gitnexus-run",
        )
    ]

    assert events, "Expected a streamed response from the live Analyst runtime"
    assert events[-1].type == "done", events[-1]
    assert not any(event.type == "error" for event in events), events

    tool_call_payloads = [json.loads(event.data) for event in events if event.type == "tool_call"]
    notifier_payloads = [json.loads(event.data) for event in events if event.type == "notifier"]
    response_text = "".join(event.data for event in events if event.type == "response")
    response_text_lower = response_text.lower()

    gitnexus_tool_calls = [
        payload
        for payload in tool_call_payloads
        if str(payload.get("name", "")).startswith("gitnexus_")
    ]
    assert gitnexus_tool_calls, tool_call_payloads
    assert any(
        str(payload.get("kind", "")).startswith("gitnexus_")
        for payload in notifier_payloads
    ), notifier_payloads
    assert "agentruntime" in response_text_lower, response_text
    assert (
        "stream.py" in response_text_lower
        or "runtime/streaming/stream.py" in response_text_lower
    ), response_text
