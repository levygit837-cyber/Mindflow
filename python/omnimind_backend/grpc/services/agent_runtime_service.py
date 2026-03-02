from collections.abc import AsyncGenerator
from typing import Any

from omnimind_backend.agents.runtime import AgentRuntime
from omnimind_backend.grpc.generated import omnimind_backend_pb2_grpc as pb2_grpc
from omnimind_backend.schemas.agent import AgentChatRequest, StreamEvent


class AgentRuntimeServiceImpl(pb2_grpc.AgentRuntimeServiceServicer):
    def __init__(self) -> None:
        self.runtime = AgentRuntime()

    async def StreamChat(
        self,
        request: Any,
        context: Any,
    ) -> AsyncGenerator[Any, None]:
        payload = AgentChatRequest(
            message=request.message,
            provider=request.provider or None,
            model=request.model or None,
            orchestrate=request.orchestrate,
            agent_type=getattr(request, "agent_type", None) or None,

        )
        async for event in self.runtime.stream_chat(payload, request.session_id, run_id=request.run_id):
            yield event
