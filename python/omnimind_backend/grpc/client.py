from collections.abc import AsyncGenerator

from omnimind_backend.grpc.services.agent_runtime_service import AgentRuntimeServiceImpl
from omnimind_backend.schemas.agent import AgentChatRequest, StreamEvent
from omnimind_backend.schemas.common import LLMProvider


class InternalGrpcClient:
    """Local fallback client for internal services.

    This client calls service implementations directly until generated gRPC
    stubs are wired in runtime environments.
    """

    def __init__(self) -> None:
        self._service = AgentRuntimeServiceImpl()
        self.agent = self._service

    async def stream_chat(
        self,
        *,
        session_id: str,
        message: str,
        provider: LLMProvider | None = None,
        model: str | None = None,
        run_id: str | None = None,
        orchestrate: bool = False,
        agent_type: str | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        payload = AgentChatRequest(
            message=message,
            provider=provider,
            model=model,
            orchestrate=orchestrate,
            agent_type=agent_type,
        )
        async for event in self._service.runtime.stream_chat(
            payload,
            session_id=session_id,
            run_id=run_id,
        ):
            yield event
