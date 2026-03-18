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
