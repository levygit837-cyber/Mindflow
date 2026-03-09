from collections.abc import AsyncGenerator
from typing import Any

from mindflow_backend.runtime.stream import AgentRuntime
from mindflow_backend.grpc.generated import mindflow_backend_pb2_grpc as pb2_grpc
from mindflow_backend.schemas.chat.agent import AgentChatRequest, StreamEvent


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
            orchestrate=getattr(request, "orchestrate", False),
            debugSteps=getattr(request, "debug_steps", False),
            agent_type=getattr(request, "agent_type", None) or None,
        )
        session_id = getattr(request, "session_id", "")
        run_id = getattr(request, "run_id", "")
        async for event in self.runtime.stream_chat(payload, session_id, run_id=run_id):
            yield event
