"""Session service for managing chat sessions and context."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, UTC

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.storage.repositories import ChatRepository
from mindflow_backend.storage.postgresql.connection import async_session_factory
from mindflow_backend.storage.postgresql.models import ChatSession, ChatMessage

_logger = get_logger(__name__)


class SessionService:
    """Service for managing chat sessions, context, and memory."""
    
    def __init__(self):
        self.logger = _logger
    
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
        self.logger.info(
            "Creating new session",
            title=title,
            user_id=user_id
        )
        
        try:
            # Generate session ID
            import uuid
            session_id = f"sess-{uuid.uuid4()}"
            
            # Create session in database
            async with async_session_factory() as session:
                chat_session = ChatSession(
                    id=session_id,
                    title=title or "New Session"
                )
                session.add(chat_session)
                await session.commit()
                await session.refresh(chat_session)
                
                return {
                    "id": chat_session.id,
                    "title": chat_session.title,
                    "created_at": chat_session.created_at.isoformat(),
                    "updated_at": chat_session.updated_at.isoformat(),
                    "message_count": 0,
                    "status": "created"
                }
                
        except Exception as e:
            self.logger.error(f"Error creating session: {str(e)}")
            raise
    
    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get session details and history from database.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary containing session data and messages
        """
        self.logger.info(f"Getting session: {session_id}")
        
        try:
            async with async_session_factory() as session:
                # Get session
                repo = ChatRepository()
                chat_session = await repo.get_session_async(session, session_id)
                
                if not chat_session:
                    raise ValueError(f"Session not found: {session_id}")
                
                # Get messages
                messages = await repo.get_messages_async(session, session_id)
                
                return {
                    "id": chat_session.id,
                    "title": chat_session.title,
                    "created_at": chat_session.created_at.isoformat(),
                    "updated_at": chat_session.updated_at.isoformat(),
                    "messages": [
                        {
                            "id": msg.id,
                            "role": msg.role,
                            "content": msg.content,
                            "provider": msg.provider,
                            "model": msg.model,
                            "created_at": msg.created_at.isoformat()
                        }
                        for msg in messages
                    ],
                    "message_count": len(messages),
                    "status": "retrieved"
                }
                
        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"Error getting session: {str(e)}")
            raise
    
    async def list_sessions(
        self,
        limit: int = 50,
        offset: int = 0,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List chat sessions from database.
        
        Args:
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip
            user_id: Optional user filter
            
        Returns:
            List of session dictionaries
        """
        self.logger.info(
            "Listing sessions",
            limit=limit,
            offset=offset,
            user_id=user_id
        )
        
        try:
            async with async_session_factory() as session:
                repo = ChatRepository()
                sessions = await repo.list_sessions_async(session, limit=limit, offset=offset)
                
                return [
                    {
                        "id": s.id,
                        "title": s.title,
                        "created_at": s.created_at.isoformat(),
                        "updated_at": s.updated_at.isoformat(),
                        "message_count": len(s.messages) if s.messages else 0,
                        "status": "listed"
                    }
                    for s in sessions
                ]
                
        except Exception as e:
            self.logger.error(f"Error listing sessions: {str(e)}")
            raise
    
    async def update_session(
        self,
        session_id: str,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update session details in database.
        
        Args:
            session_id: Session identifier
            title: New session title
            
        Returns:
            Updated session dictionary
        """
        self.logger.info(
            f"Updating session: {session_id}",
            title=title
        )
        
        try:
            async with async_session_factory() as session:
                repo = ChatRepository()
                
                # Get existing session
                chat_session = await repo.get_session_async(session, session_id)
                if not chat_session:
                    raise ValueError(f"Session not found: {session_id}")
                
                # Update title if provided
                if title is not None:
                    chat_session.title = title
                    chat_session.updated_at = datetime.now(UTC)
                
                await session.commit()
                await session.refresh(chat_session)
                
                return {
                    "id": chat_session.id,
                    "title": chat_session.title,
                    "created_at": chat_session.created_at.isoformat(),
                    "updated_at": chat_session.updated_at.isoformat(),
                    "message_count": len(chat_session.messages) if chat_session.messages else 0,
                    "status": "updated"
                }
                
        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"Error updating session: {str(e)}")
            raise
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a chat session from database.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if deleted successfully
        """
        self.logger.info(f"Deleting session: {session_id}")
        
        try:
            async with async_session_factory() as session:
                repo = ChatRepository()
                success = await repo.delete_session_async(session, session_id)
                return success
                
        except Exception as e:
            self.logger.error(f"Error deleting session: {str(e)}")
            raise
    
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add a message to a session in database.
        
        Args:
            session_id: Session identifier
            role: Message role (user, assistant, system)
            content: Message content
            provider: LLM provider
            model: Model name
            
        Returns:
            Created message dictionary
        """
        self.logger.info(
            f"Adding message to session: {session_id}",
            role=role,
            provider=provider,
            model=model
        )
        
        try:
            # Validate role
            valid_roles = ["user", "assistant", "system"]
            if role not in valid_roles:
                raise ValueError(f"Invalid role: {role}. Must be one of: {valid_roles}")
            
            async with async_session_factory() as session:
                repo = ChatRepository()
                
                # Verify session exists
                chat_session = await repo.get_session_async(session, session_id)
                if not chat_session:
                    raise ValueError(f"Session not found: {session_id}")
                
                # Create message
                chat_message = ChatMessage(
                    session_id=session_id,
                    role=role,
                    content=content,
                    provider=provider,
                    model=model
                )
                
                session.add(chat_message)
                
                # Update session timestamp
                chat_session.updated_at = datetime.now(UTC)
                
                await session.commit()
                await session.refresh(chat_message)
                
                return {
                    "id": chat_message.id,
                    "session_id": session_id,
                    "role": role,
                    "content": content,
                    "provider": provider,
                    "model": model,
                    "created_at": chat_message.created_at.isoformat(),
                    "status": "added"
                }
                
        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"Error adding message: {str(e)}")
            raise
    
    async def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary containing session statistics
        """
        self.logger.info(f"Getting session stats: {session_id}")
        
        try:
            async with async_session_factory() as session:
                repo = ChatRepository()
                
                # Get session
                chat_session = await repo.get_session_async(session, session_id)
                if not chat_session:
                    raise ValueError(f"Session not found: {session_id}")
                
                messages = await repo.get_messages_async(session, session_id)
                
                # Calculate statistics
                user_messages = [m for m in messages if m.role == "user"]
                assistant_messages = [m for m in messages if m.role == "assistant"]
                system_messages = [m for m in messages if m.role == "system"]
                
                total_tokens = sum(
                    len(m.content.split()) for m in messages
                )  # Simple token estimation
                
                return {
                    "session_id": session_id,
                    "total_messages": len(messages),
                    "user_messages": len(user_messages),
                    "assistant_messages": len(assistant_messages),
                    "system_messages": len(system_messages),
                    "estimated_tokens": total_tokens,
                    "providers_used": list(set(m.provider for m in messages if m.provider)),
                    "models_used": list(set(m.model for m in messages if m.model)),
                    "created_at": chat_session.created_at.isoformat(),
                    "last_activity": chat_session.updated_at.isoformat(),
                    "duration_hours": (
                        datetime.now(UTC) - chat_session.created_at
                    ).total_seconds() / 3600
                }
                
        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"Error getting session stats: {str(e)}")
            raise
