"""Semantic Context Manager for intelligent context sharing between sub-tasks.

Manages semantic context storage, retrieval, and dependency resolution
for multi-agent orchestration with multilingual embeddings.

Also maintains a per-session **Task Registry** that indexes every MainTask and its
SubTasks so the Orchestrator can call ``get_tasks()`` to enumerate all work done in
a session and retrieve the full content of any MainTask by ``get_main_task_content()``.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID

from mindflow_backend.agents.context.vector_store import get_vector_store
from mindflow_backend.agents.core.interfaces import VectorStore
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.services.multilingual_embeddings import get_multilingual_embedding_service

if TYPE_CHECKING:
    from mindflow_backend.schemas.orchestration.decomposition.decomposition_v2 import (
        MainTaskContract,
        MainTaskSummary,
        SubTaskContract,
    )

_logger = get_logger(__name__)


class ContextMatch:
    """Represents a matched context result."""
    
    def __init__(
        self,
        content: str,
        similarity: float,
        task_id: Optional[str] = None,
        agent_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.content = content
        self.similarity = similarity
        self.task_id = task_id
        self.agent_type = agent_type
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "content": self.content,
            "similarity": self.similarity,
            "task_id": self.task_id,
            "agent_type": self.agent_type,
            "metadata": self.metadata,
        }


class ContextEntry:
    """Represents a context entry in the system."""
    
    def __init__(
        self,
        task_id: str,
        agent_type: str,
        content: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[str]] = None,
        created_at: Optional[datetime] = None,
    ):
        self.task_id = task_id
        self.agent_type = agent_type
        self.content = content
        self.embedding = embedding
        self.metadata = metadata or {}
        self.dependencies = dependencies or []
        self.created_at = created_at or datetime.now(UTC)
        self.updated_at = datetime.now(UTC)


class SemanticContextManager:
    """Manages semantic context between sub-tasks.
    
    Provides intelligent context storage, retrieval, and dependency resolution
    using multilingual embeddings for semantic search.
    """
    
    def __init__(self, vector_store: Optional[VectorStore] = None):
        """Initialize the semantic context manager.

        Args:
            vector_store: Vector store implementation. If None, uses global instance.
        """
        self.vector_store = vector_store
        self.embedding_service = None
        self.context_cache: Dict[str, ContextEntry] = {}
        self._lock = asyncio.Lock()
        self._initialized = False

        # Task Registry — keyed by session_id → main_task_id → MainTaskSummary
        # Populated by register_main_task(); queried by get_tasks().
        self._task_registry: Dict[str, Dict[str, Any]] = {}

        # Configuration
        settings = get_settings()
        self.similarity_threshold = getattr(settings, 'context_similarity_threshold', 0.7)
        self.max_context_wait_time = getattr(settings, 'max_context_wait_time', 30)
        self.enable_context_caching = getattr(settings, 'enable_context_caching', True)
        
    async def initialize(self) -> None:
        """Initialize the context manager and its dependencies."""
        if self._initialized:
            return
            
        async with self._lock:
            if self._initialized:
                return
                
            try:
                # Initialize vector store
                if self.vector_store is None:
                    self.vector_store = await get_vector_store()
                
                # Initialize embedding service
                self.embedding_service = await get_multilingual_embedding_service()
                
                self._initialized = True
                _logger.info("semantic_context_manager_initialized")
                
            except Exception as exc:
                _logger.error("failed_to_initialize_context_manager", error=str(exc))
                raise RuntimeError(f"Failed to initialize context manager: {exc}")
    
    async def store_task_context(
        self,
        task_id: str,
        agent_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[str]] = None,
    ) -> str:
        """Store context for a specific task.
        
        Args:
            task_id: Unique identifier for the task
            agent_type: Type of agent (coder, analyst, researcher, etc.)
            content: Text content to store
            metadata: Additional metadata about the context
            dependencies: List of task IDs this task depends on
            
        Returns:
            Vector ID of the stored context
        """
        if not self._initialized:
            await self.initialize()
            
        try:
            # Generate embedding for the content
            embedding = await self.embedding_service.generate_embedding(content)
            
            # Create context entry
            entry = ContextEntry(
                task_id=task_id,
                agent_type=agent_type,
                content=content,
                embedding=embedding,
                metadata=metadata,
                dependencies=dependencies,
            )
            
            # Cache if enabled
            if self.enable_context_caching:
                self.context_cache[task_id] = entry
            
            # Store in vector store
            session_id = metadata.get("session_id", "default") if metadata else "default"
            vector_id = await self.vector_store.store_subtask_context(
                session_id=session_id,
                task_id=task_id,
                agent_type=agent_type,
                content=content,
                embedding=embedding,
                metadata=metadata,
                dependencies=dependencies,
            )
            
            _logger.info(
                "task_context_stored",
                task_id=task_id,
                agent_type=agent_type,
                vector_id=vector_id,
                content_length=len(content),
            )
            
            return vector_id
            
        except Exception as exc:
            _logger.error("failed_to_store_task_context", task_id=task_id, error=str(exc))
            raise RuntimeError(f"Failed to store task context: {exc}")
    
    async def find_relevant_context(
        self,
        task_id: str,
        query: str,
        session_id: str = "default",
        dependency_task_ids: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[ContextMatch]:
        """Find context relevant to a specific task.
        
        Args:
            task_id: ID of the task seeking context
            query: Query text to search for relevant context
            session_id: Session ID for context isolation
            dependency_task_ids: Specific task IDs to prioritize
            limit: Maximum number of results to return
            
        Returns:
            List of context matches ordered by relevance
        """
        if not self._initialized:
            await self.initialize()
            
        try:
            # Generate embedding for query
            query_embedding = await self.embedding_service.generate_embedding(query)
            
            # Search for relevant context
            results = await self.vector_store.search_subtask_context(
                session_id=session_id,
                task_id=task_id,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=self.similarity_threshold,
                include_dependencies=True,
            )
            
            # Convert to ContextMatch objects
            matches = []
            for result in results:
                match = ContextMatch(
                    content=result["content"],
                    similarity=result["similarity"],
                    task_id=result.get("task_id"),
                    agent_type=result.get("agent_type"),
                    metadata=result.get("metadata", {}),
                )
                matches.append(match)
            
            # Prioritize dependency tasks if specified
            if dependency_task_ids:
                dependency_matches = [
                    match for match in matches 
                    if match.task_id in dependency_task_ids
                ]
                other_matches = [
                    match for match in matches 
                    if match.task_id not in dependency_task_ids
                ]
                matches = dependency_matches + other_matches
            
            _logger.info(
                "relevant_context_found",
                task_id=task_id,
                matches_found=len(matches),
                query_length=len(query),
            )
            
            return matches
            
        except Exception as exc:
            _logger.error("failed_to_find_relevant_context", task_id=task_id, error=str(exc))
            return []
    
    async def wait_for_context(
        self,
        task_id: str,
        required_context_ids: List[str],
        session_id: str = "default",
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Wait for required context to become available.
        
        Args:
            task_id: ID of the task waiting for context
            required_context_ids: List of task IDs to wait for
            session_id: Session ID for context isolation
            timeout: Maximum time to wait in seconds
            
        Returns:
            Dictionary with status and available context
        """
        if not self._initialized:
            await self.initialize()
            
        timeout = timeout or self.max_context_wait_time
        
        try:
            result = await self.vector_store.wait_for_task_context(
                session_id=session_id,
                task_id=task_id,
                required_task_ids=required_context_ids,
                timeout_seconds=timeout,
            )
            
            _logger.info(
                "context_wait_completed",
                task_id=task_id,
                status=result["status"],
                wait_time=result.get("wait_time", 0),
            )
            
            return result
            
        except Exception as exc:
            _logger.error("failed_to_wait_for_context", task_id=task_id, error=str(exc))
            return {
                "status": "error",
                "error": str(exc),
                "wait_time": timeout,
            }
    
    async def get_task_dependencies_context(
        self,
        task_id: str,
        dependency_task_ids: List[str],
        session_id: str = "default",
    ) -> List[ContextMatch]:
        """Get context from specific dependency tasks.
        
        Args:
            task_id: ID of the task requesting dependencies
            dependency_task_ids: List of dependency task IDs
            session_id: Session ID for context isolation
            
        Returns:
            List of context matches from dependency tasks
        """
        if not self._initialized:
            await self.initialize()
            
        try:
            contexts = await self.vector_store.get_task_dependencies_context(
                session_id=session_id,
                task_id=task_id,
                dependency_task_ids=dependency_task_ids,
            )
            
            # Convert to ContextMatch objects
            matches = []
            for ctx in contexts:
                match = ContextMatch(
                    content=ctx["content"],
                    similarity=1.0,  # Direct dependency gets max similarity
                    task_id=ctx["task_id"],
                    agent_type=ctx["agent_type"],
                    metadata=ctx.get("metadata", {}),
                )
                matches.append(match)
            
            _logger.info(
                "dependencies_context_retrieved",
                task_id=task_id,
                dependencies_found=len(matches),
                dependencies_requested=len(dependency_task_ids),
            )
            
            return matches
            
        except Exception as exc:
            _logger.error("failed_to_get_dependencies_context", task_id=task_id, error=str(exc))
            return []
    
    async def update_task_status(
        self,
        task_id: str,
        status: str,
        session_id: str = "default",
        completion_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update the status of a task.
        
        Args:
            task_id: ID of the task to update
            status: New status (pending, running, completed, failed)
            session_id: Session ID for context isolation
            completion_data: Additional data about task completion
        """
        if not self._initialized:
            await self.initialize()
            
        try:
            await self.vector_store.update_task_status(
                session_id=session_id,
                task_id=task_id,
                status=status,
                completion_data=completion_data,
            )
            
            # Update cache if present
            if task_id in self.context_cache:
                self.context_cache[task_id].metadata["task_status"] = status
                self.context_cache[task_id].updated_at = datetime.now(UTC)
            
            _logger.info(
                "task_status_updated",
                task_id=task_id,
                status=status,
                session_id=session_id,
            )
            
        except Exception as exc:
            _logger.error("failed_to_update_task_status", task_id=task_id, error=str(exc))
    
    async def get_cached_context(self, task_id: str) -> Optional[ContextEntry]:
        """Get cached context entry for a task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Context entry if found in cache, None otherwise
        """
        if not self.enable_context_caching:
            return None
            
        return self.context_cache.get(task_id)
    
    async def clear_cache(self, task_id: Optional[str] = None) -> None:
        """Clear context cache.
        
        Args:
            task_id: Specific task ID to clear, or None to clear all
        """
        if task_id:
            self.context_cache.pop(task_id, None)
            _logger.info("context_cache_cleared_for_task", task_id=task_id)
        else:
            self.context_cache.clear()
            _logger.info("context_cache_cleared_all")
    
    # ------------------------------------------------------------------
    # Task Registry — MainTask indexing and content retrieval
    # ------------------------------------------------------------------

    async def register_main_task(
        self,
        session_id: str,
        main_contract: "MainTaskContract",
        subtasks: "list[SubTaskContract]",
    ) -> None:
        """Register a MainTask and its SubTasks in the per-session task registry.

        Called by EnhancedTasker immediately after decomposition so the Orchestrator
        can enumerate all MainTasks via ``get_tasks()`` at any point.

        Args:
            session_id: Session identifier.
            main_contract: The MainTaskContract produced by the Tasker.
            subtasks: The list of SubTaskContracts that compose this MainTask.
        """
        from mindflow_backend.schemas.orchestration.decomposition.decomposition_v2 import (  # noqa: PLC0415
            MainTaskSummary,
            SubTaskSummary,
        )

        summary = MainTaskSummary(
            main_task_id=main_contract.main_task_id,
            goal=main_contract.goal,
            description=main_contract.description,
            subtasks=[
                SubTaskSummary(
                    task_id=st.task_id,
                    title=st.title,
                    owner_agent=st.owner_agent.value,
                    priority=st.priority,
                    status="pending",
                )
                for st in subtasks
            ],
            status="in_progress",
        )

        registry = self._task_registry.setdefault(session_id, {})
        registry[str(main_contract.main_task_id)] = summary

        _logger.info(
            "main_task_registered",
            session_id=session_id,
            main_task_id=str(main_contract.main_task_id),
            subtasks=len(subtasks),
        )

    async def get_tasks(self, session_id: str) -> "list[MainTaskSummary]":
        """Return all MainTasks registered for a session, ordered by creation time.

        Each entry includes the list of SubTaskSummaries that compose it, providing
        the Orchestrator with a hierarchical view of all work done in the session
        without requiring a full session history scan.

        Args:
            session_id: Session identifier.

        Returns:
            List of MainTaskSummary objects, oldest first.
        """
        registry = self._task_registry.get(session_id, {})
        summaries = list(registry.values())
        summaries.sort(key=lambda s: s.created_at)
        return summaries

    async def get_main_task_content(
        self,
        main_task_id: str,
        session_id: str = "default",
    ) -> str:
        """Retrieve the full content of a MainTask including all its SubTask results.

        Fetches each SubTask's stored content from the vector store by task_id,
        enabling the Orchestrator to perform semantic search scoped to a specific
        MainTask's subtasks rather than across the entire session.

        Args:
            main_task_id: UUID string of the MainTask.
            session_id: Session identifier.

        Returns:
            Formatted string with MainTask goal + all available SubTask results,
            or empty string if the MainTask is not registered.
        """
        if not self._initialized:
            await self.initialize()

        registry = self._task_registry.get(session_id, {})
        summary = registry.get(main_task_id)
        if not summary:
            return ""

        parts: list[str] = [
            f"## MainTask: {summary.goal}",
        ]
        if summary.description:
            parts.append(f"Description: {summary.description}")
        parts.append(f"Status: {summary.status} | SubTasks: {len(summary.subtasks)}")

        subtask_ids = [str(st.task_id) for st in summary.subtasks]
        if subtask_ids:
            try:
                dep_contexts = await self.vector_store.get_task_dependencies_context(
                    session_id=session_id,
                    task_id=f"maintask_{main_task_id}",
                    dependency_task_ids=subtask_ids,
                )
                if dep_contexts:
                    parts.append("\n### SubTask Results")
                    for ctx in dep_contexts:
                        label = f"{ctx.get('agent_type', 'agent')} / {ctx.get('task_id', '')}"
                        parts.append(f"\n**[{label}]**\n{ctx.get('content', '')}")
            except Exception as exc:
                _logger.warning(
                    "get_main_task_content_subtask_fetch_failed",
                    main_task_id=main_task_id,
                    error=str(exc),
                )

        return "\n\n".join(parts)

    async def complete_main_task(
        self,
        main_task_id: str,
        session_id: str,
        final_answer: str = "",
    ) -> None:
        """Mark a MainTask as completed in the registry.

        Args:
            main_task_id: UUID string of the MainTask.
            session_id: Session identifier.
            final_answer: The synthesized final answer (stored in metadata only).
        """
        registry = self._task_registry.get(session_id, {})
        summary = registry.get(main_task_id)
        if summary:
            summary.status = "completed"
            summary.completed_at = datetime.now(UTC)
            _logger.info(
                "main_task_completed",
                session_id=session_id,
                main_task_id=main_task_id,
            )

        # Also store the final answer as a top-level context entry so semantic
        # searches across the session can find it.
        if final_answer:
            goal = summary.goal if summary else main_task_id
            try:
                await self.store_task_context(
                    task_id=f"synthesis_{main_task_id}",
                    agent_type="synthesizer",
                    content=f"MainTask Goal: {goal}\n\nFinal Answer:\n{final_answer}",
                    metadata={
                        "session_id": session_id,
                        "main_task_id": main_task_id,
                        "task_type": "synthesis",
                    },
                )
            except Exception as exc:
                _logger.warning(
                    "complete_main_task_store_failed",
                    main_task_id=main_task_id,
                    error=str(exc),
                )

    async def get_context_statistics(
        self,
        session_id: str = "default",
    ) -> Dict[str, Any]:
        """Get statistics about stored contexts.
        
        Args:
            session_id: Session ID to get statistics for
            
        Returns:
            Dictionary with context statistics
        """
        if not self._initialized:
            await self.initialize()
            
        try:
            stats = await self.vector_store.get_collection_stats(session_id)
            
            # Add cache statistics
            cache_stats = {
                "cached_entries": len(self.context_cache),
                "cache_enabled": self.enable_context_caching,
            }
            
            return {
                **stats,
                "cache": cache_stats,
                "similarity_threshold": self.similarity_threshold,
                "max_wait_time": self.max_context_wait_time,
            }
            
        except Exception as exc:
            _logger.error("failed_to_get_context_statistics", session_id=session_id, error=str(exc))
            return {"error": str(exc)}


# Global instance for singleton pattern
_context_manager: Optional[SemanticContextManager] = None


async def get_semantic_context_manager() -> SemanticContextManager:
    """Get or create the global semantic context manager instance."""
    global _context_manager
    
    if _context_manager is None:
        _context_manager = SemanticContextManager()
        await _context_manager.initialize()
        
    return _context_manager
