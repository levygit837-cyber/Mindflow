import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from omnimind_backend.api.deps import session_repository
from omnimind_backend.api.sse import format_sse
from omnimind_backend.grpc.client import InternalGrpcClient
from omnimind_backend.schemas.agent import AgentChatRequest, StreamEventMeta
from omnimind_backend.storage.db import db_session

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/chat/stream")
async def stream_chat(payload: AgentChatRequest, request: Request) -> StreamingResponse:
    session_id = payload.sessionId or payload.conversationId or f"session-{uuid.uuid4()}"
    run_id = str(uuid.uuid4())
    grpc_client = InternalGrpcClient()

    with db_session() as session:
        session_repository.save_message(
            session,
            session_id=session_id,
            role="user",
            content=payload.message,
            run_id=run_id,
        )
        session_repository.register_run(
            session,
            session_id=session_id,
            run_id=run_id,
            label=payload.message[:100],
            metadata={"source": "agent.chat.stream"},
        )

    async def event_generator() -> AsyncGenerator[str, None]:
        assistant_text_parts: list[str] = []
        assistant_thought_parts: list[str] = []
        tool_calls: list[dict] = []

        async for event in grpc_client.agent.stream_chat(
            session_id=session_id,
            message=payload.message,
            provider=payload.provider,
            model=payload.model,
            run_id=run_id,
        ):
            if await request.is_disconnected():
                break

            meta = event.meta or StreamEventMeta()
            if not meta.runId:
                meta.runId = run_id
            if not meta.turnRunId:
                meta.turnRunId = session_id
            event.meta = meta

            if event.type == "response":
                assistant_text_parts.append(event.data)
            elif event.type == "thought":
                assistant_thought_parts.append(event.data)
            elif event.type == "tool_call":
                try:
                    tool_calls.append(json.loads(event.data))
                except Exception:
                    pass
            elif event.type == "tool_result":
                try:
                    data = json.loads(event.data)
                    for call in tool_calls:
                        if call.get("id") == data.get("id"):
                            call["result"] = data.get("result")
                except Exception:
                    pass

            yield format_sse(event.model_dump())

            if event.type == "done":
                break

        with db_session() as session:
            session_repository.save_message(
                session,
                session_id=session_id,
                role="assistant",
                content="".join(assistant_text_parts),
                thoughts="".join(assistant_thought_parts) or None,
                tool_calls=tool_calls or None,
                run_id=run_id,
            )

    return StreamingResponse(event_generator(), media_type="text/event-stream")
