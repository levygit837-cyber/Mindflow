"""Task Retriever.

Recuperação semântica cross-task para memória de tasks.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.memory.task_memory.models import TaskMemory
from mindflow_backend.schemas.memory.contracts import MemoryRetrievalResult
from mindflow_backend.services.interfaces.base_interfaces import BaseAbstractService

_logger = get_logger(__name__)


class TaskRetriever(BaseAbstractService):
    """Retriever para memória de tasks."""
    
    def __init__(
        self,
        *,
        similarity_threshold: float = 0.7,
        max_results: int = 10,
    ) -> None:
        """Initialize Task Retriever."""
        super().__init__()
        self.similarity_threshold = similarity_threshold
        self.max_results = max_results
        
        # Lazy load dependencies
        self._vector_service = None
    
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
        if not hasattr(self, "_embedding_service") or self._embedding_service is None:
            from mindflow_backend.services import get_embedding_service
            self._embedding_service = get_embedding_service()
        return self._embedding_service
    
    async def retrieve_task_context(
        self,
        db: Session,
        task_id: str,
        query: str,
        context_limit: int = 5,
    ) -> MemoryRetrievalResult:
        """Recuperar contexto relevante de uma task."""
        self.log_operation(
            "retrieve_task_context",
            task_id=task_id,
            query=query,
        )
        
        try:
            vector_service = self._get_vector_service()
            
            # Generate query embedding
            query_embedding = await self._get_embedding_service().generate_embedding(query)
            
            # Search in task embeddings
            results = await vector_service.search_vectors(
                collection_name=f"task_context_{task_id}",
                query_vector=query_embedding,
                limit=context_limit,
                score_threshold=self.similarity_threshold,
            )
            
            if not results:
                return MemoryRetrievalResult(
                    context="",
                    references=[],
                    metadata={"task_id": task_id, "error": "No context found"}
                )
            
            # Build context from results
            context_parts = [f"Context for task {task_id}:"]
            references = []
            
            for result in results:
                content = result.get("content", "")
                if content:
                    context_parts.append(f"- {content}")
                    references.append(f"task_context:{result.get('id')}")
            
            context = "\n\n".join(context_parts)
            
            return MemoryRetrievalResult(
                context=context,
                references=references,
                metadata={
                    "task_id": task_id,
                    "result_count": len(results),
                    "retrieval_method": "semantic",
                }
            )
            
        except Exception as exc:
            _logger.error(f"Failed to retrieve task context: {exc}")
            return MemoryRetrievalResult(
                context="",
                references=[],
                metadata={"task_id": task_id, "error": str(exc)}
            )
    
    async def find_related_tasks(
        self,
        db: Session,
        task_id: str,
        max_depth: int = 3,
    ) -> list[dict[str, Any]]:
        """Encontrar tasks relacionadas por dependências."""
        self.log_operation(
            "find_related_tasks",
            task_id=task_id,
            max_depth=max_depth,
        )
        
        try:
            related_tasks = []
            visited = set()
            
            async def find_dependencies(current_task_id: str, depth: int):
                if depth >= max_depth or current_task_id in visited:
                    return
                
                visited.add(current_task_id)
                
                # Find child tasks
                child_tasks = list(db.scalars(
                    select(TaskMemory)
                    .where(TaskMemory.parent_task_id == current_task_id)
                ))
                
                for child in child_tasks:
                    related_tasks.append({
                        "task_id": child.task_id,
                        "title": child.title,
                        "relationship": "child",
                        "depth": depth + 1,
                    })
                    await find_dependencies(child.task_id, depth + 1)
            
            await find_dependencies(task_id, 0)
            
            return related_tasks
            
        except Exception as exc:
            _logger.error(f"Failed to find related tasks: {exc}")
            return []
