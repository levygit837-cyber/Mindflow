from types import SimpleNamespace

import pytest

from omnimind_backend.grpc.services.agent_runtime_service import AgentRuntimeServiceImpl
from omnimind_backend.schemas.agent import StreamEvent


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
