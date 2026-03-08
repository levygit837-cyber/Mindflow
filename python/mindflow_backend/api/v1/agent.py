import contextlib
import json
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse

from mindflow_backend.utils.formatting import format_sse
from mindflow_backend.grpc.client import LocalAgentClient
from mindflow_backend.infra.sanitizer import SanitizationError, sanitize_message
from mindflow_backend.schemas.chat.agent import AgentChatRequest, StreamEventMeta
from mindflow_backend.api.controllers.agent_controller import AgentController

router = APIRouter(prefix="/agent", tags=["agent"])

# Initialize controller
agent_controller = AgentController()


@router.post("/chat/stream")
async def stream_chat(payload: AgentChatRequest, request: Request) -> StreamingResponse:
    """Stream agent chat using the new controller architecture."""
    try:
        payload.message = sanitize_message(payload.message)
    except SanitizationError as exc:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    # Delegate to controller
    return await agent_controller.stream_chat(payload, request)


@router.get("/capabilities/{agent_type}")
async def get_agent_capabilities(agent_type: str):
    """Get capabilities for a specific agent type."""
    return await agent_controller.get_capabilities(agent_type)


@router.get("/list")
async def list_agents():
    """List all available agents."""
    return await agent_controller.list_agents()


@router.post("/validate")
async def validate_agent_request(request_data: dict):
    """Validate an agent request without processing."""
    return await agent_controller.validate_request(request_data)


# Legacy endpoints - maintained for backward compatibility
@router.post("/chat/stream/legacy")
async def stream_chat_legacy(payload: AgentChatRequest, request: Request) -> StreamingResponse:
    """Legacy streaming endpoint - maintained for compatibility."""
    try:
        payload.message = sanitize_message(payload.message)
    except SanitizationError as exc:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    # Use session_id from payload if provided (from frontend), otherwise create new
    session_id = payload.sessionId or f"sess-{uuid.uuid4()}"
    turn_id = f"turn-{uuid.uuid4()}"
    run_id = str(uuid.uuid4())
    grpc_client = LocalAgentClient()

    async def event_generator() -> AsyncGenerator[str, None]:
        async for event in grpc_client.stream_chat(
            session_id=session_id,  # Now passing the session_id for persistence
            message=payload.message,
            provider=payload.provider,
            model=payload.model,
            run_id=run_id,
            orchestrate=payload.orchestrate,
            agent_type=payload.agent_type,
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
                with contextlib.suppress(Exception):
                    json.loads(event.data)

            yield format_sse(event.model_dump())

            if event.type == "done":
                break

    return StreamingResponse(event_generator(), media_type="text/event-stream")
