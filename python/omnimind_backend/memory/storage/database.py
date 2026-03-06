"""Memory database operations."""

from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from omnimind_backend.infra.logging import get_logger
from omnimind_backend.storage.postgresql.connection import db_session
from .models import (
    AgentMemoryCursor,
    AgentMemoryEmbedding,
    AgentMemoryEvent,
    AgentMemoryFact,
    AgentMemoryWindow,
    SessionChunk,
    SessionEmbedding,
)

_logger = get_logger(__name__)


class MemoryDatabase:
    """Database operations for memory management."""
    
    def __init__(self):
        self.logger = _logger
    
    def get_or_create_cursor(
        self,
        db: Session,
        *,
        session_id: str,
        agent_id: str
    ) -> AgentMemoryCursor:
        """Get or create memory cursor for agent session."""
        cursor = db.execute(
            select(AgentMemoryCursor).where(
                AgentMemoryCursor.session_id == session_id,
                AgentMemoryCursor.agent_id == agent_id
            )
        ).scalar_one_or_none()
        
        if not cursor:
            cursor = AgentMemoryCursor(
                session_id=session_id,
                agent_id=agent_id,
                token_total=0,
                tokens_since_summary=0
            )
            db.add(cursor)
            db.flush()
        
        return cursor
    
    def get_memory_events(
        self,
        db: Session,
        session_id: str,
        agent_id: str,
        limit: Optional[int] = None
    ) -> List[AgentMemoryEvent]:
        """Get memory events for agent session."""
        query = select(AgentMemoryEvent).where(
            AgentMemoryEvent.session_id == session_id,
            AgentMemoryEvent.agent_id == agent_id
        ).order_by(AgentMemoryEvent.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return list(db.execute(query).scalars())
    
    def get_memory_windows(
        self,
        db: Session,
        session_id: str,
        agent_id: str
    ) -> List[AgentMemoryWindow]:
        """Get memory windows for agent session."""
        query = select(AgentMemoryWindow).where(
            AgentMemoryWindow.session_id == session_id,
            AgentMemoryWindow.agent_id == agent_id
        ).order_by(AgentMemoryWindow.window_start.desc())
        
        return list(db.execute(query).scalars())
    
    def get_memory_embeddings(
        self,
        db: Session,
        session_id: str,
        agent_id: str,
        limit: int = 512
    ) -> List[AgentMemoryEmbedding]:
        """Get memory embeddings for agent session."""
        query = select(AgentMemoryEmbedding).where(
            AgentMemoryEmbedding.session_id == session_id,
            AgentMemoryEmbedding.agent_id == agent_id
        ).order_by(AgentMemoryEmbedding.id.desc()).limit(limit)
        
        return list(db.execute(query).scalars())
    
    def get_session_chunks(
        self,
        db: Session,
        session_id: str,
        agent_id: str,
        limit: Optional[int] = None
    ) -> List[SessionChunk]:
        """Get session chunks for agent session."""
        query = select(SessionChunk).where(
            SessionChunk.session_id == session_id,
            SessionChunk.agent_id == agent_id
        ).order_by(SessionChunk.sequence.desc())
        
        if limit:
            query = query.limit(limit)
        
        return list(db.execute(query).scalars())
    
    def create_memory_event(
        self,
        db: Session,
        session_id: str,
        agent_id: str,
        role: str,
        content: str,
        token_count: int,
        source_message_id: Optional[int] = None
    ) -> AgentMemoryEvent:
        """Create a new memory event."""
        event = AgentMemoryEvent(
            session_id=session_id,
            agent_id=agent_id,
            role=role,
            content=content,
            token_count=token_count,
            source_message_id=source_message_id,
        )
        db.add(event)
        db.flush()
        return event
    
    def create_memory_embedding(
        self,
        db: Session,
        session_id: str,
        agent_id: str,
        source_type: str,
        source_id: int,
        content_excerpt: str,
        vector: List[float]
    ) -> AgentMemoryEmbedding:
        """Create a new memory embedding."""
        embedding = AgentMemoryEmbedding(
            session_id=session_id,
            agent_id=agent_id,
            source_type=source_type,
            source_id=source_id,
            content_excerpt=content_excerpt[:1500],
            vector=vector,
        )
        db.add(embedding)
        db.flush()
        return embedding
    
    def create_memory_window(
        self,
        db: Session,
        session_id: str,
        agent_id: str,
        window_index: int,
        token_start: int,
        token_end: int,
        event_start_id: int,
        event_end_id: int,
        summary_md: str,
        key_points: List[str],
        checksum: str
    ) -> AgentMemoryWindow:
        """Create a new memory window."""
        window = AgentMemoryWindow(
            session_id=session_id,
            agent_id=agent_id,
            window_index=window_index,
            token_start=token_start,
            token_end=token_end,
            event_start_id=event_start_id,
            event_end_id=event_end_id,
            summary_md=summary_md,
            key_points=key_points,
            coverage_ratio=1.0,
            checksum=checksum,
        )
        db.add(window)
        db.flush()
        return window
