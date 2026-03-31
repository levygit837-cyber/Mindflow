"""Task Memory Service.

Serviço principal para gerenciar memória semântica de tasks e sub-tasks
com suporte a decomposição, dependências e recuperação cross-task.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.memory.shared.core.interfaces import MemoryServiceInterface
from mindflow_backend.memory.task_memory.models import (
    TaskChunk,
    TaskDependency,
    TaskEmbedding,
    TaskMemory,
)
from mindflow_backend.schemas.memory.contracts import MemoryRetrievalResult
from mindflow_backend.services.interfaces.base_interfaces import BaseAbstractService
from mindflow_backend.utils.core import estimate_token_count

_logger = get_logger(__name__)


class TaskMemoryService(BaseAbstractService, MemoryServiceInterface):
    """Serviço para gerenciar memória de tasks."""
    
    def __init__(
        self,
        *,
        embedding_dims: int | None = None,
        retrieval_top_k: int | None = None,
    ) -> None:
        """Initialize Task Memory service."""
        super().__init__()
        settings = get_settings()
        self.embedding_dims = embedding_dims or getattr(settings, 'task_embedding_dims', 768)
        self.retrieval_top_k = retrieval_top_k or getattr(settings, 'task_retrieval_top_k', 5)
        
        # Lazy load dependencies
        self._embedding_service = None
        self._vector_service = None
    
    def _get_logger(self) -> Any:
        """Get logger instance for this service."""
        return get_logger(__name__)
    
    def _get_embedding_provider(self):
        """Get embedding provider instance (lazy loading)."""
        if self._embedding_service is None:
            from mindflow_backend.memory.shared.embeddings import get_embedding_provider
            self._embedding_service = get_embedding_provider()
        return self._embedding_service
    
    async def create_task_memory(
        self,
        db: Session,
        *,
        task_id: str,
        title: str,
        description: str,
        parent_task_id: str | None = None,
        agent_id: str,
        session_id: str,
        priority: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Criar nova memória de task."""
        self.log_operation(
            "create_task_memory",
            task_id=task_id,
            parent_task_id=parent_task_id,
            agent_id=agent_id,
        )
        
        try:
            task_memory = TaskMemory(
                task_id=task_id,
                title=title,
                description=description,
                parent_task_id=parent_task_id,
                agent_id=agent_id,
                session_id=session_id,
                priority=priority,
                metadata=metadata or {},
                token_count=estimate_token_count(title + " " + description),
            )
            
            db.add(task_memory)
            db.flush()
            
            # Store embedding for task
            await self._store_task_embedding(
                db=db,
                task_memory_id=task_memory.id,
                content=title + " " + description,
                content_type="task"
            )
            
            _logger.info(f"Task memory created: {task_id}")
            return str(task_memory.id)
            
        except Exception as exc:
            _logger.error(f"Failed to create task memory: {exc}")
            raise
    
    async def add_task_chunk(
        self,
        db: Session,
        *,
        task_memory_id: str,
        content: str,
        chunk_type: str = "content",
        keywords: list[str] | None = None,
    ) -> str:
        """Adicionar chunk a uma task."""
        self.log_operation(
            "add_task_chunk",
            task_memory_id=task_memory_id,
            chunk_type=chunk_type,
        )
        
        try:
            # Get next sequence
            last_chunk = db.scalar(
                select(TaskChunk)
                .where(TaskChunk.task_memory_id == task_memory_id)
                .order_by(TaskChunk.sequence.desc())
                .limit(1)
            )
            
            sequence = (last_chunk.sequence + 1) if last_chunk else 1
            
            chunk = TaskChunk(
                task_memory_id=task_memory_id,
                sequence=sequence,
                chunk_type=chunk_type,
                content=content,
                summary=content[:500] + "..." if len(content) > 500 else content,
                keywords=keywords or [],
                token_count=estimate_token_count(content),
            )
            
            db.add(chunk)
            db.flush()
            
            # Store embedding for chunk
            await self._store_task_embedding(
                db=db,
                task_memory_id=task_memory_id,
                chunk_id=chunk.id,
                content=content,
                content_type="chunk"
            )
            
            _logger.info(f"Task chunk added: {chunk.id}")
            return str(chunk.id)
            
        except Exception as exc:
            _logger.error(f"Failed to add task chunk: {exc}")
            raise
    
    async def get_task_context(
        self,
        db: Session,
        *,
        task_id: str,
        query: str | None = None,
        max_chunks: int = 10,
    ) -> MemoryRetrievalResult:
        """Recuperar contexto de uma task específica."""
        self.log_operation(
            "get_task_context",
            task_id=task_id,
            query=query,
        )
        
        try:
            # Get task memory
            task_memory = db.scalar(
                select(TaskMemory)
                .where(TaskMemory.task_id == task_id)
            )
            
            if not task_memory:
                return MemoryRetrievalResult(
                    context="",
                    references=[],
                    metadata={"error": "Task not found"}
                )
            
            # Build context from task and chunks
            context_parts = [f"# {task_memory.title}"]
            context_parts.append(f"Description: {task_memory.description}")
            
            if query:
                context_parts.append(f"Query: {query}")
            
            # Get chunks
            chunks = list(db.scalars(
                select(TaskChunk)
                .where(TaskChunk.task_memory_id == task_memory.id)
                .order_by(TaskChunk.sequence.asc())
                .limit(max_chunks)
            ))
            
            if chunks:
                context_parts.append("\n## Context Chunks:")
                for chunk in chunks:
                    context_parts.append(f"- [{chunk.chunk_type}] {chunk.summary}")
            
            # Get related tasks
            related_tasks = await self._get_related_tasks(db, task_id)
            if related_tasks:
                context_parts.append("\n## Related Tasks:")
                for related in related_tasks:
                    context_parts.append(f"- {related.title}: {related.description[:100]}...")
            
            context = "\n\n".join(context_parts)
            references = [f"task:{task_memory.id}"] + [f"chunk:{c.id}" for c in chunks]
            
            return MemoryRetrievalResult(
                context=context,
                references=references,
                metadata={
                    "task_id": task_id,
                    "chunk_count": len(chunks),
                    "related_count": len(related_tasks),
                }
            )
            
        except Exception as exc:
            _logger.error(f"Failed to get task context: {exc}")
            return MemoryRetrievalResult(
                context="",
                references=[],
                metadata={"error": str(exc)}
            )
    
    async def _get_related_tasks(
        self,
        db: Session,
        task_id: str,
        max_results: int = 5,
    ) -> list[TaskMemory]:
        """Get tasks relacionadas."""
        try:
            # Get dependencies where this task is parent
            child_tasks = list(db.scalars(
                select(TaskMemory)
                .where(TaskMemory.parent_task_id == task_id)
                .limit(max_results)
            ))
            
            # Get dependencies where this task is child
            parent_tasks = list(db.scalars(
                select(TaskMemory)
                .where(TaskMemory.task_id.in_(
                    select(TaskDependency.child_task_id)
                    .where(TaskDependency.parent_task_id == task_id)
                    .subquery()
                ))
                .limit(max_results)
            ))
            
            return child_tasks + parent_tasks
            
        except Exception as exc:
            _logger.error(f"Failed to get related tasks: {exc}")
            return []
    
    async def _store_task_embedding(
        self,
        db: Session,
        *,
        task_memory_id: str,
        content: str,
        content_type: str = "task",
        chunk_id: str | None = None,
    ) -> None:
        """Armazenar embedding para task/chunk."""
        try:
            provider = self._get_embedding_provider()
            embedding = await provider.embed(content)
            
            task_embedding = TaskEmbedding(
                task_memory_id=task_memory_id,
                chunk_id=chunk_id,
                content_type=content_type,
                content=content,
                embedding=embedding,
            )
            
            db.add(task_embedding)
            db.flush()
            
        except Exception as exc:
            _logger.error(f"Failed to store task embedding: {exc}")
            # Don't raise - embedding failures shouldn't break operations
    
    async def search_tasks(
        self,
        db: Session,
        *,
        query: str,
        session_id: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Buscar tasks semanticamente usando pgvector direto."""
        self.log_operation(
            "search_tasks",
            query=query,
            session_id=session_id,
        )

        try:
            provider = self._get_embedding_provider()
            query_vec = await provider.embed(query)

            # Search via pgvector cosine distance on TaskEmbedding
            stmt = (
                select(TaskEmbedding, TaskMemory)
                .join(TaskMemory, TaskEmbedding.task_memory_id == TaskMemory.id)
                .order_by(TaskEmbedding.embedding.cosine_distance(query_vec))
                .limit(limit * 2)
            )

            if session_id:
                stmt = stmt.where(TaskMemory.session_id == session_id)

            rows = list(db.execute(stmt))
            results = []
            for task_emb, task_mem in rows:
                try:
                    distance = task_emb.embedding.cosine_distance(query_vec)
                except Exception:
                    distance = 1.0
                score = 1.0 - float(distance)
                if score < 0.2:
                    continue
                results.append({
                    "task_id": str(task_mem.task_id),
                    "title": task_mem.title,
                    "score": score,
                    "content": task_emb.content[:500],
                })
                if len(results) >= limit:
                    break

            return results

        except Exception as exc:
            _logger.error(f"Failed to search tasks: {exc}")
            return []
