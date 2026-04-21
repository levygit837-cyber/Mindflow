from collections.abc import AsyncGenerator
from typing import Any

from mindflow_backend.grpc_internal.generated import mindflow_backend_pb2 as pb2
from mindflow_backend.grpc_internal.generated import mindflow_backend_pb2_grpc as pb2_grpc
from mindflow_backend.grpc_internal.serialization import stream_event_to_proto
from mindflow_backend.runtime import RuntimeAgentRuntime
from mindflow_backend.schemas.chat.agent import AgentChatRequest


class AgentRuntimeServiceImpl(pb2_grpc.AgentRuntimeServiceServicer):
    def __init__(self) -> None:
        self.runtime = RuntimeAgentRuntime()

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
            folder_path=getattr(request, "folder_path", None) or None,
        )
        session_id = getattr(request, "session_id", "")
        run_id = getattr(request, "run_id", "")
        async for event in self.runtime.stream_chat(payload, session_id, run_id=run_id):
            yield stream_event_to_proto(event, pb2)
