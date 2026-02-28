import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from omnimind_backend.api.sse import format_sse
from omnimind_backend.grpc.client import InternalGrpcClient
from omnimind_backend.schemas.agent import AgentChatRequest, StreamEventMeta

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/chat/stream")
async def stream_chat(payload: AgentChatRequest, request: Request) -> StreamingResponse:
    turn_id = f"turn-{uuid.uuid4()}"
    run_id = str(uuid.uuid4())
    grpc_client = InternalGrpcClient()

    async def event_generator() -> AsyncGenerator[str, None]:
        async for event in grpc_client.agent.stream_chat(
            session_id=turn_id,
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
                meta.turnRunId = turn_id
            event.meta = meta

            # Keep tool payload validation side-effect free.
            if event.type in {"tool_call", "tool_result"}:
                try:
                    json.loads(event.data)
                except Exception:
                    pass

            yield format_sse(event.model_dump())

            if event.type == "done":
                break

    return StreamingResponse(event_generator(), media_type="text/event-stream")
