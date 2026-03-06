"""Agent controller for handling agent-related API endpoints."""

from __future__ import annotations

from typing import Any
from fastapi import Request, Depends
from fastapi.responses import StreamingResponse

from mindflow_backend.api.controllers.base_controller import BaseController, require_auth, sanitize_input, rate_limit, audit_log
from mindflow_backend.api.schemas.requests import AgentChatRequest
from mindflow_backend.api.schemas.responses import AgentResponse
from mindflow_backend.services import get_agent_service
from mindflow_backend.grpc.client import LocalAgentClient
from mindflow_backend.infra.sanitizer import SanitizationError, sanitize_message
from mindflow_backend.schemas.chat.agent import StreamEvent, StreamEventMeta


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
            session_id = self.validate_session_id(payload.session_id)
            
            # Log request
            self.log_request(request, "agent_chat_stream", 
                           agent_type=payload.agent_type,
                           provider=payload.provider,
                           session_id=session_id)
            
            # Generate IDs
            import uuid
            turn_id = f"turn-{uuid.uuid4()}"
            run_id = str(uuid.uuid4())
            
            # Create gRPC client
            grpc_client = LocalAgentClient()
            
            async def event_generator():
                """Generate streaming events."""
                try:
                    async for event in grpc_client.stream_chat(
                        session_id=session_id,
                        message=sanitized_message,
                        provider=payload.provider,
                        model=payload.model,
                        run_id=run_id,
                        orchestrate=payload.orchestrate,
                        agent_type=payload.agent_type,
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
                                import json
                                json.loads(event.data)
                            except json.JSONDecodeError:
                                self.logger.warning(f"Invalid tool payload in event: {event.type}")
                                continue
                        
                        # Format and yield SSE event
                        from mindflow_backend.api.sse import format_sse
                        yield format_sse(event.model_dump())
                        
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
                    from mindflow_backend.api.sse import format_sse
                    yield format_sse(error_event.model_dump())
            
            return StreamingResponse(event_generator(), media_type="text/event-stream")
            
        except SanitizationError as e:
            raise self.handle_error(e, "agent_chat_stream")
        except Exception as e:
            raise self.handle_error(e, "agent_chat_stream")
    
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
    async def list_agents(self) -> AgentResponse:
        """List all available agents."""
        try:
            self.log_request(None, "list_agents")
            
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
