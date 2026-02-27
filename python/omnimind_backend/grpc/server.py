import asyncio

import grpc

from omnimind_backend.grpc.services.agent_runtime_service import AgentRuntimeServiceImpl
from omnimind_backend.infra.config import get_settings


async def serve() -> None:
    """Start internal gRPC server.

    Generated bindings are expected in `omnimind_backend.grpc.generated`.
    """

    settings = get_settings()
    server = grpc.aio.server()

    try:
        from omnimind_backend.grpc.generated import omnimind_backend_pb2_grpc as pb2_grpc
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Missing generated gRPC bindings. Run: python/scripts/gen_proto.sh"
        ) from exc

    pb2_grpc.add_AgentRuntimeServiceServicer_to_server(AgentRuntimeServiceImpl(), server)

    server.add_insecure_port(f"{settings.grpc_host}:{settings.grpc_port}")
    await server.start()
    await server.wait_for_termination()


def run() -> None:
    asyncio.run(serve())


if __name__ == "__main__":
    run()
