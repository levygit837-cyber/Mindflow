import sys
import types

from fastapi import FastAPI

# Keep import path stable when generated gRPC bindings are absent in test checkouts.
_pb2 = types.ModuleType("mindflow_backend.grpc.generated.mindflow_backend_pb2")
_pb2_grpc = types.ModuleType("mindflow_backend.grpc.generated.mindflow_backend_pb2_grpc")
_pb2_grpc.AgentRuntimeServiceServicer = type("AgentRuntimeServiceServicer", (), {})
sys.modules.setdefault("mindflow_backend.grpc.generated.mindflow_backend_pb2", _pb2)
sys.modules.setdefault("mindflow_backend.grpc.generated.mindflow_backend_pb2_grpc", _pb2_grpc)

_loguru = types.ModuleType("loguru")


class _DummyLogger:
    def bind(self, *args, **kwargs):
        return self

    def __getattr__(self, _name):
        return lambda *args, **kwargs: None


_loguru.logger = _DummyLogger()
sys.modules.setdefault("loguru", _loguru)

from mindflow_backend.api.router import router as api_router


def test_v1_router_has_no_legacy_namespace() -> None:
    app = FastAPI()
    app.include_router(api_router)

    paths = {route.path for route in app.routes}
    assert not any(path.startswith("/v1/legacy") for path in paths)


def test_v1_router_has_no_legacy_agent_stream_route() -> None:
    app = FastAPI()
    app.include_router(api_router)

    paths = {route.path for route in app.routes}
    assert "/v1/agent/chat/stream/legacy" not in paths
