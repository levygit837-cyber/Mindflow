"""Memory controller for managing agent memory, context, and RAG."""

from __future__ import annotations

from typing import Any
from fastapi import Request

from mindflow_backend.api.controllers.base_controller import BaseController, require_auth, audit_log
from mindflow_backend.memory.api.schemas import (
    MemorySearchRequest,
    MemorySummaryRequest,
    ContextWindowRequest,
    MemoryResponse,
    MemorySearchResponse,
    MemorySummaryResponse,
    ContextWindowResponse
)
from mindflow_backend.services import get_memory_service


class MemoryController(BaseController):
    """Controller for memory management operations."""
    
    def __init__(self):
        super().__init__()
        self.memory_service = get_memory_service()
    
    @require_auth
    @audit_log("memory_get_agent")
    async def get_agent_memory(
        self, 
        agent_id: str, 
        session_id: str, 
        token_limit: int | None = None,
        req: Request = None
    ) -> MemoryResponse:
        """Get memory for a specific agent in a session."""
        try:
            self.log_request(req, "get_agent_memory", agent_id=agent_id, session_id=session_id)
            
            memory_data = await self.memory_service.get_agent_memory(
                agent_id=agent_id,
                session_id=session_id,
                token_limit=token_limit
            )
            
            return MemoryResponse(
                success=True,
                message=f"Memory retrieved for agent {agent_id}",
                agent_id=agent_id,
                session_id=session_id,
                memory_events=memory_data.get("memory_events", []),
                token_count=memory_data.get("token_count"),
                window_index=memory_data.get("window_index"),
                metadata=memory_data
            )
            
        except Exception as e:
            raise self.handle_error(e, "get_agent_memory")
    
    @require_auth
    @audit_log("memory_search")
    async def search_memory(self, request: MemorySearchRequest, req: Request) -> MemorySearchResponse:
        """Search memory/context using semantic similarity."""
        try:
            self.log_request(req, "search_memory", session_id=request.session_id, query=request.query[:50])
            
            results = await self.memory_service.search_semantic_context(
                query=request.query,
                session_id=request.session_id,
                top_k=request.top_k,
                min_score=request.min_score
            )
            
            return MemorySearchResponse(
                success=True,
                message="Memory search completed",
                query=request.query,
                results=results,
                total_found=len(results),
                search_type=request.search_type,
                metadata={
                    "top_k": request.top_k,
                    "min_score": request.min_score,
                    "agent_id": request.agent_id
                }
            )
            
        except Exception as e:
            raise self.handle_error(e, "search_memory")
    
    @require_auth
    @audit_log("memory_add_event")
    async def add_memory_event(
        self,
        agent_id: str,
        session_id: str,
        role: str,
        content: str,
        token_count: int,
        source_message_id: int | None = None,
        req: Request = None
    ) -> MemoryResponse:
        """Add a memory event for an agent."""
        try:
            # Sanitize content
            sanitized_content = self.sanitize_input(content)
            
            self.log_request(req, "add_memory_event", agent_id=agent_id, session_id=session_id, role=role)
            
            event_data = await self.memory_service.add_memory_event(
                agent_id=agent_id,
                session_id=session_id,
                role=role,
                content=sanitized_content,
                token_count=token_count,
                source_message_id=source_message_id
            )
            
            return MemoryResponse(
                success=True,
                message="Memory event added",
                agent_id=agent_id,
                session_id=session_id,
                metadata=event_data
            )
            
        except Exception as e:
            raise self.handle_error(e, "add_memory_event")
    
    @require_auth
    @audit_log("memory_context_window")
    async def get_context_window(
        self,
        session_id: str,
        window_start: int,
        window_end: int,
        req: Request = None
    ) -> ContextWindowResponse:
        """Get a specific context window."""
        try:
            self.log_request(req, "get_context_window", session_id=session_id, 
                           window_start=window_start, window_end=window_end)
            
            window_data = await self.memory_service.get_context_window(
                session_id=session_id,
                window_start=window_start,
                window_end=window_end
            )
            
            return ContextWindowResponse(
                success=True,
                message="Context window retrieved",
                session_id=session_id,
                window_start=window_start,
                window_end=window_end,
                content=window_data["content"],
                events=window_data.get("events", []),
                token_count=window_data["token_count"],
                metadata=window_data
            )
            
        except Exception as e:
            raise self.handle_error(e, "get_context_window")
    
    @require_auth
    @audit_log("memory_create_summary")
    async def create_memory_summary(
        self,
        agent_id: str,
        session_id: str,
        window_start: int,
        window_end: int,
        summary_type: str = "auto",
        req: Request = None
    ) -> MemorySummaryResponse:
        """Create a summary of a memory window."""
        try:
            self.log_request(req, "create_memory_summary", agent_id=agent_id, session_id=session_id)
            
            summary_data = await self.memory_service.create_memory_summary(
                agent_id=agent_id,
                session_id=session_id,
                window_range=(window_start, window_end)
            )
            
            return MemorySummaryResponse(
                success=True,
                message="Memory summary created",
                agent_id=agent_id,
                session_id=session_id,
                window_range=(window_start, window_end),
                summary=summary_data["summary"],
                key_points=summary_data["key_points"],
                coverage_ratio=summary_data["coverage_ratio"],
                token_count=summary_data.get("token_count", window_end - window_start),
                created_at=summary_data.get("created_at"),
                metadata=summary_data
            )
            
        except Exception as e:
            raise self.handle_error(e, "create_memory_summary")
    
    @require_auth
    @audit_log("memory_get_windows")
    async def get_memory_windows(self, agent_id: str, session_id: str, req: Request = None) -> MemoryResponse:
        """Get all memory windows for an agent."""
        try:
            self.log_request(req, "get_memory_windows", agent_id=agent_id, session_id=session_id)
            
            windows_data = await self.memory_service.get_memory_windows(agent_id, session_id)
            
            return MemoryResponse(
                success=True,
                message=f"Memory windows retrieved for agent {agent_id}",
                agent_id=agent_id,
                session_id=session_id,
                memory_events=windows_data,
                metadata={"windows_count": len(windows_data)}
            )
            
        except Exception as e:
            raise self.handle_error(e, "get_memory_windows")
    
    @require_auth
    @audit_log("memory_update_cursor")
    async def update_memory_cursor(
        self,
        agent_id: str,
        session_id: str,
        token_total: int,
        tokens_since_summary: int,
        req: Request = None
    ) -> MemoryResponse:
        """Update memory cursor for an agent."""
        try:
            self.log_request(req, "update_memory_cursor", agent_id=agent_id, session_id=session_id)
            
            cursor_data = await self.memory_service.update_memory_cursor(
                agent_id=agent_id,
                session_id=session_id,
                token_total=token_total,
                tokens_since_summary=tokens_since_summary
            )
            
            return MemoryResponse(
                success=True,
                message="Memory cursor updated",
                agent_id=agent_id,
                session_id=session_id,
                token_count=token_total,
                metadata=cursor_data
            )
            
        except Exception as e:
            raise self.handle_error(e, "update_memory_cursor")
    
    @require_auth
    @audit_log("memory_session_stats")
    async def get_session_memory_stats(self, session_id: str, req: Request = None) -> dict[str, Any]:
        """Get memory statistics for a session."""
        try:
            self.log_request(req, "get_session_memory_stats", session_id=session_id)
            
            # This would aggregate memory data across all agents in a session
            # For now, return a placeholder that could be enhanced
            
            return {
                "success": True,
                "message": "Session memory stats retrieved",
                "session_id": session_id,
                "total_agents": 0,  # Would be calculated from actual data
                "total_memory_events": 0,
                "total_tokens": 0,
                "memory_windows": [],
                "last_activity": None,
                "metadata": {"status": "placeholder"}
            }
            
        except Exception as e:
            raise self.handle_error(e, "get_session_memory_stats")
    
    @require_auth
    @audit_log("memory_cleanup")
    async def cleanup_old_memory(
        self,
        session_id: str,
        days_to_keep: int = 30,
        req: Request = None
    ) -> dict[str, Any]:
        """Clean up old memory data for a session."""
        try:
            self.log_request(req, "cleanup_old_memory", session_id=session_id, days_to_keep=days_to_keep)
            
            # This would implement cleanup logic
            # For now, return a placeholder response
            
            return {
                "success": True,
                "message": f"Memory cleanup completed for session {session_id}",
                "session_id": session_id,
                "days_to_keep": days_to_keep,
                "events_removed": 0,  # Would be calculated from actual cleanup
                "space_freed": 0,  # Would be calculated in bytes
                "metadata": {"status": "placeholder"}
            }
            
        except Exception as e:
            raise self.handle_error(e, "cleanup_old_memory")
