import asyncio
import contextlib
import json
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from mindflow_backend.api.dependencies import protected_route_dependencies
from mindflow_backend.api.controllers.agent_controller import AgentController
from mindflow_backend.utils.formatting import format_sse
from mindflow_backend.grpc.client import LocalAgentClient
from mindflow_backend.infra.sanitizer import SanitizationError, sanitize_message
from mindflow_backend.schemas.chat.agent import (
    AgentChatRequest,
    AgentExecutionMessageRequest,
    AgentExecutionResponse,
    StreamEventMeta,
)
from mindflow_backend.schemas.tools.shell_tabs import ShellTabCreateRequest, ShellTabExecRequest
from mindflow_backend.services import get_shell_tab_service

router = APIRouter(prefix="/agent", tags=["agent"], dependencies=protected_route_dependencies)

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


@router.post("/executions", response_model=AgentExecutionResponse)
async def create_execution(payload: AgentChatRequest, request: Request):
    """Create a durable root execution before opening a stream."""
    try:
        payload.message = sanitize_message(payload.message)
    except SanitizationError as exc:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return await agent_controller.create_execution(payload, request)


@router.get("/capabilities/{agent_type}")
async def get_agent_capabilities(agent_type: str):
    """Get capabilities for a specific agent type."""
    return await agent_controller.get_capabilities(agent_type)


@router.get("/list")
async def list_agents(request: Request):
    """List all available agents."""
    return await agent_controller.list_agents(request)


@router.post("/validate")
async def validate_agent_request(request_data: dict):
    """Validate an agent request without processing."""
    return await agent_controller.validate_request(request_data)


@router.get("/execution/{execution_id}", response_model=AgentExecutionResponse)
async def get_execution_status(execution_id: str, request: Request):
    """Get status for an agent execution."""
    return await agent_controller.get_execution_status(execution_id, request)


@router.get("/execution/{execution_id}/events")
async def stream_execution_events(
    execution_id: str,
    request: Request,
    after_seq: int = 0,
    follow: bool = True,
) -> StreamingResponse:
    """Replay durable events and optionally keep polling for live updates."""

    async def event_generator() -> AsyncGenerator[str, None]:
        cursor = after_seq
        while True:
            events = await agent_controller.get_execution_events(
                execution_id,
                after_id=cursor,
                req=request,
            )
            for event in events:
                cursor = max(cursor, int(event.get("id", 0) or 0))
                yield format_sse(event)
                await asyncio.sleep(0)

            if not follow or await request.is_disconnected():
                break
            await asyncio.sleep(0.75)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/execution/{execution_id}/messages")
async def post_execution_message(
    execution_id: str,
    payload: AgentExecutionMessageRequest,
    request: Request,
):
    """Append a durable mailbox message to a running execution."""
    return await agent_controller.send_execution_message(execution_id, payload, request)


@router.post("/execution/{execution_id}/pause", response_model=AgentExecutionResponse)
async def pause_execution(execution_id: str, request: Request):
    """Request a pause for an agent execution."""
    return await agent_controller.pause_execution(execution_id, request)


@router.post("/execution/{execution_id}/resume", response_model=AgentExecutionResponse)
async def resume_execution(execution_id: str, request: Request):
    """Request a resume for an agent execution."""
    return await agent_controller.resume_execution(execution_id, request)


@router.get("/shell-tabs/{session_id}")
async def list_shell_tabs(session_id: str):
    service = get_shell_tab_service()
    tabs = await service.list_tabs(session_id=session_id)
    return [tab.model_dump(mode="json") for tab in tabs]


@router.post("/shell-tabs/{session_id}")
async def open_shell_tab(session_id: str, payload: ShellTabCreateRequest):
    service = get_shell_tab_service()
    created = await service.create_tab(
        session_id=session_id,
        cwd=payload.cwd,
        title=payload.title,
    )
    return created.model_dump(mode="json")


@router.get("/shell-tabs/{session_id}/events")
async def stream_shell_tab_events(session_id: str, request: Request) -> StreamingResponse:
    service = get_shell_tab_service()

    async def event_generator() -> AsyncGenerator[str, None]:
        async for event in service.subscribe(session_id=session_id):
            if await request.is_disconnected():
                break
            yield format_sse(event)
            await asyncio.sleep(0)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/shell-tabs/{session_id}/{tab_id}")
async def get_shell_tab_status(session_id: str, tab_id: str):
    service = get_shell_tab_service()
    try:
        status = await service.get_tab_status(session_id=session_id, tab_id=tab_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return status.model_dump(mode="json")


@router.post("/shell-tabs/{session_id}/{tab_id}/exec")
async def exec_shell_tab(session_id: str, tab_id: str, payload: ShellTabExecRequest):
    service = get_shell_tab_service()
    try:
        updated = await service.exec_in_tab(
            session_id=session_id,
            tab_id=tab_id,
            command=payload.command,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return updated.model_dump(mode="json")


@router.get("/shell-tabs/{session_id}/{tab_id}/buffer")
async def read_shell_tab_buffer(session_id: str, tab_id: str):
    service = get_shell_tab_service()
    try:
        snapshot = await service.read_tab_buffer(session_id=session_id, tab_id=tab_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return snapshot.model_dump(mode="json")


@router.delete("/shell-tabs/{session_id}/{tab_id}")
async def close_shell_tab(session_id: str, tab_id: str):
    service = get_shell_tab_service()
    try:
        closed = await service.close_tab(session_id=session_id, tab_id=tab_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return closed.model_dump(mode="json")


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
            session_id=session_id,
            message=payload.message,
            provider=payload.provider,
            model=payload.model,
            run_id=run_id,
            orchestrate=payload.orchestrate,
            agent_type=payload.agent_type,
            folder_path=getattr(payload, "folder_path", None),
            execution_id=getattr(payload, "execution_id", None),
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
            # Give the event loop a chance to flush the TCP write buffer.
            await asyncio.sleep(0)

            if event.type == "done":
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
