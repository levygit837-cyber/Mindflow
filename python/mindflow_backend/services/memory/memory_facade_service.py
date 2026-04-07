"""Memory Facade Service - Service wrapper for the canonical MemoryFacade.

This module provides a service-layer wrapper around MemoryFacade that implements
the MemoryFacadeInterface and integrates with the service container.
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.memory.facade import MemoryFacade
from mindflow_backend.schemas.memory.contracts import (
    AgentMemorySnapshot,
    MemoryPersistResult,
    MemoryRecallRequest,
    MemoryRecallResponse,
    SessionBlockSchema,
)
from mindflow_backend.schemas.memory.annotation import MemoryAnnotation
from mindflow_backend.services.interfaces.base_interfaces import BaseAbstractService
from mindflow_backend.interfaces.services.memory import MemoryFacadeInterface

_logger = get_logger(__name__)


class MemoryFacadeService(BaseAbstractService, MemoryFacadeInterface):
    """Service wrapper for MemoryFacade implementing MemoryFacadeInterface.
    
    This service provides the canonical interface to the memory subsystem,
    delegating to MemoryFacade for all operations.
    """
    
    def __init__(self) -> None:
        """Initialize the memory facade service."""
        super().__init__()
        self._facade = MemoryFacade()
    
    def _get_logger(self) -> Any:
        """Get logger instance for this service."""
        return _logger
    
    async def record_message(
        self,
        db: Any,
        *,
        session_id: str,
        agent_id: str,
        role: str,
        content: str,
        source_message_id: int | None = None,
        idempotency_key: str | None = None,
        source_status: str = "final",
        derived_from_recall: bool = False,
    ) -> MemoryPersistResult:
        """Persist a message to agent memory and embed it immediately.
        
        Args:
            db: Database session
            session_id: Session identifier
            agent_id: Agent identifier
            role: Message role (user, assistant, system, etc.)
            content: Message content
            source_message_id: Optional source message ID for deduplication
            idempotency_key: Optional idempotency key
            source_status: Source status (final, partial, etc.)
            derived_from_recall: Whether content was derived from memory recall
            
        Returns:
            MemoryPersistResult with persistence details
        """
        self.log_operation(
            "record_message",
            session_id=session_id,
            agent_id=agent_id,
            role=role,
            has_content=bool(content),
        )
        
        return await self._facade.record_message(
            db,
            session_id=session_id,
            agent_id=agent_id,
            role=role,
            content=content,
            source_message_id=source_message_id,
            idempotency_key=idempotency_key,
            source_status=source_status,
            derived_from_recall=derived_from_recall,
        )
    
    async def recall(self, request: MemoryRecallRequest) -> MemoryRecallResponse:
        """Retrieve semantically relevant context for a query.
        
        Args:
            request: Memory recall request with query, session_id, and filters
            
        Returns:
            MemoryRecallResponse with context and hits
        """
        self.log_operation(
            "recall",
            session_id=request.session_id,
            agent_id=request.agent_id,
            query=request.query[:100] + "..." if len(request.query) > 100 else request.query,
        )
        
        return await self._facade.recall(request)
    
    async def get_agent_snapshot(
        self,
        session_id: str,
        agent_id: str,
        token_limit: int | None = None,
    ) -> AgentMemorySnapshot:
        """Return a lightweight snapshot of an agent's memory state.
        
        Args:
            session_id: Session identifier
            agent_id: Agent identifier
            token_limit: Optional token limit for the snapshot
            
        Returns:
            AgentMemorySnapshot with events and windows
        """
        self.log_operation(
            "get_agent_snapshot",
            session_id=session_id,
            agent_id=agent_id,
            token_limit=token_limit,
        )
        
        return await self._facade.get_agent_snapshot(
            session_id=session_id,
            agent_id=agent_id,
            token_limit=token_limit,
        )
    
    async def list_session_blocks(
        self,
        session_id: str,
        categories: list[str] | None = None,
        limit: int = 10,
    ) -> list[SessionBlockSchema]:
        """Return the latest categorical session blocks.
        
        Args:
            session_id: Session identifier
            categories: Optional list of categories to filter
            limit: Maximum number of blocks to return
            
        Returns:
            List of SessionBlockSchema
        """
        self.log_operation(
            "list_session_blocks",
            session_id=session_id,
            categories=categories,
            limit=limit,
        )
        
        return await self._facade.list_session_blocks(
            session_id=session_id,
            categories=categories,
            limit=limit,
        )
    
    async def save_annotation(self, annotation: MemoryAnnotation) -> None:
        """Save an annotation to memory.
        
        Args:
            annotation: MemoryAnnotation to save
        """
        self.log_operation(
            "save_annotation",
            session_id=annotation.session_id,
            agent_id=annotation.observer_agent_id,
            annotation_type=annotation.annotation_type,
        )
        
        await self._facade.save_annotation(annotation)


# Singleton instance
_memory_facade_service: MemoryFacadeService | None = None


def get_memory_facade_service() -> MemoryFacadeService:
    """Get the singleton MemoryFacadeService instance.
    
    Returns:
        MemoryFacadeService singleton instance
    """
    global _memory_facade_service
    if _memory_facade_service is None:
        _memory_facade_service = MemoryFacadeService()
    return _memory_facade_service


def reset_memory_facade_service() -> None:
    """Reset the singleton instance (useful for testing)."""
    global _memory_facade_service
    _memory_facade_service = None
