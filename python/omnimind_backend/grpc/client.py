from collections.abc import AsyncGenerator

from omnimind_backend.grpc.services.agent_runtime_service import AgentRuntimeServiceImpl
from omnimind_backend.schemas.chat.agent import AgentChatRequest, StreamEvent
from omnimind_backend.schemas.core.common import LLMProvider


class LocalAgentClient:
    """In-process client that calls service implementations directly (not real gRPC).

    Calls AgentRuntimeServiceImpl methods in-process instead of over a real gRPC
    channel. This avoids the need for generated stubs and a running gRPC server
    during development and testing.

    TODO: Replace with a real gRPC channel client (using generated stubs) when the
    service is deployed as a separate process or in a distributed environment.
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
