"""Session service for managing chat sessions and context.

This service provides comprehensive session management including creation,
retrieval, message handling, and context coordination with memory services.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, UTC
import uuid

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.storage import ChatRepository, async_db_session, ChatSession, ChatMessage
from mindflow_backend.services.interfaces.base_interfaces import BaseAbstractService
from mindflow_backend.services.interfaces.core_interfaces import SessionServiceInterface


class SessionService(BaseAbstractService, SessionServiceInterface):
    """Service for managing chat sessions, context, and memory.
    
    This service handles session lifecycle, message management,
    and coordinates with memory services for context preservation.
    """
    
    def __init__(self) -> None:
        """Initialize session service with repository and dependencies."""
        super().__init__()
        self._chat_repo = ChatRepository()
        
        # Lazy load dependencies to avoid circular imports
        self._memory_service = None
        self._agent_service = None
    
    def _get_logger(self) -> Any:
        """Get logger instance for this service."""
        return get_logger(__name__)
    
    def _get_memory_service(self):
        """Get memory service instance (lazy loading)."""
        if self._memory_service is None:
            from mindflow_backend.memory import get_memory_service
            self._memory_service = get_memory_service()
        return self._memory_service
    
    def _get_agent_service(self):
        """Get agent service instance (lazy loading)."""
        if self._agent_service is None:
            from mindflow_backend.services import get_agent_service
            self._agent_service = get_agent_service()
        return self._agent_service
    
    async def create_session(
        self,
        title: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new chat session using real database operations.
        
        Args:
            title: Optional session title
            user_id: Optional user identifier
            
        Returns:
            Dictionary containing session data
        """
        self.log_operation("create_session", title=title, user_id=user_id)
        
        try:
            # Generate session ID
            session_id = f"sess-{uuid.uuid4()}"
            
            # Create session in database
            async with async_session_factory() as session:
                chat_session = ChatSession(
                    id=session_id,
                    title=title or "New Session",
                    user_id=user_id
                )
                session.add(chat_session)
                await session.commit()
                await session.refresh(chat_session)
                
                # Initialize memory for this session
                memory_service = self._get_memory_service()
                await memory_service.initialize_session_memory(
                    session_id=session_id,
                    agent_types=["analyst", "coder", "researcher", "reviewer"]
                )
                
                return {
                    "id": chat_session.id,
                    "title": chat_session.title,
                    "user_id": chat_session.user_id,
                    "created_at": chat_session.created_at.isoformat(),
                    "updated_at": chat_session.updated_at.isoformat(),
                    "message_count": 0,
                    "status": "created",
                    "memory_initialized": True
                }
                
        except Exception as exc:
            self._logger.error(f"Error creating session: {str(exc)}")
            raise
    
    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get session details and history from database.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary containing session data and messages
        """
        self.log_operation("get_session", session_id=session_id)
        
        try:
            async with async_session_factory() as session:
                # Get session
                chat_session = await self._chat_repo.get_session_async(session, session_id)
                
                if not chat_session:
                    raise ValueError(f"Session not found: {session_id}")
                
                # Get messages
                messages = await self._chat_repo.get_messages_async(session, session_id)
                
                # Get memory context
                memory_service = self._get_memory_service()
                memory_context = await memory_service.get_session_memory_summary(session_id)
                
                return {
                    "id": chat_session.id,
                    "title": chat_session.title,
                    "user_id": chat_session.user_id,
                    "created_at": chat_session.created_at.isoformat(),
                    "updated_at": chat_session.updated_at.isoformat(),
                    "messages": [
                        {
                            "id": msg.id,
                            "role": msg.role,
                            "content": msg.content,
                            "provider": msg.provider,
                            "model": msg.model,
                            "token_count": msg.token_count,
                            "created_at": msg.created_at.isoformat(),
                            "metadata": msg.metadata
                        }
                        for msg in messages
                    ],
                    "message_count": len(messages),
                    "memory_context": memory_context,
                    "status": "active"
                }
                
        except Exception as exc:
            self._logger.error(f"Error getting session {session_id}: {str(exc)}")
            raise
    
    async def list_sessions(
        self,
        limit: int = 50,
        offset: int = 0,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List sessions with pagination and filtering.
        
        Args:
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip
            user_id: Optional user filter
            
        Returns:
            List of session dictionaries
        """
        self.log_operation("list_sessions", limit=limit, offset=offset, user_id=user_id)
        
        try:
            async with async_session_factory() as session:
                sessions = await self._chat_repo.list_sessions_async(
                    session, limit=limit, offset=offset, user_id=user_id
                )
                
                return [
                    {
                        "id": sess.id,
                        "title": sess.title,
                        "user_id": sess.user_id,
                        "created_at": sess.created_at.isoformat(),
                        "updated_at": sess.updated_at.isoformat(),
                        "message_count": sess.message_count or 0,
                        "status": "active"
                    }
                    for sess in sessions
                ]
                
        except Exception as exc:
            self._logger.error(f"Error listing sessions: {str(exc)}")
            raise
    
    async def update_session(
        self,
        session_id: str,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update session information.
        
        Args:
            session_id: Session identifier
            title: New session title
            
        Returns:
            Updated session data
        """
        self.log_operation("update_session", session_id=session_id, title=title)
        
        try:
            async with async_session_factory() as session:
                # Get existing session
                chat_session = await self._chat_repo.get_session_async(session, session_id)
                
                if not chat_session:
                    raise ValueError(f"Session not found: {session_id}")
                
                # Update title if provided
                if title:
                    chat_session.title = title
                    chat_session.updated_at = datetime.now(UTC)
                
                await session.commit()
                await session.refresh(chat_session)
                
                return {
                    "id": chat_session.id,
                    "title": chat_session.title,
                    "user_id": chat_session.user_id,
                    "created_at": chat_session.created_at.isoformat(),
                    "updated_at": chat_session.updated_at.isoformat(),
                    "message_count": chat_session.message_count or 0,
                    "status": "updated"
                }
                
        except Exception as exc:
            self._logger.error(f"Error updating session {session_id}: {str(exc)}")
            raise
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and all associated data.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if deletion successful
        """
        self.log_operation("delete_session", session_id=session_id)
        
        try:
            async with async_session_factory() as session:
                # Delete session (cascade deletes messages)
                deleted = await self._chat_repo.delete_session_async(session, session_id)
                
                if deleted:
                    # Clean up memory data
                    memory_service = self._get_memory_service()
                    await memory_service.cleanup_session_memory(session_id)
                
                return deleted
                
        except Exception as exc:
            self._logger.error(f"Error deleting session {session_id}: {str(exc)}")
            raise
    
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add a message to a session.
        
        Args:
            session_id: Session identifier
            role: Message role (user, assistant, system)
            content: Message content
            provider: Optional LLM provider
            model: Optional model name
            
        Returns:
            Created message data
        """
        self.log_operation(
            "add_message",
            session_id=session_id,
            role=role,
            content_length=len(content),
            provider=provider,
            model=model
        )
        
        try:
            # Validate inputs
            if role not in ["user", "assistant", "system"]:
                raise ValueError(f"Invalid role: {role}")
            
            if not content or len(content.strip()) == 0:
                raise ValueError("Message content cannot be empty")
            
            async with async_session_factory() as db_session:
                # Verify session exists
                chat_session = await self._chat_repo.get_session_async(db_session, session_id)
                if not chat_session:
                    raise ValueError(f"Session not found: {session_id}")
                
                # Create message
                message = ChatMessage(
                    session_id=session_id,
                    role=role,
                    content=content,
                    provider=provider,
                    model=model,
                    token_count=self._estimate_token_count(content),
                    metadata={}
                )
                
                # Add to database
                db_session.add(message)
                
                # Update session timestamp
                chat_session.updated_at = datetime.now(UTC)
                chat_session.message_count = (chat_session.message_count or 0) + 1
                
                await db_session.commit()
                await db_session.refresh(message)
                
                # Store in memory service for context retrieval
                if role in ["user", "assistant"]:
                    memory_service = self._get_memory_service()
                    await memory_service.add_memory_event(
                        agent_id="session",  # General session memory
                        session_id=session_id,
                        role=role,
                        content=content,
                        token_count=message.token_count,
                        source_message_id=message.id
                    )
                
                return {
                    "id": message.id,
                    "session_id": message.session_id,
                    "role": message.role,
                    "content": message.content,
                    "provider": message.provider,
                    "model": message.model,
                    "token_count": message.token_count,
                    "created_at": message.created_at.isoformat(),
                    "metadata": message.metadata
                }
                
        except Exception as exc:
            self._logger.error(f"Error adding message to session {session_id}: {str(exc)}")
            raise
    
    async def get_session_messages(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get messages from a session with pagination.
        
        Args:
            session_id: Session identifier
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            
        Returns:
            List of message dictionaries
        """
        self.log_operation("get_session_messages", session_id=session_id, limit=limit, offset=offset)
        
        try:
            async with async_session_factory() as session:
                messages = await self._chat_repo.get_messages_async(
                    session, session_id, limit=limit, offset=offset
                )
                
                return [
                    {
                        "id": msg.id,
                        "session_id": msg.session_id,
                        "role": msg.role,
                        "content": msg.content,
                        "provider": msg.provider,
                        "model": msg.model,
                        "token_count": msg.token_count,
                        "created_at": msg.created_at.isoformat(),
                        "metadata": msg.metadata
                    }
                    for msg in messages
                ]
                
        except Exception as exc:
            self._logger.error(f"Error getting messages for session {session_id}: {str(exc)}")
            raise
    
    async def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """Get comprehensive session context including memory.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary containing session context
        """
        self.log_operation("get_session_context", session_id=session_id)
        
        try:
            # Get basic session info
            session_data = await self.get_session(session_id)
            
            # Get memory context
            memory_service = self._get_memory_service()
            memory_context = await memory_service.get_session_memory_summary(session_id)
            
            # Get agent interaction history
            agent_service = self._get_agent_service()
            agent_history = await memory_service.get_agent_interaction_history(session_id)
            
            return {
                "session": session_data,
                "memory_context": memory_context,
                "agent_history": agent_history,
                "context_summary": self._generate_context_summary(session_data, memory_context)
            }
            
        except Exception as exc:
            self._logger.error(f"Error getting session context {session_id}: {str(exc)}")
            raise
    
    def _estimate_token_count(self, text: str) -> int:
        """Estimate token count for text (rough approximation)."""
        # Rough estimate: ~4 characters per token
        return max(1, len(text) // 4)
    
    def _generate_context_summary(self, session_data: Dict[str, Any], memory_context: Dict[str, Any]) -> str:
        """Generate a summary of session context."""
        message_count = session_data.get("message_count", 0)
        session_age = datetime.now(UTC) - datetime.fromisoformat(session_data.get("created_at"))
        
        summary_parts = [
            f"Session with {message_count} messages",
            f"Age: {session_age.days} days"
        ]
        
        if memory_context.get("total_tokens"):
            summary_parts.append(f"Total tokens: {memory_context['total_tokens']}")
        
        if memory_context.get("agent_types"):
            summary_parts.append(f"Active agents: {', '.join(memory_context['agent_types'])}")
        
        return " | ".join(summary_parts)
