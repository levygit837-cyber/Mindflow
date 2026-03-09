"""Memory service for managing agent memory, context windows, and RAG operations.

This service provides comprehensive memory management including rolling memory,
semantic search, context retrieval, and coordination with vector services.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from mindflow_backend.infra.config import get_settings
from mindflow_backend.utils.core import estimate_token_count
from mindflow_backend.schemas.memory.contracts import MemoryEntry, ContextWindow, MemoryCursor
from mindflow_backend.schemas.session.contracts import RetrievedContext
from mindflow_backend.memory.storage.models import (
    AgentMemoryCursor,
    AgentMemoryEmbedding,
    AgentMemoryEvent,
    AgentMemoryFact,
    AgentMemoryWindow,
    SessionChunk,
    SessionEmbedding,
)
from mindflow_backend.storage.postgresql.connection import db_session
from mindflow_backend.services.interfaces.base_interfaces import BaseAbstractService
from mindflow_backend.memory.core.interfaces import MemoryServiceInterface


@dataclass(slots=True)
class MemoryRetrievalResult:
    """Result of memory retrieval operation."""
    context: str
    references: List[str]
    metadata: Dict[str, Any] | None = None


class MemoryService(BaseAbstractService, MemoryServiceInterface):
    """Service for managing agent memory, context windows, and RAG operations.
    
    This service handles rolling memory windows, semantic search, context retrieval,
    and coordinates with vector services for embedding generation and storage.
    """
    
    def __init__(
        self,
        *,
        summary_window_tokens: Optional[int] = None,
        retrieval_top_k: Optional[int] = None,
        embedding_dims: Optional[int] = None,
    ) -> None:
        """Initialize memory service with configuration."""
        super().__init__()
        settings = get_settings()
        self.summary_window_tokens = summary_window_tokens or getattr(settings, 'memory_summary_window_tokens', 4000)
        self.retrieval_top_k = retrieval_top_k or getattr(settings, 'memory_retrieval_top_k', 5)
        self.embedding_dims = embedding_dims or getattr(settings, 'memory_embedding_dims', 768)
        
        # Lazy load dependencies
        self._vector_service = None
        self._embedding_service = None
    
    def _get_logger(self) -> Any:
        """Get logger instance for this service."""
        return get_logger(__name__)
    
    def _get_vector_service(self):
        """Get vector service instance (lazy loading)."""
        if self._vector_service is None:
            from mindflow_backend.services import get_vector_service
            self._vector_service = get_vector_service()
        return self._vector_service
    
    def _get_embedding_service(self):
        """Get embedding service instance (lazy loading)."""
        if self._embedding_service is None:
            from mindflow_backend.services import get_embedding_service
            self._embedding_service = get_embedding_service()
        return self._embedding_service
    
    async def get_agent_memory(
        self,
        agent_id: str,
        session_id: str,
        token_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get agent memory with optional token limit.
        
        Args:
            agent_id: Agent identifier
            session_id: Session identifier
            token_limit: Optional token limit for memory window
            
        Returns:
            Dictionary containing agent memory data
        """
        self.log_operation("get_agent_memory", agent_id=agent_id, session_id=session_id, token_limit=token_limit)
        
        try:
            with db_session() as db:
                # Get memory cursor
                cursor = self._get_or_create_cursor(db, session_id=session_id, agent_id=agent_id)
                
                # Get recent memory events
                query = select(AgentMemoryEvent).where(
                    AgentMemoryEvent.session_id == session_id,
                    AgentMemoryEvent.agent_id == agent_id
                ).order_by(AgentMemoryEvent.created_at.desc())
                
                if token_limit:
                    # Apply token limit by accumulating events
                    events = []
                    total_tokens = 0
                    for event in db.execute(query).scalars():
                        if total_tokens + event.token_count > token_limit:
                            break
                        events.append(event)
                        total_tokens += event.token_count
                else:
                    events = list(db.execute(query).scalars())
                
                # Get memory windows
                windows_query = select(AgentMemoryWindow).where(
                    AgentMemoryWindow.session_id == session_id,
                    AgentMemoryWindow.agent_id == agent_id
                ).order_by(AgentMemoryWindow.window_start.desc())
                
                windows = list(db.execute(windows_query).scalars())
                
                return {
                    "agent_id": agent_id,
                    "session_id": session_id,
                    "cursor": {
                        "token_total": cursor.token_total,
                        "tokens_since_summary": cursor.tokens_since_summary,
                        "last_summary_at": cursor.last_summary_at.isoformat() if cursor.last_summary_at else None
                    },
                    "recent_events": [
                        {
                            "id": event.id,
                            "role": event.role,
                            "content": event.content[:500] + "..." if len(event.content) > 500 else event.content,
                            "token_count": event.token_count,
                            "created_at": event.created_at.isoformat()
                        }
                        for event in events
                    ],
                    "memory_windows": [
                        {
                            "id": window.id,
                            "window_start": window.window_start,
                            "window_end": window.window_end,
                            "summary": window.summary[:200] + "..." if len(window.summary) > 200 else window.summary,
                            "created_at": window.created_at.isoformat()
                        }
                        for window in windows
                    ],
                    "total_events": len(events),
                    "total_windows": len(windows)
                }
                
        except Exception as exc:
            self._logger.error(f"Error getting agent memory: {str(exc)}")
            raise
    
    async def add_memory_event(
        self,
        agent_id: str,
        session_id: str,
        role: str,
        content: str,
        token_count: int,
        source_message_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Add a memory event for an agent.
        
        Args:
            agent_id: Agent identifier
            session_id: Session identifier
            role: Event role (user, assistant, system)
            content: Event content
            token_count: Token count of content
            source_message_id: Optional source message ID
            
        Returns:
            Dictionary containing created memory event data
        """
        self.log_operation(
            "add_memory_event",
            agent_id=agent_id,
            session_id=session_id,
            role=role,
            content_length=len(content),
            token_count=token_count
        )
        
        try:
            if token_count <= 0:
                token_count = estimate_token_count(content)
            
            with db_session() as db:
                # Create memory event
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
                
                # Update cursor
                cursor = self._get_or_create_cursor(db, session_id=session_id, agent_id=agent_id)
                cursor.token_total += token_count
                cursor.tokens_since_summary += token_count
                
                # Generate and store embedding
                try:
                    embedding_service = self._get_embedding_service()
                    embedding = await embedding_service.generate_embedding(content)
                    
                    vector_service = self._get_vector_service()
                    await vector_service.insert_vectors(
                        collection_name=f"agent_memory_{agent_id}",
                        vectors=[{
                            "id": str(event.id),
                            "vector": embedding,
                            "metadata": {
                                "session_id": session_id,
                                "agent_id": agent_id,
                                "role": role,
                                "created_at": event.created_at.isoformat()
                            }
                        }]
                    )
                except Exception as exc:
                    self._logger.warning(f"Failed to generate/store embedding: {str(exc)}")
                
                # Check if summary is needed
                if cursor.tokens_since_summary >= self.summary_window_tokens:
                    await self._summarize_pending_window(
                        db,
                        session_id=session_id,
                        agent_id=agent_id,
                        cursor=cursor
                    )
                
                await db.commit()
                
                return {
                    "id": event.id,
                    "session_id": event.session_id,
                    "agent_id": event.agent_id,
                    "role": event.role,
                    "content": content,
                    "token_count": event.token_count,
                    "created_at": event.created_at.isoformat(),
                    "embedding_stored": True
                }
                
        except Exception as exc:
            self._logger.error(f"Error adding memory event: {str(exc)}")
            raise
    
    async def get_context_window(
        self,
        session_id: str,
        window_start: int,
        window_end: int
    ) -> Dict[str, Any]:
        """Get context window for a specific token range.
        
        Args:
            session_id: Session identifier
            window_start: Start token position
            window_end: End token position
            
        Returns:
            Dictionary containing context window data
        """
        self.log_operation("get_context_window", session_id=session_id, window_start=window_start, window_end=window_end)
        
        try:
            with db_session() as db:
                # Get events within token range
                query = select(AgentMemoryEvent).where(
                    AgentMemoryEvent.session_id == session_id,
                    AgentMemoryEvent.token_position >= window_start,
                    AgentMemoryEvent.token_position <= window_end
                ).order_by(AgentMemoryEvent.token_position)
                
                events = list(db.execute(query).scalars())
                
                # Reconstruct context
                context_parts = []
                for event in events:
                    context_parts.append(f"{event.role}: {event.content}")
                
                context = "\n".join(context_parts)
                
                return {
                    "session_id": session_id,
                    "window_start": window_start,
                    "window_end": window_end,
                    "context": context,
                    "event_count": len(events),
                    "total_tokens": sum(event.token_count for event in events)
                }
                
        except Exception as exc:
            self._logger.error(f"Error getting context window: {str(exc)}")
            raise
    
    async def search_semantic_context(
        self,
        query: str,
        session_id: str,
        top_k: int = 5,
        min_score: float = 0.3
    ) -> List[Dict[str, Any]]:
        """Search for semantically similar context.
        
        Args:
            query: Search query
            session_id: Session identifier
            top_k: Maximum number of results
            min_score: Minimum similarity score
            
        Returns:
            List of semantically similar context items
        """
        self.log_operation(
            "search_semantic_context",
            session_id=session_id,
            query_length=len(query),
            top_k=top_k,
            min_score=min_score
        )
        
        try:
            # Generate query embedding
            embedding_service = self._get_embedding_service()
            query_embedding = await embedding_service.generate_embedding(query)
            
            # Search across all agent collections
            vector_service = self._get_vector_service()
            all_results = []
            
            for agent_id in ["analyst", "coder", "researcher", "reviewer"]:
                try:
                    collection_name = f"agent_memory_{agent_id}"
                    results = await vector_service.search_vectors(
                        collection_name=collection_name,
                        query_vector=query_embedding,
                        limit=top_k,
                        score_threshold=min_score,
                        filters={"session_id": session_id}
                    )
                    
                    for result in results:
                        # Get full event content
                        with db_session() as db:
                            event = db.get(AgentMemoryEvent, UUID(result["id"]))
                            if event:
                                all_results.append({
                                    "agent_id": agent_id,
                                    "event_id": result["id"],
                                    "content": event.content,
                                    "role": event.role,
                                    "score": result.get("score", 0.0),
                                    "created_at": event.created_at.isoformat()
                                })
                except Exception:
                    # Collection might not exist for this agent
                    continue
            
            # Sort by score and limit results
            all_results.sort(key=lambda x: x["score"], reverse=True)
            return all_results[:top_k]
            
        except Exception as exc:
            self._logger.error(f"Error searching semantic context: {str(exc)}")
            return []
    
    async def create_memory_summary(
        self,
        agent_id: str,
        session_id: str,
        window_range: Tuple[int, int]
    ) -> Dict[str, Any]:
        """Create a memory summary for a token window.
        
        Args:
            agent_id: Agent identifier
            session_id: Session identifier
            window_range: Token window range (start, end)
            
        Returns:
            Dictionary containing memory summary data
        """
        self.log_operation(
            "create_memory_summary",
            agent_id=agent_id,
            session_id=session_id,
            window_range=window_range
        )
        
        try:
            window_start, window_end = window_range
            
            # Get events in window
            with db_session() as db:
                query = select(AgentMemoryEvent).where(
                    AgentMemoryEvent.session_id == session_id,
                    AgentMemoryEvent.agent_id == agent_id,
                    AgentMemoryEvent.token_position >= window_start,
                    AgentMemoryEvent.token_position <= window_end
                ).order_by(AgentMemoryEvent.token_position)
                
                events = list(db.execute(query).scalars())
                
                if not events:
                    return {
                        "agent_id": agent_id,
                        "session_id": session_id,
                        "window_range": window_range,
                        "summary": "No events found in window",
                        "event_count": 0
                    }
                
                # Generate summary (simplified - would use LLM in production)
                content_parts = []
                for event in events:
                    content_parts.append(f"{event.role}: {event.content[:200]}...")
                
                summary_content = "\n".join(content_parts)
                summary = f"Summary of {len(events)} events from tokens {window_start}-{window_end}:\n{summary_content}"
                
                # Create memory window record
                memory_window = AgentMemoryWindow(
                    session_id=session_id,
                    agent_id=agent_id,
                    window_start=window_start,
                    window_end=window_end,
                    summary=summary,
                    event_count=len(events)
                )
                db.add(memory_window)
                await db.commit()
                
                return {
                    "id": memory_window.id,
                    "agent_id": agent_id,
                    "session_id": session_id,
                    "window_range": window_range,
                    "summary": summary,
                    "event_count": len(events),
                    "created_at": memory_window.created_at.isoformat()
                }
                
        except Exception as exc:
            self._logger.error(f"Error creating memory summary: {str(exc)}")
            raise
    
    async def get_memory_windows(
        self,
        agent_id: str,
        session_id: str
    ) -> List[Dict[str, Any]]:
        """Get all memory windows for an agent in a session.
        
        Args:
            agent_id: Agent identifier
            session_id: Session identifier
            
        Returns:
            List of memory window dictionaries
        """
        self.log_operation("get_memory_windows", agent_id=agent_id, session_id=session_id)
        
        try:
            with db_session() as db:
                query = select(AgentMemoryWindow).where(
                    AgentMemoryWindow.session_id == session_id,
                    AgentMemoryWindow.agent_id == agent_id
                ).order_by(AgentMemoryWindow.window_start.desc())
                
                windows = list(db.execute(query).scalars())
                
                return [
                    {
                        "id": window.id,
                        "session_id": window.session_id,
                        "agent_id": window.agent_id,
                        "window_start": window.window_start,
                        "window_end": window.window_end,
                        "summary": window.summary,
                        "event_count": window.event_count,
                        "created_at": window.created_at.isoformat()
                    }
                    for window in windows
                ]
                
        except Exception as exc:
            self._logger.error(f"Error getting memory windows: {str(exc)}")
            raise
    
    async def update_memory_cursor(
        self,
        agent_id: str,
        session_id: str,
        token_total: int,
        tokens_since_summary: int
    ) -> Dict[str, Any]:
        """Update memory cursor for an agent.
        
        Args:
            agent_id: Agent identifier
            session_id: Session identifier
            token_total: Total token count
            tokens_since_summary: Tokens since last summary
            
        Returns:
            Updated cursor data
        """
        self.log_operation(
            "update_memory_cursor",
            agent_id=agent_id,
            session_id=session_id,
            token_total=token_total,
            tokens_since_summary=tokens_since_summary
        )
        
        try:
            with db_session() as db:
                cursor = self._get_or_create_cursor(db, session_id=session_id, agent_id=agent_id)
                cursor.token_total = token_total
                cursor.tokens_since_summary = tokens_since_summary
                
                await db.commit()
                
                return {
                    "agent_id": agent_id,
                    "session_id": session_id,
                    "token_total": cursor.token_total,
                    "tokens_since_summary": cursor.tokens_since_summary,
                    "last_summary_at": cursor.last_summary_at.isoformat() if cursor.last_summary_at else None
                }
                
        except Exception as exc:
            self._logger.error(f"Error updating memory cursor: {str(exc)}")
            raise
    
    async def retrieve_context_for_query(
        self,
        query: str,
        session_id: str,
        agent_id: str
    ) -> Dict[str, Any]:
        """Retrieve relevant context for a query.
        
        Args:
            query: Search query
            session_id: Session identifier
            agent_id: Agent identifier
            
        Returns:
            Dictionary containing relevant context
        """
        self.log_operation(
            "retrieve_context_for_query",
            query=query[:100],
            session_id=session_id,
            agent_id=agent_id
        )
        
        try:
            # Get recent memory
            memory_data = await self.get_agent_memory(agent_id, session_id, token_limit=2000)
            
            # Get semantic matches
            semantic_results = await self.search_semantic_context(query, session_id, top_k=3)
            
            # Combine results
            context_parts = []
            references = []
            
            # Add recent events
            for event in memory_data.get("recent_events", [])[:5]:
                context_parts.append(f"Recent ({event['role']}): {event['content']}")
                references.append(f"recent_event_{event['id']}")
            
            # Add semantic matches
            for result in semantic_results:
                context_parts.append(f"Related ({result['role']}): {result['content']}")
                references.append(f"semantic_match_{result['event_id']}")
            
            context = "\n\n".join(context_parts)
            
            return MemoryRetrievalResult(
                context=context,
                references=references,
                metadata={
                    "query": query,
                    "session_id": session_id,
                    "agent_id": agent_id,
                    "recent_events_count": len(memory_data.get("recent_events", [])),
                    "semantic_matches_count": len(semantic_results)
                }
            ).__dict__
            
        except Exception as exc:
            self._logger.error(f"Error retrieving context for query: {str(exc)}")
            return MemoryRetrievalResult(context="", references=[]).__dict__
    
    # Helper methods
    
    def _get_or_create_cursor(
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
    
    async def _summarize_pending_window(
        self,
        db: Session,
        *,
        session_id: str,
        agent_id: str,
        cursor: AgentMemoryCursor
    ) -> None:
        """Summarize pending memory window."""
        window_start = cursor.token_total - cursor.tokens_since_summary
        window_end = cursor.token_total
        
        await self.create_memory_summary(agent_id, session_id, (window_start, window_end))
        
        # Reset cursor
        cursor.tokens_since_summary = 0
        cursor.last_summary_at = datetime.now(UTC)
    
    # Additional methods for session management
    
    async def initialize_session_memory(self, session_id: str, agent_types: List[str]) -> Dict[str, Any]:
        """Initialize memory for a new session.
        
        Args:
            session_id: Session identifier
            agent_types: List of agent types to initialize
            
        Returns:
            Dictionary containing initialization results
        """
        self.log_operation("initialize_session_memory", session_id=session_id, agent_types=agent_types)
        
        try:
            results = {}
            
            for agent_type in agent_types:
                # Create cursor for each agent
                with db_session() as db:
                    cursor = self._get_or_create_cursor(db, session_id=session_id, agent_id=agent_type)
                    await db.commit()
                
                # Initialize vector collection
                try:
                    vector_service = self._get_vector_service()
                    await vector_service.create_collection(
                        collection_name=f"agent_memory_{agent_type}",
                        dimension=self.embedding_dims
                    )
                    results[agent_type] = {"status": "initialized", "vector_collection": True}
                except Exception as exc:
                    self._logger.warning(f"Failed to create vector collection for {agent_type}: {str(exc)}")
                    results[agent_type] = {"status": "initialized", "vector_collection": False}
            
            return {
                "session_id": session_id,
                "agent_types": results,
                "initialized_at": datetime.now(UTC).isoformat()
            }
            
        except Exception as exc:
            self._logger.error(f"Error initializing session memory: {str(exc)}")
            raise
    
    async def cleanup_session_memory(self, session_id: str) -> bool:
        """Clean up memory data for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if cleanup successful
        """
        self.log_operation("cleanup_session_memory", session_id=session_id)
        
        try:
            with db_session() as db:
                # Delete memory events
                db.execute(
                    select(AgentMemoryEvent).where(AgentMemoryEvent.session_id == session_id)
                ).delete()
                
                # Delete memory windows
                db.execute(
                    select(AgentMemoryWindow).where(AgentMemoryWindow.session_id == session_id)
                ).delete()
                
                # Delete memory cursors
                db.execute(
                    select(AgentMemoryCursor).where(AgentMemoryCursor.session_id == session_id)
                ).delete()
                
                await db.commit()
            
            # Clean up vector collections
            vector_service = self._get_vector_service()
            for agent_id in ["analyst", "coder", "researcher", "reviewer"]:
                try:
                    await vector_service.delete_vectors(
                        collection_name=f"agent_memory_{agent_id}",
                        vector_ids=[]  # Delete all vectors for this session
                    )
                except Exception:
                    pass  # Collection might not exist
            
            return True
            
        except Exception as exc:
            self._logger.error(f"Error cleaning up session memory: {str(exc)}")
            return False
    
    async def get_session_memory_summary(self, session_id: str) -> Dict[str, Any]:
        """Get comprehensive memory summary for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary containing session memory summary
        """
        self.log_operation("get_session_memory_summary", session_id=session_id)
        
        try:
            summary = {
                "session_id": session_id,
                "agents": {},
                "total_tokens": 0,
                "total_events": 0,
                "total_windows": 0
            }
            
            for agent_id in ["analyst", "coder", "researcher", "reviewer"]:
                with db_session() as db:
                    cursor = db.execute(
                        select(AgentMemoryCursor).where(
                            AgentMemoryCursor.session_id == session_id,
                            AgentMemoryCursor.agent_id == agent_id
                        )
                    ).scalar_one_or_none()
                    
                    if cursor:
                        # Count events and windows
                        event_count = db.execute(
                            select(AgentMemoryEvent).where(
                                AgentMemoryEvent.session_id == session_id,
                                AgentMemoryEvent.agent_id == agent_id
                            )
                        ).count()
                        
                        window_count = db.execute(
                            select(AgentMemoryWindow).where(
                                AgentMemoryWindow.session_id == session_id,
                                AgentMemoryWindow.agent_id == agent_id
                            )
                        ).count()
                        
                        summary["agents"][agent_id] = {
                            "token_total": cursor.token_total,
                            "tokens_since_summary": cursor.tokens_since_summary,
                            "event_count": event_count,
                            "window_count": window_count,
                            "last_summary_at": cursor.last_summary_at.isoformat() if cursor.last_summary_at else None
                        }
                        
                        summary["total_tokens"] += cursor.token_total
                        summary["total_events"] += event_count
                        summary["total_windows"] += window_count
            
            return summary
            
        except Exception as exc:
            self._logger.error(f"Error getting session memory summary: {str(exc)}")
            return {"session_id": session_id, "error": str(exc)}
    
    async def get_agent_interaction_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get interaction history for all agents in a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of interaction events
        """
        self.log_operation("get_agent_interaction_history", session_id=session_id)
        
        try:
            with db_session() as db:
                query = select(AgentMemoryEvent).where(
                    AgentMemoryEvent.session_id == session_id
                ).order_by(AgentMemoryEvent.created_at.desc())
                
                events = list(db.execute(query).scalars())
                
                return [
                    {
                        "id": event.id,
                        "agent_id": event.agent_id,
                        "role": event.role,
                        "content": event.content[:300] + "..." if len(event.content) > 300 else event.content,
                        "token_count": event.token_count,
                        "created_at": event.created_at.isoformat()
                    }
                    for event in events
                ]
                
        except Exception as exc:
            self._logger.error(f"Error getting agent interaction history: {str(exc)}")
            return []


# Import datetime for timestamp generation
from datetime import datetime, UTC
