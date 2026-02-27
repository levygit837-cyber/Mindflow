from omnimind_backend.grpc.services.agent_runtime_service import AgentRuntimeServiceImpl


class InternalGrpcClient:
    """Local fallback client for internal services.

    This client calls service implementations directly until generated gRPC
    stubs are wired in runtime environments.
    """

    def __init__(self) -> None:
        self.agent = AgentRuntimeServiceImpl()
