import asyncio
import json
import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

if "redis" not in sys.modules:
    redis_module = types.ModuleType("redis")
    redis_asyncio_module = types.ModuleType("redis.asyncio")
    redis_module.asyncio = redis_asyncio_module
    sys.modules["redis"] = redis_module
    sys.modules["redis.asyncio"] = redis_asyncio_module

import mindflow_backend.runtime.streaming.stream as runtime_stream_module
from mindflow_backend.hooks.event_broadcaster import (
    HookEventBroadcaster,
    HookExecutionEvent,
    HookExecutionState,
)
from mindflow_backend.runtime.streaming.stream import AgentRuntime
from mindflow_backend.schemas.agent import AgentChatRequest


class _DummyResponse:
    def __init__(self, content: str) -> None:
        self.content = content


class _DummyModel:
    async def ainvoke(self, _messages):
        return _DummyResponse("Here is a deterministic response payload for streaming validation.")

    async def astream(self, _messages):
        class ChunkWithMetadata:
            def __init__(self, content, metadata=None):
                self.content = content
                self.response_metadata = metadata or {}

        yield ChunkWithMetadata("", {"thought": "I am thinking about this"})
        yield ChunkWithMetadata("Here ")
        yield ChunkWithMetadata("is ")
        yield ChunkWithMetadata("a deterministic response payload for streaming validation.")


class _ChunkWithThinkingList:
    def __init__(self) -> None:
        self.content = [
            {"type": "thinking", "thinking": "reasoning summary"},
            {"type": "text", "text": "final answer"},
        ]


class _DummyModelWithThinkingList:
    async def astream(self, _messages):
        yield _ChunkWithThinkingList()


class _FakeExecutionMemory:
    def __init__(self) -> None:
        self.events: list[dict] = []
        self.executions: dict[str, dict] = {}

    async def mark_status(self, execution_id: str, status: str, **kwargs):
        record = self.executions.setdefault(
            execution_id,
            {"id": execution_id, "status": status, "current_stage": kwargs.get("stage")},
        )
        record["status"] = status
        record.update(kwargs)
        return SimpleNamespace(**record)

    async def append_event(self, execution_id: str, event_type: str, payload: dict | None = None, **kwargs):
        self.events.append(
            {
                "execution_id": execution_id,
                "event_type": event_type,
                "payload": payload or {},
                **kwargs,
            },
        )

    async def get_execution(self, execution_id: str):
        record = self.executions.get(execution_id)
        return SimpleNamespace(**record) if record else None



@pytest.mark.asyncio
async def test_stream_contract_has_ordered_seq_and_run_linkage(monkeypatch) -> None:
    monkeypatch.setattr("mindflow_backend.runtime.streaming.stream.db_session", MagicMock())
    monkeypatch.setattr(
        "mindflow_backend.runtime.streaming.stream.get_model_for_provider",
        lambda _provider, _model: _DummyModel(),
    )

    runtime = AgentRuntime()
    payload = AgentChatRequest(message="summarize this", provider="openai", model="stub")

    events = [event async for event in runtime.stream_chat(payload, session_id="session-1", run_id="run-1")]

    assert events
    filtered_events = [e for e in events if e.seq > 0 and e.seq < 999]
    assert [evt.seq for evt in filtered_events] == list(range(1, len(filtered_events) + 1))
    assert events[-1].type == "done"

    assert all(evt.meta is not None for evt in filtered_events)
    assert all(evt.meta and evt.meta.runId == "run-1" for evt in filtered_events)
    assert all(evt.meta and evt.meta.turnRunId == "session-1" for evt in filtered_events)

    response_events = [evt for evt in events if evt.type == "response"]
    assert response_events
    assert all(evt.meta and evt.meta.category is not None for evt in response_events)
    
    thought_events = [evt for evt in events if evt.type == "thought"]
    assert thought_events
    assert "I am thinking about this" in thought_events[0].data

    step_events = [evt for evt in events if evt.type == "agent_step"]
    assert step_events
    payload_data = json.loads(step_events[0].data)
    assert {"stepName", "detail", "action"}.issubset(set(payload_data.keys()))


@pytest.mark.asyncio
async def test_stream_contract_emits_tool_events_for_search(monkeypatch) -> None:
    monkeypatch.setattr(
        "mindflow_backend.runtime.streaming.stream.get_model_for_provider",
        lambda _provider, _model: _DummyModel(),
    )

    async def _fake_search(_query: str) -> str:
        return "fresh web context"

    monkeypatch.setattr("mindflow_backend.runtime.streaming.stream.search_web", _fake_search)

    runtime = AgentRuntime()
    payload = AgentChatRequest(message="search latest docs", provider="openai", model="stub")

    events = [event async for event in runtime.stream_chat(payload, session_id="session-2", run_id="run-2")]

    assert any(evt.type == "tool_call" for evt in events)
    assert any(evt.type == "tool_result" for evt in events)


@pytest.mark.asyncio
async def test_stream_contract_extracts_thought_and_response_from_list_content(monkeypatch) -> None:
    monkeypatch.setattr("mindflow_backend.runtime.streaming.stream.db_session", MagicMock())
    monkeypatch.setattr(
        "mindflow_backend.runtime.streaming.stream.get_model_for_provider",
        lambda _provider, _model: _DummyModelWithThinkingList(),
    )

    runtime = AgentRuntime()
    payload = AgentChatRequest(message="responda", provider="openai", model="stub")

    events = [event async for event in runtime.stream_chat(payload, session_id="session-3", run_id="run-3")]
    thought_events = [evt for evt in events if evt.type == "thought"]
    response_events = [evt for evt in events if evt.type == "response"]

    assert any("reasoning summary" in evt.data for evt in thought_events)
    assert any("final answer" in evt.data for evt in response_events)


@pytest.mark.asyncio
async def test_direct_analyst_with_folder_path_uses_structured_flow(monkeypatch) -> None:
    monkeypatch.setattr("mindflow_backend.runtime.streaming.stream.db_session", MagicMock())

    runtime = AgentRuntime()
    direct_called = False
    orchestrated_called = False

    async def _fake_direct(*_args, **_kwargs):
        nonlocal direct_called
        direct_called = True
        if False:
            yield None

    async def _fake_orchestrated(*_args, **_kwargs):
        nonlocal orchestrated_called
        orchestrated_called = True
        yield type(
            "Evt",
            (),
            {
                "id": "evt-1",
                "seq": 1,
                "type": "done",
                "mode": "messages",
                "data": "",
                "meta": None,
            },
        )()

    monkeypatch.setattr(runtime, "_stream_chat_direct_agent", _fake_direct)
    monkeypatch.setattr(runtime, "_stream_chat_orchestrated", _fake_orchestrated)
    monkeypatch.setattr(runtime, "_save_message_bg", AsyncMock())

    payload = AgentChatRequest(
        message="analise esta codebase",
        provider="openai",
        model="stub",
        agent_type="analyst",
        folder_path="/tmp/project",
    )

    _ = [event async for event in runtime.stream_chat(payload, session_id="session-4", run_id="run-4")]

    assert orchestrated_called is True
    assert direct_called is False


@pytest.mark.asyncio
async def test_direct_agent_uses_tool_capable_fallback_model_when_requested_model_cannot_bind_tools(monkeypatch) -> None:
    monkeypatch.setattr("mindflow_backend.runtime.streaming.stream.db_session", MagicMock())
    monkeypatch.setattr(runtime_stream_module, "get_settings", lambda: SimpleNamespace(default_provider="ollama", default_model="orch:latest"))
    monkeypatch.setattr(runtime_stream_module, "_load_history_messages", AsyncMock(return_value=[]))
    monkeypatch.setattr("mindflow_backend.agents._registry.get_agent", lambda _agent_type: SimpleNamespace(system_prompt="sys", sandbox="read_only", root_dir=None))
    monkeypatch.setattr("mindflow_backend.agents.tools.sandbox.MindFlowSandbox", lambda **_kwargs: object())

    class _FakeRegistry:
        def get_tools_for_agent(self, _agent):
            return ["tool-a"]

    monkeypatch.setattr("mindflow_backend.agents.tools.create_default_registry", lambda *_args, **_kwargs: _FakeRegistry())
    monkeypatch.setattr(
        "mindflow_backend.agents.tools.base.langchain_adapter.to_langchain_tools",
        lambda _tools: ["lc-tool"],
    )

    runtime = AgentRuntime()
    monkeypatch.setattr(runtime, "_save_message_bg", AsyncMock())
    monkeypatch.setattr(
        runtime_stream_module,
        "resolve_provider_model_for_tools",
        lambda provider, model, tools_required: ("ollama", "qwen3:8b"),
    )

    captured: dict[str, str] = {}

    class _FallbackAwareModel:
        def bind_tools(self, _tools, **_kwargs):
            return self

    monkeypatch.setattr(
        runtime_stream_module,
        "get_model_for_provider",
        lambda provider, model: captured.update({"provider": provider, "model": model}) or _FallbackAwareModel(),
    )

    async def _fake_tool_stream(**kwargs):
        normalizer = kwargs["normalizer"]
        counter = kwargs["counter"]
        run_id = kwargs["run_id"]
        agent_type = kwargs["agent_type"]
        yield normalizer.response_event(
            runtime._next_seq(counter),
            "fallback-ok",
            run_id=run_id,
            extra_meta={"agent": agent_type},
        )

    monkeypatch.setattr(runtime, "_stream_tool_aware_direct_agent", _fake_tool_stream)

    payload = AgentChatRequest(
        message="crie um projeto python funcional",
        provider="ollama",
        model="orch:latest",
        agent_type="coder",
        folder_path="/tmp/project",
    )

    events = [event async for event in runtime.stream_chat(payload, session_id="session-5", run_id="run-5")]

    assert captured == {"provider": "ollama", "model": "qwen3:8b"}


@pytest.mark.asyncio
async def test_stream_chat_calls_runtime_user_prompt_hook_once(monkeypatch) -> None:
    monkeypatch.setattr("mindflow_backend.runtime.streaming.stream.db_session", MagicMock())
    monkeypatch.setattr(
        "mindflow_backend.runtime.streaming.stream.get_model_for_provider",
        lambda _provider, _model: _DummyModel(),
    )

    runtime = AgentRuntime()
    runtime._save_message_bg = AsyncMock()
    runtime.handle_user_prompt = AsyncMock()

    payload = AgentChatRequest(message="hook me", provider="openai", model="stub")
    _ = [event async for event in runtime.stream_chat(payload, session_id="session-hook", run_id="run-hook")]

    runtime.handle_user_prompt.assert_awaited_once_with(
        session_id="session-hook",
        prompt="hook me",
    )


@pytest.mark.asyncio
async def test_stream_chat_bridges_hook_events_into_execution_events(monkeypatch) -> None:
    broadcaster = HookEventBroadcaster.get_instance()
    broadcaster._handlers.clear()
    broadcaster._pending_events.clear()

    monkeypatch.setattr("mindflow_backend.runtime.streaming.stream.db_session", MagicMock())

    runtime = AgentRuntime()
    fake_execution_memory = _FakeExecutionMemory()
    fake_execution_memory.executions["exec-hook"] = {
        "id": "exec-hook",
        "status": "running",
        "current_stage": "booting",
    }
    runtime._execution_memory = fake_execution_memory
    runtime._save_message_bg = AsyncMock()
    runtime._sync_session_runtime_state = AsyncMock()
    runtime._start_execution = AsyncMock(
        return_value=SimpleNamespace(
            id="exec-hook",
            root_execution_id="exec-hook",
            parent_execution_id=None,
            status="running",
            current_stage="booting",
        ),
    )

    async def _fake_handle_user_prompt(*, session_id: str, prompt: str, **kwargs) -> None:
        del prompt, kwargs
        await broadcaster.emit(
            HookExecutionEvent(
                state=HookExecutionState.STARTED,
                hook_id="hook-1",
                hook_name="prompt-hook",
                hook_event="UserPromptSubmit",
                session_id=session_id,
            ),
        )
        await broadcaster.emit(
            HookExecutionEvent(
                state=HookExecutionState.COMPLETED,
                hook_id="hook-1",
                hook_name="prompt-hook",
                hook_event="UserPromptSubmit",
                session_id=session_id,
                outcome="success",
            ),
        )

    async def _fake_legacy(*args, **kwargs):
        yield type(
            "Evt",
            (),
            {
                "id": "evt-response",
                "seq": 1,
                "type": "response",
                "mode": "messages",
                "data": "fallback-ok",
                "meta": None,
            },
        )()
        yield type(
            "Evt",
            (),
            {
                "id": "evt-done",
                "seq": 2,
                "type": "done",
                "mode": "messages",
                "data": "",
                "meta": None,
            },
        )()

    runtime.handle_user_prompt = _fake_handle_user_prompt
    runtime._stream_chat_legacy = _fake_legacy

    payload = AgentChatRequest(message="bridge hooks", provider="openai", model="stub")
    events = [event async for event in runtime.stream_chat(payload, session_id="session-hook-events", run_id="run-hook-events")]

    assert events[-1].type == "done"
    hook_events = [
        event
        for event in fake_execution_memory.events
        if event["event_type"] == "hook_execution"
    ]
    assert len(hook_events) == 2
    assert hook_events[0]["payload"]["hook_name"] == "prompt-hook"
    assert hook_events[1]["payload"]["hook_state"] == "completed"
    assert any(evt.type == "response" and "fallback-ok" in evt.data for evt in events)
    assert events[-1].type == "done"


@pytest.mark.asyncio
async def test_direct_coder_uses_augmented_ollama_runtime_prompt_for_qwen_tool_fallback(monkeypatch) -> None:
    from unittest.mock import AsyncMock, MagicMock

    monkeypatch.setattr("mindflow_backend.runtime.streaming.stream.db_session", MagicMock())
    monkeypatch.setattr(runtime_stream_module, "get_settings", lambda: SimpleNamespace(default_provider="ollama", default_model="orch:latest"))
    monkeypatch.setattr(runtime_stream_module, "_load_history_messages", AsyncMock(return_value=[]))
    monkeypatch.setattr("mindflow_backend.agents._registry.get_agent", lambda _agent_type: SimpleNamespace(system_prompt="full-coder-prompt", sandbox="read_only", root_dir=None))
    monkeypatch.setattr("mindflow_backend.agents.tools.sandbox.MindFlowSandbox", lambda **_kwargs: object())

    class _FakeRegistry:
        def get_tools_for_agent(self, _agent):
            return ["tool-a"]

    monkeypatch.setattr("mindflow_backend.agents.tools.create_default_registry", lambda *_args, **_kwargs: _FakeRegistry())
    monkeypatch.setattr(
        "mindflow_backend.agents.tools.base.langchain_adapter.to_langchain_tools",
        lambda _tools: ["lc-tool"],
    )
    monkeypatch.setattr(
        runtime_stream_module,
        "resolve_provider_model_for_tools",
        lambda provider, model, tools_required: ("ollama", "qwen3:8b"),
    )

    runtime = AgentRuntime()
    monkeypatch.setattr(runtime, "_save_message_bg", AsyncMock())

    captured_messages: dict[str, list] = {}

    class _Model:
        def bind_tools(self, _tools, **_kwargs):
            return self

    monkeypatch.setattr(runtime_stream_module, "get_model_for_provider", lambda *_args, **_kwargs: _Model())

    async def _fake_tool_stream(**kwargs):
        captured_messages["messages"] = kwargs["messages"]
        normalizer = kwargs["normalizer"]
        counter = kwargs["counter"]
        run_id = kwargs["run_id"]
        yield normalizer.response_event(runtime._next_seq(counter), "ok", run_id=run_id)

    monkeypatch.setattr(runtime, "_stream_tool_aware_direct_agent", _fake_tool_stream)

    payload = AgentChatRequest(
        message="crie hello.txt",
        provider="ollama",
        model="orch:latest",
        agent_type="coder",
    )

    _ = [event async for event in runtime.stream_chat(payload, session_id="session-6a", run_id="run-6a")]

    assert "full-coder-prompt" in captured_messages["messages"][0].content
    assert runtime_stream_module._OLLAMA_CODER_TOOL_RUNTIME_PROMPT in captured_messages["messages"][0].content


def test_ollama_coder_runtime_prompt_enforces_exact_cli_contract() -> None:
    prompt = runtime_stream_module._OLLAMA_CODER_TOOL_RUNTIME_PROMPT

    assert 'python app.py add "text"' in prompt
    assert "python app.py list" in prompt
    assert "python app.py done 1" in prompt
    assert "python -m unittest -q" in prompt
    assert "sys.executable" in prompt
    assert "integer task IDs starting at 1" in prompt


@pytest.mark.asyncio
async def test_stream_chat_emits_timeout_error_when_no_progress_arrives(monkeypatch) -> None:
    from unittest.mock import AsyncMock, MagicMock

    monkeypatch.setattr("mindflow_backend.runtime.streaming.stream.db_session", MagicMock())
    monkeypatch.setattr(
        runtime_stream_module,
        "get_settings",
        lambda: SimpleNamespace(
            default_provider="openai",
            default_model="stub",
            agent_stream_timeout_seconds=0.05,
            agent_stream_progress_heartbeat_seconds=0.01,
        ),
    )

    runtime = AgentRuntime()
    monkeypatch.setattr(runtime, "_save_message_bg", AsyncMock())

    async def _stalled_direct(*_args, **_kwargs):
        await asyncio.sleep(0.2)
        if False:
            yield None

    monkeypatch.setattr(runtime, "_stream_chat_direct_agent", _stalled_direct)

    payload = AgentChatRequest(message="continue", provider="openai", model="stub", agent_type="coder")

    events = [event async for event in runtime.stream_chat(payload, session_id="session-6", run_id="run-6")]

    assert any(evt.type == "agent_step" and "waiting" in evt.data.lower() for evt in events)
    assert any(evt.type == "error" and "timed out" in evt.data.lower() for evt in events)
    assert events[-1].type == "done"


@pytest.mark.asyncio
async def test_stream_chat_allows_longer_initial_wait_before_first_tool_progress(monkeypatch) -> None:
    from unittest.mock import AsyncMock, MagicMock

    monkeypatch.setattr("mindflow_backend.runtime.streaming.stream.db_session", MagicMock())
    monkeypatch.setattr(
        runtime_stream_module,
        "get_settings",
        lambda: SimpleNamespace(
            default_provider="openai",
            default_model="stub",
            agent_stream_timeout_seconds=0.05,
            agent_stream_initial_timeout_seconds=0.2,
            agent_stream_progress_heartbeat_seconds=0.01,
        ),
    )

    runtime = AgentRuntime()
    monkeypatch.setattr(runtime, "_save_message_bg", AsyncMock())

    async def _slow_first_progress(*_args, **_kwargs):
        normalizer = runtime_stream_module.AgentChatStreamNormalizer(
            provider="openai",
            model="stub",
            turn_run_id="session-7",
        )
        yield normalizer.step_event(
            1,
            run_id="run-7",
            step_name="Direct Agent: coder",
            detail="Executing directly with coder personality.",
            action="start",
            node="direct",
            node_category="RUNTIME",
            user_visible=True,
        )
        await asyncio.sleep(0.1)
        yield normalizer.tool_call_event(
            2,
            tool_call_id="tool-1",
            name="write_file",
            args={"file_path": "hello.txt"},
            run_id="run-7",
        )
        yield normalizer.response_event(3, "ok", run_id="run-7")
        yield runtime._done_event(
            counter=[3],
            provider="openai",
            model="stub",
            run_id="run-7",
            session_id="session-7",
        )

    monkeypatch.setattr(runtime, "_stream_chat_direct_agent", _slow_first_progress)

    payload = AgentChatRequest(message="continue", provider="openai", model="stub", agent_type="coder")

    events = [event async for event in runtime.stream_chat(payload, session_id="session-7", run_id="run-7")]

    assert any(evt.type == "tool_call" for evt in events)
    assert any(evt.type == "response" and evt.data == "ok" for evt in events)
    assert not any(evt.type == "error" and "timed out" in evt.data.lower() for evt in events)
    assert events[-1].type == "done"


@pytest.mark.asyncio
async def test_stream_chat_allows_longer_wait_between_tool_iterations(monkeypatch) -> None:
    from unittest.mock import AsyncMock, MagicMock

    monkeypatch.setattr("mindflow_backend.runtime.streaming.stream.db_session", MagicMock())
    monkeypatch.setattr(
        runtime_stream_module,
        "get_settings",
        lambda: SimpleNamespace(
            default_provider="openai",
            default_model="stub",
            agent_stream_timeout_seconds=0.05,
            agent_stream_initial_timeout_seconds=0.2,
            agent_stream_tool_progress_timeout_seconds=0.2,
            agent_stream_progress_heartbeat_seconds=0.01,
        ),
    )

    runtime = AgentRuntime()
    monkeypatch.setattr(runtime, "_save_message_bg", AsyncMock())

    async def _slow_after_tool_progress(*_args, **_kwargs):
        normalizer = runtime_stream_module.AgentChatStreamNormalizer(
            provider="openai",
            model="stub",
            turn_run_id="session-8",
        )
        yield normalizer.step_event(
            1,
            run_id="run-8",
            step_name="Direct Agent: coder",
            detail="Executing directly with coder personality.",
            action="start",
            node="direct",
            node_category="RUNTIME",
            user_visible=True,
        )
        yield normalizer.tool_call_event(
            2,
            tool_call_id="tool-1",
            name="write_file",
            args={"file_path": "hello.txt"},
            run_id="run-8",
        )
        await asyncio.sleep(0.1)
        yield normalizer.tool_result_event(
            3,
            tool_call_id="tool-1",
            name="write_file",
            result="ok",
            run_id="run-8",
        )
        yield runtime._done_event(
            counter=[3],
            provider="openai",
            model="stub",
            run_id="run-8",
            session_id="session-8",
        )

    monkeypatch.setattr(runtime, "_stream_chat_direct_agent", _slow_after_tool_progress)

    payload = AgentChatRequest(message="continue", provider="openai", model="stub", agent_type="coder")

    events = [event async for event in runtime.stream_chat(payload, session_id="session-8", run_id="run-8")]

    assert any(evt.type == "tool_call" for evt in events)
    assert any(evt.type == "tool_result" and evt.data for evt in events)
    assert not any(evt.type == "error" and "timed out" in evt.data.lower() for evt in events)
    assert events[-1].type == "done"
