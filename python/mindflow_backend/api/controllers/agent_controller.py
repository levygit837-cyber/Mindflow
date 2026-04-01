"""Agent controller for handling agent-related API endpoints."""

from __future__ import annotations

import asyncio
import inspect
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse

from mindflow_backend.api.controllers.base_controller import (
    BaseController,
    audit_log,
    rate_limit,
    require_auth,
    sanitize_input,
)
from mindflow_backend.grpc.factory import get_runtime_client
from mindflow_backend.infra.sanitizer import SanitizationError
from mindflow_backend.schemas.api.requests import AgentChatRequest
from mindflow_backend.schemas.api.responses import AgentResponse
from mindflow_backend.schemas.chat.agent import (
    AgentExecutionMessageRequest,
    AgentExecutionResponse,
    StreamEvent,
    StreamEventMeta,
)
from mindflow_backend.services import get_agent_service

# Hook handlers for prompt submission
from mindflow_backend.hooks.handlers.user_prompt_submit import UserPromptSubmitHandler

# ── Module-level client access ────────────────────────────────────────────────
# Use the transport factory so the active transport mode is respected.
# _get_local_agent_client() is kept as a backward-compat alias used in main.py.

def _get_local_agent_client():
    """Return the runtime client from the transport factory (cached internally)."""
    return get_runtime_client()


class AgentController(BaseController):
    """Controller for agent operations and chat interactions."""
    
    def __init__(self):
        super().__init__()
        self.agent_service = get_agent_service()
    
    @require_auth
    @sanitize_input
    @rate_limit("agent_chat")
    @audit_log("agent_chat_stream")
    async def stream_chat(self, payload: AgentChatRequest, request: Request) -> StreamingResponse:
        """Handle streaming agent chat with full security and validation."""
        try:
            # Validate request
            await self.agent_service.validate_agent_request(payload.model_dump())
            
            # Sanitize message
            sanitized_message = self.sanitize_input(payload.message)
            
            # Validate session ID
            raw_session_id = getattr(payload, "session_id", None) or getattr(payload, "sessionId", None)
            session_id = self.validate_session_id(raw_session_id)
            
            # Log request
            self.log_request(request, "agent_chat_stream", 
                           agent_type=payload.agent_type,
                           provider=payload.provider,
                           session_id=session_id)
            
            # Generate IDs
            import uuid
            turn_id = f"turn-{uuid.uuid4()}"
            run_id = str(uuid.uuid4())
            
            # Fire UserPromptSubmit hook (background task — non-blocking)
            asyncio.create_task(self._fire_user_prompt_submit_hook(session_id))
            
            # Reuse the cached client (avoids rebuilding AgentRuntime / LangGraph per request)
            grpc_client = _get_local_agent_client()
            
            async def event_generator():
                """Generate streaming events."""
                import asyncio
                import json

                from mindflow_backend.utils.formatting import format_sse
                try:
                    async for event in grpc_client.stream_chat(
                        session_id=session_id,
                        message=sanitized_message,
                        provider=payload.provider,
                        model=payload.model,
                        run_id=run_id,
                        orchestrate=payload.orchestrate,
                        agent_type=payload.agent_type,
                        folder_path=getattr(payload, 'folder_path', None),
                        execution_id=getattr(payload, "execution_id", None),
                    ):
                        if await request.is_disconnected():
                            break

                        # Add metadata
                        meta = event.meta or StreamEventMeta()
                        if not meta.runId:
                            meta.runId = run_id
                        if not meta.turnRunId:
                            meta.turnRunId = turn_id
                        event.meta = meta

                        # Validate tool payload
                        if event.type in {"tool_call", "tool_result"}:
                            try:
                                json.loads(event.data)
                            except json.JSONDecodeError:
                                self.logger.warning(f"Invalid tool payload in event: {event.type}")
                                continue

                        yield format_sse(event.model_dump())
                        # Yield control to the event loop so uvicorn can drain the TCP
                        # write buffer and send this chunk before processing the next event.
                        await asyncio.sleep(0)

                        if event.type == "done":
                            break

                except Exception as e:
                    self.logger.error(f"Error in stream generation: {str(e)}", exc_info=True)
                    error_event = StreamEvent(
                        id=str(uuid.uuid4()),
                        seq=999,
                        type="error",
                        mode="messages",
                        data=str(e),
                        meta=StreamEventMeta(runId=run_id, turnRunId=turn_id)
                    )
                    yield format_sse(error_event.model_dump())

            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no",
                    "Connection": "keep-alive",
                },
            )
            
        except SanitizationError as e:
            raise self.handle_error(e, "agent_chat_stream")
        except Exception as e:
            raise self.handle_error(e, "agent_chat_stream")

    @require_auth
    @audit_log("agent_execution_create")
    async def create_execution(self, payload: AgentChatRequest, request: Request | None = None) -> AgentExecutionResponse:
        raw_session_id = getattr(payload, "session_id", None) or getattr(payload, "sessionId", None)
        session_id = self.validate_session_id(raw_session_id)
        self.log_request(
            request,
            "create_execution",
            agent_type=payload.agent_type,
            provider=payload.provider,
            session_id=session_id,
        )

        runtime_client = _get_local_agent_client()
        runtime_method = getattr(runtime_client, "create_execution", None)
        if runtime_method is None or not callable(runtime_method):
            raise HTTPException(status_code=501, detail="Runtime does not implement create_execution")

        result = runtime_method(payload=payload, session_id=session_id)
        if inspect.isawaitable(result):
            result = await result

        return self._normalize_execution_response(
            payload=result,
            execution_id=result.get("execution_id", ""),
            action="create",
            default_message="Execution created",
        )
    
    @require_auth
    @audit_log("agent_capabilities")
    async def get_capabilities(self, agent_type: str) -> AgentResponse:
        """Get capabilities for a specific agent type."""
        try:
            self.log_request(None, "get_capabilities", agent_type=agent_type)
            
            capabilities_data = await self.agent_service.get_agent_capabilities(agent_type)
            
            return AgentResponse(
                success=True,
                message=f"Capabilities retrieved for {agent_type}",
                agent_type=agent_type,
                response=f"Agent {agent_type} capabilities: {', '.join(capabilities_data.get('capabilities', []))}",
                capabilities=capabilities_data.get("capabilities", []),
                metadata=capabilities_data
            )
            
        except Exception as e:
            raise self.handle_error(e, "get_capabilities")
    
    @require_auth
    @audit_log("agent_list")
    async def list_agents(self, request: Request | None = None) -> AgentResponse:
        """List all available agents."""
        try:
            self.log_request(request, "list_agents")
            
            agents_data = await self.agent_service.list_available_agents()
            
            return AgentResponse(
                success=True,
                message="Available agents retrieved",
                response=f"Found {agents_data.get('available_count', 0)} available agents",
                capabilities=list(agents_data.get("agents", {}).keys()),
                metadata=agents_data
            )
            
        except Exception as e:
            raise self.handle_error(e, "list_agents")
    
    @require_auth
    @audit_log("agent_validate")
    async def validate_request(self, request_data: dict[str, Any]) -> AgentResponse:
        """Validate an agent request without processing."""
        try:
            is_valid = await self.agent_service.validate_agent_request(request_data)
            
            return AgentResponse(
                success=True,
                message="Request validation completed",
                response="Request is valid" if is_valid else "Request validation failed",
                metadata={"valid": is_valid}
            )
            
        except Exception as e:
            raise self.handle_error(e, "validate_request")

    @require_auth
    @audit_log("agent_execution_status")
    async def get_execution_status(self, execution_id: str, req: Request | None = None) -> AgentExecutionResponse:
        """Get execution status for an agent runtime execution."""
        return await self._resolve_execution_action(
            execution_id=execution_id,
            runtime_method_name="get_execution_status",
            req=req,
            action=None,
            default_message="Execution status retrieved",
        )

    @require_auth
    @audit_log("agent_execution_pause")
    async def pause_execution(self, execution_id: str, req: Request | None = None) -> AgentExecutionResponse:
        """Request a pause for an agent runtime execution."""
        return await self._resolve_execution_action(
            execution_id=execution_id,
            runtime_method_name="pause_execution",
            req=req,
            action="pause",
            default_status="pause_requested",
            default_message="Pause requested",
        )

    @require_auth
    @audit_log("agent_execution_resume")
    async def resume_execution(self, execution_id: str, req: Request | None = None) -> AgentExecutionResponse:
        """Request a resume for an agent runtime execution."""
        return await self._resolve_execution_action(
            execution_id=execution_id,
            runtime_method_name="resume_execution",
            req=req,
            action="resume",
            default_status="resume_requested",
            default_message="Resume requested",
        )

    @require_auth
    @audit_log("agent_execution_events")
    async def get_execution_events(
        self,
        execution_id: str,
        *,
        after_id: int = 0,
        req: Request | None = None,
    ) -> list[dict[str, Any]]:
        self.log_request(req, "get_execution_events", execution_id=execution_id, after_id=after_id)

        runtime_client = _get_local_agent_client()
        runtime_method = getattr(runtime_client, "get_execution_events", None)
        if runtime_method is None or not callable(runtime_method):
            raise HTTPException(status_code=501, detail="Runtime does not implement get_execution_events")

        result = runtime_method(execution_id=execution_id, after_id=after_id)
        if inspect.isawaitable(result):
            result = await result
        return [self._normalize_execution_payload(item) for item in list(result or [])]

    @require_auth
    @audit_log("agent_execution_message")
    async def send_execution_message(
        self,
        execution_id: str,
        payload: AgentExecutionMessageRequest,
        req: Request | None = None,
    ) -> dict[str, Any]:
        self.log_request(req, "send_execution_message", execution_id=execution_id, message_type=payload.message_type)

        runtime_client = _get_local_agent_client()
        runtime_method = getattr(runtime_client, "send_execution_message", None)
        if runtime_method is None or not callable(runtime_method):
            raise HTTPException(status_code=501, detail="Runtime does not implement send_execution_message")

        result = runtime_method(
            execution_id=execution_id,
            message_type=payload.message_type,
            content=payload.content,
            sender_execution_id=payload.sender_execution_id,
            visibility=payload.visibility,
            payload=payload.payload,
        )
        if inspect.isawaitable(result):
            result = await result
        return self._normalize_execution_payload(result)

    async def _resolve_execution_action(
        self,
        *,
        execution_id: str,
        runtime_method_name: str,
        req: Request | None,
        action: str | None,
        default_message: str,
        default_status: str | None = None,
    ) -> AgentExecutionResponse:
        self.log_request(req, runtime_method_name, execution_id=execution_id)

        runtime_client = _get_local_agent_client()
        runtime_method = getattr(runtime_client, runtime_method_name, None)
        if runtime_method is None or not callable(runtime_method):
            raise HTTPException(
                status_code=501,
                detail=f"Runtime does not implement {runtime_method_name}",
            )

        result = runtime_method(execution_id=execution_id)
        if inspect.isawaitable(result):
            result = await result

        payload = self._normalize_execution_payload(result)
        return self._normalize_execution_response(
            payload=payload,
            execution_id=execution_id,
            action=action,
            default_message=default_message,
            default_status=default_status,
        )

    def _normalize_execution_response(
        self,
        *,
        payload: dict[str, Any],
        execution_id: str,
        action: str | None,
        default_message: str,
        default_status: str | None = None,
    ) -> AgentExecutionResponse:
        status = payload.get("status") or default_status or action or "unknown"
        snapshot = payload.get("snapshot")
        if snapshot is None:
            snapshot = payload.get("state") or {}

        tree = payload.get("tree") or {}
        messages = payload.get("messages") or []
        processes = payload.get("processes") or []
        events = payload.get("events") or []

        metadata = payload.get("metadata")
        if metadata is None:
            metadata = {
                key: value
                for key, value in payload.items()
                if key
                not in {
                    "execution_id",
                    "root_execution_id",
                    "parent_execution_id",
                    "status",
                    "stage",
                    "action",
                    "paused",
                    "can_resume",
                    "progress",
                    "snapshot",
                    "state",
                    "tree",
                    "events",
                    "messages",
                    "processes",
                    "metadata",
                    "message",
                }
            }

        return AgentExecutionResponse(
            success=payload.get("success", True),
            message=payload.get("message") or default_message,
            execution_id=payload.get("execution_id", execution_id),
            root_execution_id=payload.get("root_execution_id"),
            parent_execution_id=payload.get("parent_execution_id"),
            status=status,
            stage=payload.get("stage"),
            action=payload.get("action", action),
            paused=payload.get("paused", status in {"paused", "pause_requested"}),
            can_resume=payload.get("can_resume", status in {"paused", "pause_requested"}),
            progress=payload.get("progress"),
            snapshot=snapshot if isinstance(snapshot, dict) else {"value": snapshot},
            tree=tree if isinstance(tree, dict) else {"value": tree},
            events=events if isinstance(events, list) else [{"value": events}],
            messages=messages if isinstance(messages, list) else [{"value": messages}],
            processes=processes if isinstance(processes, list) else [{"value": processes}],
            metadata=metadata if isinstance(metadata, dict) else {"value": metadata},
            timestamp=payload.get("timestamp"),
        )

    def _normalize_execution_payload(self, payload: Any) -> dict[str, Any]:
        if payload is None:
            return {}
        if isinstance(payload, dict):
            return payload
        if hasattr(payload, "model_dump"):
            return payload.model_dump()
        if hasattr(payload, "__dict__"):
            return {
                key: value
                for key, value in vars(payload).items()
                if not key.startswith("_")
            }
        return {"value": payload}

    async def _fire_user_prompt_submit_hook(self, session_id: str) -> None:
        """Fire UserPromptSubmit hook in background."""
        from mindflow_backend.infra.config import get_settings
        try:
            async for result in UserPromptSubmitHandler.execute(
                session_id=session_id,
                cwd=get_settings().working_path,
            ):
                if result.add_context:
                    self.logger.debug(
                        "user_prompt_submit_hook_context",
                        session_id=session_id,
                        context=result.add_context[:200],
                    )
        except Exception as exc:
            self.logger.warning(
                "user_prompt_submit_hooks_error",
                session_id=session_id,
                error=str(exc),
            )
