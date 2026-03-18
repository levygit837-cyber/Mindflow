import sys
import types
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

# Keep import path stable when generated gRPC bindings are absent in test checkouts.
_pb2 = types.ModuleType("mindflow_backend.grpc.generated.mindflow_backend_pb2")
_pb2_grpc = types.ModuleType("mindflow_backend.grpc.generated.mindflow_backend_pb2_grpc")
_pb2_grpc.AgentRuntimeServiceServicer = type("AgentRuntimeServiceServicer", (), {})
sys.modules.setdefault("mindflow_backend.grpc.generated.mindflow_backend_pb2", _pb2)
sys.modules.setdefault("mindflow_backend.grpc.generated.mindflow_backend_pb2_grpc", _pb2_grpc)

from mindflow_backend.api.v1.agent import router as agent_router


app = FastAPI()
app.include_router(agent_router, prefix="/v1")


def test_execution_status_route_returns_runtime_status(monkeypatch) -> None:
    fake_runtime = AsyncMock()
    fake_runtime.get_execution_status.return_value = {
        "execution_id": "exec-123",
        "status": "running",
        "progress": 0.5,
        "paused": False,
        "can_resume": False,
        "snapshot": {"step": "analyzing"},
        "metadata": {"source": "runtime"},
    }

    monkeypatch.setattr(
        "mindflow_backend.api.controllers.agent_controller._get_local_agent_client",
        lambda: fake_runtime,
    )

    client = TestClient(app)
    response = client.get("/v1/agent/execution/exec-123")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["execution_id"] == "exec-123"
    assert payload["status"] == "running"
    assert payload["progress"] == 0.5
    assert payload["snapshot"] == {"step": "analyzing"}


def test_pause_execution_route_requests_pause(monkeypatch) -> None:
    fake_runtime = AsyncMock()
    fake_runtime.pause_execution.return_value = {
        "execution_id": "exec-123",
        "status": "paused",
        "paused": True,
        "can_resume": True,
        "snapshot": {"step": "waiting"},
        "metadata": {"source": "runtime"},
    }

    monkeypatch.setattr(
        "mindflow_backend.api.controllers.agent_controller._get_local_agent_client",
        lambda: fake_runtime,
    )

    client = TestClient(app)
    response = client.post("/v1/agent/execution/exec-123/pause")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["execution_id"] == "exec-123"
    assert payload["status"] == "paused"
    assert payload["paused"] is True
    assert payload["can_resume"] is True


def test_resume_execution_route_requests_resume(monkeypatch) -> None:
    fake_runtime = AsyncMock()
    fake_runtime.resume_execution.return_value = {
        "execution_id": "exec-123",
        "status": "running",
        "paused": False,
        "can_resume": False,
        "snapshot": {"step": "resumed"},
        "metadata": {"source": "runtime"},
    }

    monkeypatch.setattr(
        "mindflow_backend.api.controllers.agent_controller._get_local_agent_client",
        lambda: fake_runtime,
    )

    client = TestClient(app)
    response = client.post("/v1/agent/execution/exec-123/resume")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["execution_id"] == "exec-123"
    assert payload["status"] == "running"
    assert payload["paused"] is False


def test_create_execution_route_returns_root_execution(monkeypatch) -> None:
    fake_runtime = AsyncMock()
    fake_runtime.create_execution.return_value = {
        "execution_id": "exec-123",
        "root_execution_id": "exec-123",
        "status": "queued",
        "stage": "routing",
        "paused": False,
        "can_resume": False,
        "snapshot": {},
        "metadata": {"session_id": "sess-123"},
    }

    monkeypatch.setattr(
        "mindflow_backend.api.controllers.agent_controller._get_local_agent_client",
        lambda: fake_runtime,
    )

    client = TestClient(app)
    response = client.post(
        "/v1/agent/executions",
        json={"message": "Planeje uma sessão durável", "orchestrate": True, "sessionId": "sess-123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["execution_id"] == "exec-123"
    assert payload["status"] == "queued"
    assert payload["metadata"]["session_id"] == "sess-123"


def test_post_execution_message_route_records_context_update(monkeypatch) -> None:
    fake_runtime = AsyncMock()
    fake_runtime.send_execution_message.return_value = {
        "success": True,
        "execution_id": "exec-child",
        "status": "running",
        "message": {
            "id": 1,
            "message_type": "context_update",
            "content": "Novo contexto",
            "recipient_execution_id": "exec-child",
        },
    }

    monkeypatch.setattr(
        "mindflow_backend.api.controllers.agent_controller._get_local_agent_client",
        lambda: fake_runtime,
    )

    client = TestClient(app)
    response = client.post(
        "/v1/agent/execution/exec-child/messages",
        json={"message_type": "context_update", "content": "Novo contexto"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["message"]["message_type"] == "context_update"
    assert payload["message"]["recipient_execution_id"] == "exec-child"


def test_execution_events_route_replays_events_without_follow(monkeypatch) -> None:
    fake_runtime = AsyncMock()
    fake_runtime.get_execution_events.return_value = [
        {
            "id": 1,
            "execution_id": "exec-123",
            "sequence": 1,
            "event_type": "execution_started",
            "payload": {"stage": "routing"},
        }
    ]

    monkeypatch.setattr(
        "mindflow_backend.api.controllers.agent_controller._get_local_agent_client",
        lambda: fake_runtime,
    )

    client = TestClient(app)
    response = client.get("/v1/agent/execution/exec-123/events?after_seq=0&follow=false")

    assert response.status_code == 200
    assert "data:" in response.text
    assert "execution_started" in response.text


def test_status_route_returns_not_implemented_when_runtime_missing_operation(monkeypatch) -> None:
    fake_runtime = AsyncMock()
    del fake_runtime.get_execution_status

    monkeypatch.setattr(
        "mindflow_backend.api.controllers.agent_controller._get_local_agent_client",
        lambda: fake_runtime,
    )

    client = TestClient(app)
    response = client.get("/v1/agent/execution/exec-123")

    assert response.status_code == 501
    assert "get_execution_status" in response.json()["detail"]
