"""Session controller for managing chat sessions and context."""

from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from mindflow_backend.api.controllers.base_controller import BaseController, audit_log, require_auth
from mindflow_backend.schemas.api.common import PaginationParams
from mindflow_backend.schemas.api.requests import SessionCreateRequest, SessionUpdateRequest
from mindflow_backend.schemas.api.responses import SessionListResponse, SessionResponse
from mindflow_backend.services import get_session_service
from mindflow_backend.storage import db_session


class SessionController(BaseController):
    """Controller for session management operations."""
    
    def __init__(self):
        super().__init__()
        self.session_service = get_session_service()
    
    def get_db_dependency(self):
        """Get database session dependency."""
        def get_db():
            with db_session() as db:
                yield db
        return Depends(get_db)
    
    @require_auth
    @audit_log("session_create")
    async def create_session(self, request: SessionCreateRequest, db: Session = None) -> SessionResponse:
        """Create a new chat session."""
        try:
            self.log_request(None, "create_session", title=request.title)
            
            session_data = await self.session_service.create_session(
                title=request.title,
                user_id=request.user_id
            )
            
            return SessionResponse(
                success=True,
                message="Session created successfully",
                id=session_data["id"],
                title=session_data["title"],
                created_at=session_data["created_at"],
                updated_at=session_data["updated_at"],
                metadata=session_data
            )
            
        except Exception as e:
            raise self.handle_error(e, "create_session")
    
    @require_auth
    @audit_log("session_get")
    async def get_session(self, session_id: str, db: Session = None) -> SessionResponse:
        """Get session details and history."""
        try:
            self.log_request(None, "get_session", session_id=session_id)
            
            session_data = await self.session_service.get_session(session_id)
            
            if not session_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found"
                )
            
            return SessionResponse(
                success=True,
                message="Session retrieved successfully",
                id=session_data["id"],
                title=session_data["title"],
                created_at=session_data["created_at"],
                updated_at=session_data["updated_at"],
                message_count=len(session_data.get("messages", [])),
                metadata=session_data
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise self.handle_error(e, "get_session")
    
    @require_auth
    @audit_log("session_list")
    async def list_sessions(
        self, 
        pagination: PaginationParams = PaginationParams(),
        db: Session = None
    ) -> SessionListResponse:
        """List chat sessions with pagination."""
        try:
            self.log_request(None, "list_sessions", limit=pagination.limit, offset=pagination.offset)
            
            # Get sessions and total count
            sessions_data = await self.session_service.list_sessions(
                limit=pagination.limit,
                offset=pagination.offset
            )
            
            # Get actual total count for pagination
            total_count = await self.session_service.count_sessions()
            
            # Convert to response format
            session_responses = []
            for session_data in sessions_data:
                session_responses.append(SessionResponse(
                    id=session_data["id"],
                    title=session_data["title"],
                    created_at=session_data["created_at"],
                    updated_at=session_data["updated_at"],
                    metadata=session_data
                ))
            
            # Calculate has_next based on actual total
            current_end = pagination.offset + len(session_responses)
            has_next = current_end < total_count
            
            return SessionListResponse(
                items=session_responses,
                total=total_count,
                limit=pagination.limit,
                offset=pagination.offset,
                has_next=has_next,
                has_prev=pagination.offset > 0
            )
            
        except Exception as e:
            raise self.handle_error(e, "list_sessions")
    
    @require_auth
    @audit_log("session_update")
    async def update_session(
        self, 
        session_id: str, 
        request: SessionUpdateRequest, 
        db: Session = None
    ) -> SessionResponse:
        """Update session details."""
        try:
            self.log_request(None, "update_session", session_id=session_id, title=request.title)
            
            session_data = await self.session_service.update_session(
                session_id=session_id,
                title=request.title
            )
            
            return SessionResponse(
                success=True,
                message="Session updated successfully",
                id=session_data["id"],
                title=session_data["title"],
                updated_at=session_data["updated_at"],
                metadata=session_data
            )
            
        except Exception as e:
            raise self.handle_error(e, "update_session")
    
    @require_auth
    @audit_log("session_delete")
    async def delete_session(self, session_id: str, db: Session = None) -> dict[str, Any]:
        """Delete a chat session."""
        try:
            self.log_request(None, "delete_session", session_id=session_id)
            
            success = await self.session_service.delete_session(session_id)
            
            return {
                "success": True,
                "message": "Session deleted successfully",
                "session_id": session_id
            }
            
        except Exception as e:
            raise self.handle_error(e, "delete_session")
    
    @require_auth
    @audit_log("message_add")
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        provider: str | None = None,
        model: str | None = None,
        db: Session = None
    ) -> dict[str, Any]:
        """Add a message to a session."""
        try:
            # Sanitize content
            sanitized_content = self.sanitize_input(content)
            
            self.log_request(
                None, 
                "add_message", 
                session_id=session_id,
                role=role,
                provider=provider,
                model=model
            )
            
            message_data = await self.session_service.add_message(
                session_id=session_id,
                role=role,
                content=sanitized_content,
                provider=provider,
                model=model
            )
            
            return {
                "success": True,
                "message": "Message added successfully",
                "data": message_data
            }
            
        except Exception as e:
            raise self.handle_error(e, "add_message")
