from collections.abc import AsyncGenerator

from omnimind_backend.agents.runtime import AgentRuntime
from omnimind_backend.schemas.agent import AgentChatRequest, StreamEvent


class AgentRuntimeServiceImpl:
    def __init__(self) -> None:
        self.runtime = AgentRuntime()

    async def stream_chat(
        self,
        *,
        session_id: str,
        message: str,
        provider: str | None,
        model: str | None,
        run_id: str | None = None,
        orchestrate: bool = False,
    ) -> AsyncGenerator[StreamEvent, None]:
        payload = AgentChatRequest(
            message=message,
            provider=provider,
            model=model,
            orchestrate=orchestrate,
        )
        async for event in self.runtime.stream_chat(payload, session_id, run_id=run_id):
            yield event
