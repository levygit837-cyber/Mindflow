"""Task Integration.

Integração entre Task Memory e o sistema de orquestração.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.services.interfaces.base_interfaces import BaseAbstractService

_logger = get_logger(__name__)


class TaskIntegration(BaseAbstractService):
    """Integração entre Task Memory e orquestração."""
    
    def __init__(self) -> None:
        """Initialize Task Integration."""
        super().__init__()
        
        # Lazy load dependencies
        self._task_memory_service = None
        self._orchestrator_router = None
    
    def _get_logger(self) -> Any:
        """Get logger instance for this service."""
        return get_logger(__name__)
    
    def _get_task_memory_service(self):
        """Get task memory service instance (lazy loading)."""
        if self._task_memory_service is None:
            from mindflow_backend.memory.task_memory.service import TaskMemoryService
            self._task_memory_service = TaskMemoryService()
        return self._task_memory_service
    
    def _get_orchestrator_router(self):
        """Get orchestrator router instance (lazy loading)."""
        if self._orchestrator_router is None:
            from mindflow_backend.orchestrator.routing.intelligent_router import IntelligentRouter
            self._orchestrator_router = IntelligentRouter()
        return self._orchestrator_router
    
    async def store_task_execution_context(
        self,
        db: Session,
        *,
        task_id: str,
        execution_result: dict[str, Any],
        agent_id: str,
        session_id: str,
    ) -> str:
        """Armazenar contexto de execução de uma task."""
        self.log_operation(
            "store_task_execution_context",
            task_id=task_id,
            agent_id=agent_id,
        )
        
        try:
            task_memory_service = self._get_task_memory_service()
            
            # Add execution result as chunk
            content = f"Execution Result: {execution_result.get('result', 'No result')}"
            if execution_result.get('error'):
                content += f"\nError: {execution_result['error']}"
            
            chunk_id = await task_memory_service.add_task_chunk(
                db=db,
                task_memory_id=task_id,
                content=content,
                chunk_type="execution_result",
                keywords=["execution", "result"]
            )
            
            _logger.info(f"Task execution context stored: {chunk_id}")
            return chunk_id
            
        except Exception as exc:
            _logger.error(f"Failed to store task execution context: {exc}")
            raise
    
    async def get_task_for_decomposition(
        self,
        db: Session,
        task_id: str,
        agent_id: str,
    ) -> dict[str, Any] | None:
        """Obter task para decomposição com contexto completo."""
        self.log_operation(
            "get_task_for_decomposition",
            task_id=task_id,
            agent_id=agent_id,
        )
        
        try:
            task_memory_service = self._get_task_memory_service()
            
            # Get task memory and chunks
            task = await self._get_task_with_chunks(db, task_id)
            if not task:
                return None
            
            # Build context for decomposition
            context = {
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "priority": task.priority,
                "metadata": task.metadata,
                "chunks": [
                    {
                        "sequence": chunk.sequence,
                        "type": chunk.chunk_type,
                        "content": chunk.content,
                        "summary": chunk.summary,
                    }
                    for chunk in task.get("chunks", [])
                ]
            }
            
            _logger.info(f"Task context retrieved for decomposition: {task_id}")
            return context
            
        except Exception as exc:
            _logger.error(f"Failed to get task for decomposition: {exc}")
            return None
    
    async def _get_task_with_chunks(
        self,
        db: Session,
        task_id: str,
    ) -> dict[str, Any] | None:
        """Obter task com chunks."""
        try:
            from mindflow_backend.memory.task_memory.models import TaskChunk, TaskMemory
            
            task = db.scalar(
                select(TaskMemory).where(TaskMemory.task_id == task_id)
            )
            
            if not task:
                return None
            
            # Get chunks
            chunks = list(db.scalars(
                select(TaskChunk)
                .where(TaskChunk.task_memory_id == task_id)
                .order_by(TaskChunk.sequence.asc())
            ))
            
            return {
                "id": task.task_id,
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "priority": task.priority,
                "metadata": task.metadata,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "chunks": chunks
            }
            
        except Exception as exc:
            _logger.error(f"Failed to get task with chunks: {exc}")
            return None
