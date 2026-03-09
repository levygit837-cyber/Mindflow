"""Task Decomposer.

Integração com decomposition engine para processamento de tasks.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.orchestration.decomposition.decomposition_v2 import (
    MainTaskContract,
    SubTaskContract,
)
from mindflow_backend.services.interfaces.base_interfaces import BaseAbstractService

_logger = get_logger(__name__)


class TaskDecomposer(BaseAbstractService):
    """Decomposer para integração com decomposition engine."""
    
    def __init__(self) -> None:
        """Initialize Task Decomposer."""
        super().__init__()
        
        # Lazy load dependencies
        self._decomposition_engine = None
    
    def _get_logger(self) -> Any:
        """Get logger instance for this service."""
        return get_logger(__name__)
    
    def _get_decomposition_engine(self):
        """Get decomposition engine instance (lazy loading)."""
        if self._decomposition_engine is None:
            from mindflow_backend.decomposition.engine import TaskDecomposer as EngineTaskDecomposer
            self._decomposition_engine = EngineTaskDecomposer()
        return self._decomposition_engine
    
    async def decompose_task_with_memory(
        self,
        db: Session,
        task_description: str,
        session_id: str,
        agent_id: str,
        existing_context: Optional[str] = None,
    ) -> Tuple[MainTaskContract, List[SubTaskContract]]:
        """Decompor task usando contexto da memória."""
        self.log_operation(
            "decompose_task_with_memory",
            task_description=task_description[:100],
            session_id=session_id,
            agent_id=agent_id,
        )
        
        try:
            # Get relevant context from task memory
            memory_context = ""
            if existing_context:
                memory_context = f"Existing Context: {existing_context}\n\n"
            
            # Use decomposition engine with memory context
            decomposition_engine = self._get_decomposition_engine()
            main_task, sub_tasks = await decomposition_engine.decompose(
                message=memory_context + task_description,
                session_id=session_id,
                complexity_score=0.5,  # Default complexity
                memory_context=existing_context or "",
            )
            
            # Enhance subtasks with memory references
            enhanced_sub_tasks = []
            for sub_task in sub_tasks:
                enhanced_sub_tasks.append(SubTaskContract(
                    id=sub_task.id,
                    title=sub_task.title,
                    description=sub_task.description,
                    dependencies=sub_task.dependencies,
                    estimated_tokens=sub_task.estimated_tokens,
                    memory_reference=f"task_memory:{agent_id}:main_context",
                    context_requirements=sub_task.context_requirements,
                ))
            
            _logger.info(
                f"Task decomposed with memory",
                main_task_id=main_task.id,
                sub_tasks_count=len(enhanced_sub_tasks),
            )
            
            return main_task, enhanced_sub_tasks
            
        except Exception as exc:
            _logger.error(f"Failed to decompose task with memory: {exc}")
            # Return empty decomposition on error
            from mindflow_backend.schemas.orchestration.decomposition.decomposition_v2 import MainTaskContract, SubTaskContract
            
            empty_main = MainTaskContract(
                id="decomposition_failed",
                title="Task Decomposition Failed",
                description=task_description,
                complexity_score=0.5,
                estimated_tokens=100,
                dependencies=[],
                context_requirements=[],
            )
            
            return empty_main, []
