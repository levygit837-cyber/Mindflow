"""Session service for managing chat sessions and context.

This service provides comprehensive session management including creation,
retrieval, message handling, and context coordination with memory services.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select

from mindflow_backend.infra.database.connection import get_db_session
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.services.interfaces.base_interfaces import BaseAbstractService
from mindflow_backend.services.interfaces.core_interfaces import SessionServiceInterface
from mindflow_backend.storage.postgresql.models import ChatMessage, ChatSession

_SESSION_METADATA: dict[str, dict[str, Any]] = {}


class SessionService(BaseAbstractService, SessionServiceInterface):
    """Service for managing chat sessions, context, and memory.
    
    This service handles session lifecycle, message management,
    and coordinates with memory services for context preservation.
    """
    
    def __init__(self) -> None:
        """Initialize session service with repository and dependencies."""
        super().__init__()
        
        # Lazy load dependencies to avoid circular imports
        self._memory_service = None
        self._agent_service = None
        self._runtime = None
    
    def _get_logger(self) -> Any:
        """Get logger instance for this service."""
        return get_logger(__name__)
    
    def _get_memory_service(self):
        """Get memory service instance (lazy loading)."""
        if self._memory_service is None:
            from mindflow_backend.memory.session_memory.service import SessionMemoryService
            self._memory_service = SessionMemoryService()
        return self._memory_service
    
    def _get_agent_service(self):
        """Get agent service instance (lazy loading)."""
        if self._agent_service is None:
            from mindflow_backend.services import get_agent_service
            self._agent_service = get_agent_service()
        return self._agent_service

    def _get_runtime(self):
        """Get canonical runtime instance for lifecycle hooks."""
        if self._runtime is None:
            from mindflow_backend.runtime.streaming.stream import AgentRuntime
            self._runtime = AgentRuntime()
        return self._runtime

    @staticmethod
    def _session_owner(chat_session: ChatSession) -> str | None:
        """Return the compatibility user id for a chat session."""
        return getattr(chat_session, "owner_id", None)

    @staticmethod
    def _message_metadata(_message: ChatMessage) -> dict[str, Any]:
        """Return message metadata for legacy response contracts."""
        return {}

    @staticmethod
    def _session_metadata(session_id: str) -> dict[str, Any]:
        """Return mutable compatibility metadata for session mode state."""
        return _SESSION_METADATA.setdefault(session_id, {})

    @staticmethod
    async def _message_count(db_session: Any, session_id: str) -> int:
        result = await db_session.execute(
            select(func.count(ChatMessage.id)).where(ChatMessage.session_id == session_id)
        )
        return int(result.scalar() or 0)
    
    async def create_session(
        self,
        title: str | None = None,
        user_id: str | None = None
    ) -> dict[str, Any]:
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
            async with get_db_session() as session:
                chat_session = ChatSession(
                    id=session_id,
                    title=title or "New Session",
                    owner_id=user_id,
                )
                session.add(chat_session)
                await session.commit()
                await session.refresh(chat_session)
                
                # Initialize memory for this session
                memory_service = self._get_memory_service()
                if hasattr(memory_service, "initialize_session_memory"):
                    await memory_service.initialize_session_memory(
                        session_id=session_id,
                        agent_types=["analyst", "coder", "researcher", "reviewer"],
                    )
                
                # Fire SessionStart hook (background task — non-blocking)
                asyncio.create_task(self._fire_session_start_hook(session_id))
                
                return {
                    "id": chat_session.id,
                    "title": chat_session.title,
                    "user_id": self._session_owner(chat_session),
                    "created_at": chat_session.created_at.isoformat(),
                    "updated_at": chat_session.updated_at.isoformat(),
                    "message_count": 0,
                    "status": "created",
                    "memory_initialized": True
                }
                
        except Exception as exc:
            self._logger.error(f"Error creating session: {str(exc)}")
            raise

    async def _fire_session_start_hook(self, session_id: str) -> None:
        """Fire SessionStart hook in background."""
        try:
            await self._get_runtime().start_session(session_id)
        except Exception as exc:
            self._logger.warning(
                "session_start_hooks_error",
                session_id=session_id,
                error=str(exc),
            )
    
    async def get_session(self, session_id: str) -> dict[str, Any]:
        """Get session details and history from database.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary containing session data and messages
        """
        self.log_operation("get_session", session_id=session_id)
        
        try:
            async with get_db_session() as session:
                # Get session
                chat_session = await session.get(ChatSession, session_id)
                
                if not chat_session:
                    raise ValueError(f"Session not found: {session_id}")
                
                # Get messages
                result = await session.execute(
                    select(ChatMessage)
                    .where(ChatMessage.session_id == session_id)
                    .order_by(ChatMessage.created_at.asc())
                )
                messages = list(result.scalars().all())
                
                # Get memory context
                memory_service = self._get_memory_service()
                memory_context = await memory_service.get_session_memory_summary(session_id)
                
                return {
                    "id": chat_session.id,
                    "title": chat_session.title,
                    "user_id": self._session_owner(chat_session),
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
                            "metadata": self._message_metadata(msg),
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
        user_id: str | None = None
    ) -> list[dict[str, Any]]:
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
            async with get_db_session() as session:
                stmt = select(ChatSession).order_by(ChatSession.updated_at.desc()).offset(offset).limit(limit)
                if user_id:
                    stmt = stmt.where(ChatSession.owner_id == user_id)
                result = await session.execute(stmt)
                sessions = list(result.scalars().all())

                counts = {
                    sess.id: await self._message_count(session, sess.id)
                    for sess in sessions
                }
                
                return [
                    {
                        "id": sess.id,
                        "title": sess.title,
                        "user_id": self._session_owner(sess),
                        "created_at": sess.created_at.isoformat(),
                        "updated_at": sess.updated_at.isoformat(),
                        "message_count": counts.get(sess.id, 0),
                        "status": "active",
                    }
                    for sess in sessions
                ]
                
        except Exception as exc:
            self._logger.error(f"Error listing sessions: {str(exc)}")
            raise
    
    async def count_sessions(self, user_id: str | None = None) -> int:
        """Count total sessions with optional user filter.
        
        Args:
            user_id: Optional user filter
            
        Returns:
            Total number of sessions
        """
        self.log_operation("count_sessions", user_id=user_id)
        
        try:
            async with get_db_session() as session:
                # Build query
                stmt = select(func.count(ChatSession.id))
                if user_id:
                    stmt = stmt.where(ChatSession.owner_id == user_id)
                
                result = await session.execute(stmt)
                count = result.scalar() or 0
                
                return count
                
        except Exception as exc:
            self._logger.error(f"Error counting sessions: {str(exc)}")
            return 0
    
    async def update_session(
        self,
        session_id: str,
        title: str | None = None
    ) -> dict[str, Any]:
        """Update session information.
        
        Args:
            session_id: Session identifier
            title: New session title
            
        Returns:
            Updated session data
        """
        self.log_operation("update_session", session_id=session_id, title=title)
        
        try:
            async with get_db_session() as session:
                # Get existing session
                chat_session = await session.get(ChatSession, session_id)
                
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
                    "user_id": self._session_owner(chat_session),
                    "created_at": chat_session.created_at.isoformat(),
                    "updated_at": chat_session.updated_at.isoformat(),
                    "message_count": await self._message_count(session, session_id),
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
            async with get_db_session() as session:
                # Delete session (cascade deletes messages)
                chat_session = await session.get(ChatSession, session_id)
                deleted = chat_session is not None
                if chat_session is not None:
                    await session.delete(chat_session)
                    await session.commit()
                
                if deleted:
                    # Clean up memory data
                    memory_service = self._get_memory_service()
                    if hasattr(memory_service, "cleanup_session_memory"):
                        await memory_service.cleanup_session_memory(session_id)
                    
                    # Fire SessionEnd hook (background task — non-blocking)
                    asyncio.create_task(self._fire_session_end_hook(session_id))
                
                return deleted
                
        except Exception as exc:
            self._logger.error(f"Error deleting session {session_id}: {str(exc)}")
            raise

    async def _fire_session_end_hook(self, session_id: str) -> None:
        """Fire SessionEnd hook in background."""
        try:
            await self._get_runtime().end_session(session_id, reason="logout")
        except Exception as exc:
            self._logger.warning(
                "session_end_hooks_error",
                session_id=session_id,
                error=str(exc),
            )
    
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        provider: str | None = None,
        model: str | None = None
    ) -> dict[str, Any]:
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
            
            async with get_db_session() as db_session:
                # Verify session exists
                chat_session = await db_session.get(ChatSession, session_id)
                if not chat_session:
                    raise ValueError(f"Session not found: {session_id}")
                
                # Create message
                message = ChatMessage(
                    session_id=session_id,
                    role=role,
                    content=content,
                    provider=provider,
                    model=model,
                )
                
                # Add to database
                db_session.add(message)
                
                # Update session timestamp
                chat_session.updated_at = datetime.now(UTC)
                
                await db_session.commit()
                await db_session.refresh(message)
                
                # Store in memory service for context retrieval
                if role in ["user", "assistant"]:
                    memory_service = self._get_memory_service()
                    if hasattr(memory_service, "add_memory_event"):
                        await memory_service.add_memory_event(
                            agent_id="session",
                            session_id=session_id,
                            role=role,
                            content=content,
                            token_count=message.token_count,
                            source_message_id=message.id,
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
                    "metadata": self._message_metadata(message),
                }
                
        except Exception as exc:
            self._logger.error(f"Error adding message to session {session_id}: {str(exc)}")
            raise
    
    async def get_session_messages(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> list[dict[str, Any]]:
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
            async with get_db_session() as session:
                result = await session.execute(
                    select(ChatMessage)
                    .where(ChatMessage.session_id == session_id)
                    .order_by(ChatMessage.created_at.asc())
                    .offset(offset)
                    .limit(limit)
                )
                messages = list(result.scalars().all())
                
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
                        "metadata": self._message_metadata(msg),
                    }
                    for msg in messages
                ]
                
        except Exception as exc:
            self._logger.error(f"Error getting messages for session {session_id}: {str(exc)}")
            raise
    
    async def get_session_context(self, session_id: str) -> dict[str, Any]:
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
            if hasattr(memory_service, "get_agent_interaction_history"):
                agent_history = await memory_service.get_agent_interaction_history(session_id)
            else:
                agent_history = []
            
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
    
    def _generate_context_summary(self, session_data: dict[str, Any], memory_context: dict[str, Any]) -> str:
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
    
    # ─── Permission Mode Management ─────────────────────────────────────
    
    async def get_permission_mode(self, session_id: str) -> Any:
        """Get current permission mode for session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Current PermissionMode for the session
        """
        from mindflow_backend.permissions.types import PermissionMode
        
        self.log_operation("get_permission_mode", session_id=session_id)
        
        try:
            async with get_db_session() as session:
                chat_session = await session.get(ChatSession, session_id)
                if not chat_session:
                    self._logger.warning(f"Session {session_id} not found, returning DEFAULT mode")
                    return PermissionMode.DEFAULT
                
                # Get mode from session metadata
                metadata = self._session_metadata(session_id)
                mode_value = metadata.get("permission_mode", PermissionMode.DEFAULT.value)
                
                # Convert to PermissionMode enum
                try:
                    return PermissionMode(mode_value)
                except ValueError:
                    self._logger.warning(f"Invalid permission mode '{mode_value}', returning DEFAULT")
                    return PermissionMode.DEFAULT
                    
        except Exception as exc:
            self._logger.error(f"Error getting permission mode for session {session_id}: {str(exc)}")
            return PermissionMode.DEFAULT
    
    async def set_permission_mode(
        self,
        session_id: str,
        mode: Any,
        pre_plan_mode: Any | None = None
    ) -> None:
        """Set permission mode for session with optional pre-plan snapshot.
        
        Args:
            session_id: Session identifier
            mode: New PermissionMode to set
            pre_plan_mode: Optional snapshot of mode before entering Plan Mode
        """
        self.log_operation(
            "set_permission_mode",
            session_id=session_id,
            mode=mode.value if hasattr(mode, "value") else str(mode),
            pre_plan_mode=pre_plan_mode.value if pre_plan_mode and hasattr(pre_plan_mode, "value") else None
        )
        
        try:
            async with get_db_session() as session:
                chat_session = await session.get(ChatSession, session_id)
                if not chat_session:
                    raise ValueError(f"Session {session_id} not found")
                
                # Update metadata with new mode
                metadata = self._session_metadata(session_id)
                metadata["permission_mode"] = mode.value if hasattr(mode, "value") else str(mode)
                
                # Save pre-plan mode snapshot if provided
                if pre_plan_mode is not None:
                    metadata["pre_plan_mode"] = pre_plan_mode.value if hasattr(pre_plan_mode, "value") else str(pre_plan_mode)
                
                chat_session.updated_at = datetime.now(UTC)
                await session.commit()
                
                self._logger.info(
                    f"Permission mode updated for session {session_id}: "
                    f"mode={metadata['permission_mode']}, "
                    f"pre_plan_mode={metadata.get('pre_plan_mode')}"
                )
                
        except Exception as exc:
            self._logger.error(f"Error setting permission mode for session {session_id}: {str(exc)}")
            raise
    
    async def exit_plan_mode(
        self,
        session_id: str,
        action: str
    ) -> Any:
        """Exit plan mode, restoring pre-plan mode or proceeding.
        
        Args:
            session_id: Session identifier
            action: "confirm" to execute plan, "reject" to restore previous mode
            
        Returns:
            The PermissionMode to switch to after exiting Plan Mode
        """
        from mindflow_backend.permissions.types import PermissionMode
        
        self.log_operation("exit_plan_mode", session_id=session_id, action=action)
        
        try:
            async with get_db_session() as session:
                chat_session = await session.get(ChatSession, session_id)
                if not chat_session:
                    raise ValueError(f"Session {session_id} not found")
                
                metadata = self._session_metadata(session_id)
                pre_plan_mode_value = metadata.get("pre_plan_mode", PermissionMode.DEFAULT.value)
                
                # Determine target mode based on action
                if action == "confirm":
                    # After confirming plan, switch to ACCEPT_EDITS for execution
                    target_mode = PermissionMode.ACCEPT_EDITS
                else:
                    # After rejecting plan, restore previous mode
                    try:
                        target_mode = PermissionMode(pre_plan_mode_value)
                    except ValueError:
                        target_mode = PermissionMode.DEFAULT
                
                # Update metadata
                metadata["permission_mode"] = target_mode.value
                metadata.pop("pre_plan_mode", None)  # Clear pre-plan snapshot
                
                chat_session.updated_at = datetime.now(UTC)
                await session.commit()
                
                self._logger.info(
                    f"Exited Plan Mode for session {session_id}: "
                    f"action={action}, target_mode={target_mode.value}"
                )
                
                return target_mode
                
        except Exception as exc:
            self._logger.error(f"Error exiting plan mode for session {session_id}: {str(exc)}")
            return PermissionMode.DEFAULT
