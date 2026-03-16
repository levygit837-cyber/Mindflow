from types import SimpleNamespace

import pytest

from mindflow_backend.grpc.services.agent_runtime_service import AgentRuntimeServiceImpl
from mindflow_backend.schemas.agent import StreamEvent


@pytest.mark.asyncio
async def test_service_streamchat_handles_optional_fields_without_attribute_errors(monkeypatch) -> None:
    request = SimpleNamespace(
        message="oi",
        provider="vertexai",
        model="gemini-3-flash-preview",
        session_id="s1",
        run_id="r1",
    )

    svc = AgentRuntimeServiceImpl()

    async def _fake_stream_chat(*_args, **_kwargs):
        yield StreamEvent(
            id="evt-1",
            seq=1,
            type="response",
            mode="messages",
            data="ok",
            meta=None,
        )

    monkeypatch.setattr(svc.runtime, "stream_chat", _fake_stream_chat)

    events = [e async for e in svc.StreamChat(request, context=None)]
    assert events


@pytest.mark.asyncio
async def test_service_streamchat_preserves_folder_path(monkeypatch) -> None:
    request = SimpleNamespace(
        message="oi",
        provider="vertexai",
        model="gemini-3-flash-preview",
        session_id="s1",
        run_id="r1",
        folder_path="/repo",
    )

    svc = AgentRuntimeServiceImpl()
    captured = {}

    async def _fake_stream_chat(payload, *_args, **_kwargs):
        captured["folder_path"] = payload.folder_path
        yield StreamEvent(
            id="evt-1",
            seq=1,
            type="done",
            mode="messages",
            data="",
            meta=None,
        )

    monkeypatch.setattr(svc.runtime, "stream_chat", _fake_stream_chat)

    _ = [e async for e in svc.StreamChat(request, context=None)]
    assert captured["folder_path"] == "/repo"


@pytest.mark.asyncio
async def test_service_streamchat_yields_protobuf_events(monkeypatch) -> None:
    """StreamChat() must yield pb2.StreamEvent protobuf messages, not domain objects."""
    from mindflow_backend.schemas.chat.agent import StreamEvent as DomainStreamEvent

    request = SimpleNamespace(
        message="ping",
        provider="vertexai",
        model="gemini-flash",
        session_id="s1",
        run_id="r1",
    )

    svc = AgentRuntimeServiceImpl()

    async def _fake_stream_chat(*_args, **_kwargs):
        yield DomainStreamEvent(
            id="evt-1",
            seq=1,
            type="response",
            mode="messages",
            data="ok",
            meta={"runId": "r1"},
        )

    monkeypatch.setattr(svc.runtime, "stream_chat", _fake_stream_chat)

    events = [e async for e in svc.StreamChat(request, context=None)]
    assert len(events) == 1
    # The service must yield a protobuf message (has DESCRIPTOR attribute).
    assert hasattr(events[0], "DESCRIPTOR"), "Expected a protobuf message, got domain object"
    assert events[0].id == "evt-1"
