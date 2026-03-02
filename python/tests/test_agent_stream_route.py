import sys
import types

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Keep import path stable when generated gRPC bindings are absent in test checkouts.
_pb2 = types.ModuleType("omnimind_backend.grpc.generated.omnimind_backend_pb2")
_pb2_grpc = types.ModuleType("omnimind_backend.grpc.generated.omnimind_backend_pb2_grpc")
_pb2_grpc.AgentRuntimeServiceServicer = type("AgentRuntimeServiceServicer", (), {})
sys.modules.setdefault("omnimind_backend.grpc.generated.omnimind_backend_pb2", _pb2)
sys.modules.setdefault("omnimind_backend.grpc.generated.omnimind_backend_pb2_grpc", _pb2_grpc)

from omnimind_backend.api.v1.agent import router as agent_router
from omnimind_backend.schemas.agent import StreamEvent

app = FastAPI()
app.include_router(agent_router, prefix="/v1")


def test_stream_route_emits_response_and_done(monkeypatch) -> None:
    async def _fake_stream_chat(self, **_kwargs):
        yield StreamEvent(
            id="evt-1",
            seq=1,
            type="response",
            mode="messages",
            data="hello",
            meta=None,
        )
        yield StreamEvent(
            id="evt-2",
            seq=2,
            type="done",
            mode="messages",
            data="",
            meta=None,
        )

    monkeypatch.setattr(
        "omnimind_backend.grpc.client.InternalGrpcClient.stream_chat",
        _fake_stream_chat,
        raising=False,
    )

    client = TestClient(app)
    with client.stream("POST", "/v1/agent/chat/stream", json={"message": "oi"}) as resp:
        body = "".join(list(resp.iter_text()))

    assert "\"type\": \"response\"" in body
    assert "\"type\": \"done\"" in body
