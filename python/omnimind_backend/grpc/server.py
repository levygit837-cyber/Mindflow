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

    host = settings.grpc_host
    port = settings.grpc_port

    # Conditional TLS: use secure port in production if certs are available.
    if (
        settings.app_env == "production"
        and settings.grpc_tls_cert_path
        and settings.grpc_tls_key_path
    ):
        import pathlib

        cert = pathlib.Path(settings.grpc_tls_cert_path).read_bytes()
        key = pathlib.Path(settings.grpc_tls_key_path).read_bytes()
        credentials = grpc.ssl_server_credentials([(key, cert)])
        server.add_secure_port(f"{host}:{port}", credentials)
    else:
        server.add_insecure_port(f"{host}:{port}")

    await server.start()
    print(f"gRPC Server started on {host}:{port}", flush=True)
    await server.wait_for_termination()


def run() -> None:
    asyncio.run(serve())


if __name__ == "__main__":
    run()
