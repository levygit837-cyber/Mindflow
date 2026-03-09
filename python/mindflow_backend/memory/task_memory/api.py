"""CrossTaskContextAPI — public interface for agents to request context from sibling sub-tasks.

Usage during DT pipeline resolution::

    api = CrossTaskContextAPI()

    # Before an agent runs:
    ctx = await api.get_context_for_subtask(
        db=db,
        requesting_task_id="subtask_b_id",
        query="what did subtask A produce about authentication?",
        sibling_task_ids=["subtask_a_id"],
    )
    if ctx.has_content:
        # prepend ctx.formatted_context to agent messages

    # After the agent produces output:
    await api.store_subtask_result(
        db=db,
        task_id="subtask_b_id",
        result_content=agent_output,
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.orm import Session

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.memory.shared.embeddings.factory import get_embedding_provider
from mindflow_backend.memory.task_memory.models import TaskChunk, TaskMemory

_logger = get_logger(__name__)


@dataclass
class CrossTaskContextResult:
    """Result of a cross-task context retrieval."""

    requesting_task_id: str
    hits: list[dict] = field(default_factory=list)

    @property
    def has_content(self) -> bool:
        return bool(self.hits)

    @property
    def formatted_context(self) -> str:
        """Human-readable context block to prepend to agent messages."""
        if not self.hits:
            return ""
        lines = ["[Cross-task context from sibling sub-tasks]"]
        for hit in self.hits:
            task_id = hit["task_id"]
            content = hit["content"]
            score = hit.get("score", 0.0)
            lines.append(f"- [task:{task_id}] (score: {score:.2f}) {content}")
        return "\n".join(lines)


class CrossTaskContextAPI:
    """Public API for inter-agent cross-task context retrieval.

    Uses pgvector cosine search on TaskChunk.embedding to find the most
    semantically relevant chunks from sibling sub-tasks.
    """

    def __init__(self, *, similarity_threshold: float = 0.3, max_results: int = 5) -> None:
        self._similarity_threshold = similarity_threshold
        self._max_results = max_results

    async def get_context_for_subtask(
        self,
        db: Session,
        *,
        requesting_task_id: str,
        query: str,
        sibling_task_ids: list[str] | None = None,
        parent_task_id: str | None = None,
        max_results: int | None = None,
    ) -> CrossTaskContextResult:
        """Retrieve semantically relevant context from sibling sub-tasks.

        Args:
            db: SQLAlchemy synchronous session.
            requesting_task_id: The task ID of the calling agent (excluded from results).
            query: What context the agent needs (natural language).
            sibling_task_ids: Explicit list of task_ids to search. If None, discovers
                              siblings automatically via parent_task_id.
            parent_task_id: Used to discover siblings when sibling_task_ids is None.
            max_results: Override default max_results.

        Returns:
            CrossTaskContextResult with ranked context hits.
        """
        limit = max_results or self._max_results

        # Discover sibling task IDs if not provided explicitly
        if sibling_task_ids is None:
            sibling_task_ids = await self._discover_siblings(
                db,
                requesting_task_id=requesting_task_id,
                parent_task_id=parent_task_id,
            )

        if not sibling_task_ids:
            return CrossTaskContextResult(requesting_task_id=requesting_task_id)

        # Generate query embedding
        provider = get_embedding_provider()
        try:
            query_vec = await provider.embed(query)
        except Exception as exc:
            _logger.warning("cross_task_embed_failed", error=str(exc))
            return CrossTaskContextResult(requesting_task_id=requesting_task_id)

        # Retrieve TaskMemory rows for sibling task IDs
        task_memory_rows = list(db.scalars(
            select(TaskMemory).where(TaskMemory.task_id.in_(sibling_task_ids))
        ))
        task_memory_ids = [str(row.id) for row in task_memory_rows]
        task_id_map = {str(row.id): row.task_id for row in task_memory_rows}

        if not task_memory_ids:
            return CrossTaskContextResult(requesting_task_id=requesting_task_id)

        # pgvector cosine search across TaskChunk embeddings
        stmt = (
            select(TaskChunk)
            .where(TaskChunk.task_memory_id.in_(task_memory_ids))
            .order_by(TaskChunk.embedding.cosine_distance(query_vec))
            .limit(limit * 2)
        )
        chunks = list(db.scalars(stmt))

        hits: list[dict] = []
        for chunk in chunks:
            try:
                distance = chunk.embedding.cosine_distance(query_vec)
                score = 1.0 - float(distance)
            except Exception:
                score = 0.0
            if score < self._similarity_threshold:
                continue
            hits.append({
                "task_id": task_id_map.get(str(chunk.task_memory_id), str(chunk.task_memory_id)),
                "chunk_id": str(chunk.id),
                "content": (chunk.summary or chunk.content)[:800],
                "score": score,
                "chunk_type": chunk.chunk_type,
            })
            if len(hits) >= limit:
                break

        _logger.info(
            "cross_task_context_retrieved",
            requesting_task_id=requesting_task_id,
            siblings_searched=len(sibling_task_ids),
            hits=len(hits),
        )
        return CrossTaskContextResult(requesting_task_id=requesting_task_id, hits=hits)

    async def store_subtask_result(
        self,
        db: Session,
        *,
        task_id: str,
        result_content: str,
        result_type: str = "execution_result",
    ) -> None:
        """Store an agent's execution result as a TaskChunk with embedding.

        Called after a sub-task agent completes its work, making the result
        immediately available for sibling agents via cross-task retrieval.
        """
        task_mem = db.scalar(select(TaskMemory).where(TaskMemory.task_id == task_id))
        if not task_mem:
            _logger.warning("cross_task_store_no_task_memory", task_id=task_id)
            return

        # Count existing chunks for sequence
        existing = list(db.scalars(
            select(TaskChunk).where(TaskChunk.task_memory_id == str(task_mem.id))
        ))
        sequence = len(existing)

        # Generate embedding
        provider = get_embedding_provider()
        try:
            vector = await provider.embed(result_content)
        except Exception as exc:
            _logger.warning("cross_task_store_embed_failed", task_id=task_id, error=str(exc))
            vector = [0.0] * provider.dimension()

        chunk = TaskChunk(
            task_memory_id=str(task_mem.id),
            sequence=sequence,
            chunk_type=result_type,
            content=result_content,
            summary=result_content[:500],
            keywords=[],
            token_count=len(result_content.split()),
            embedding=vector,
        )
        db.add(chunk)
        db.flush()

        _logger.info(
            "cross_task_result_stored",
            task_id=task_id,
            chunk_id=str(chunk.id),
            chunk_type=result_type,
        )

    async def _discover_siblings(
        self,
        db: Session,
        *,
        requesting_task_id: str,
        parent_task_id: str | None,
    ) -> list[str]:
        """Find sibling task IDs sharing the same parent, excluding the requesting task."""
        if not parent_task_id:
            # Try to find parent via TaskMemory
            req_mem = db.scalar(select(TaskMemory).where(TaskMemory.task_id == requesting_task_id))
            if req_mem and req_mem.parent_task_id:
                parent_task_id = req_mem.parent_task_id
            else:
                return []

        siblings = list(db.scalars(
            select(TaskMemory.task_id)
            .where(
                TaskMemory.parent_task_id == parent_task_id,
                TaskMemory.task_id != requesting_task_id,
            )
        ))
        return siblings


@lru_cache(maxsize=1)
def get_cross_task_api() -> CrossTaskContextAPI:
    return CrossTaskContextAPI()
