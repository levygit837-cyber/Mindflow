"""Memory Service - Centralized service for the Intelligent Memory System.

Provides unified interface for:
- Saving memories (structured + embeddings + full-text)
- Searching memories (semantic + full-text + hybrid)
- Managing scope (global, project, session)
- Integration with CategoryManager
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from mindflow_backend.infra.database.connection import get_db_session
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.memory.category_manager import CategoryManager, MemoryScope, MemoryType
from mindflow_backend.memory.storage.models import (
    MemoryCategory,
    MemoryEmbedding,
    MemoryEntry,
    MemorySubCategory,
    MemoryTag,
)
from mindflow_backend.services.context.embedding_service import EmbeddingService

_logger = get_logger(__name__)


class SearchMode(str, Enum):
    """Search mode for memory retrieval."""
    SEMANTIC = "semantic"  # Embedding similarity
    FULLTEXT = "fulltext"  # PostgreSQL full-text search
    HYBRID = "hybrid"  # Combined semantic + full-text


class MemorySearchResult:
    """Result of a memory search."""

    def __init__(
        self,
        memory: MemoryEntry,
        score: float,
        search_type: str,
    ):
        self.memory = memory
        self.score = score
        self.search_type = search_type

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.memory.id,
            "content": self.memory.content[:200] + "..." if len(self.memory.content) > 200 else self.memory.content,
            "memory_type": self.memory.memory_type,
            "category": getattr(self.memory.category, 'name', None) if self.memory.category else None,
            "scope": self.memory.scope,
            "importance": self.memory.importance,
            "score": round(self.score, 4),
            "search_type": self.search_type,
            "created_at": self.memory.created_at.isoformat() if self.memory.created_at else None,
        }


class MemoryService:
    """Centralized service for memory operations.

    This is the main interface for the Intelligent Memory System,
    providing unified access to all memory functionality.
    """

    def __init__(self) -> None:
        """Initialize the memory service."""
        self.category_manager = CategoryManager()
        self.embedding_service = EmbeddingService()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the memory service."""
        if self._initialized:
            return

        async with get_db_session() as db:
            await self.category_manager.initialize(db)

        self._initialized = True
        _logger.info("memory_service_initialized")

    async def save_memory(
        self,
        content: str,
        memory_type: str,
        scope: str | MemoryScope,
        project_id: int | None = None,
        session_id: str | None = None,
        category: str | None = None,
        subcategory: str | None = None,
        structured_data: dict[str, Any] | None = None,
        source_agent_id: str | None = None,
        source_tool: str | None = None,
        importance: float | None = None,
        tags: list[str] | None = None,
        file_path: str | None = None,
        generate_embedding: bool = True,
    ) -> MemoryEntry:
        """Save a memory entry.

        This is the main method for saving memories. It handles:
        - Category classification (if not provided)
        - Scope validation
        - Embedding generation
        - Full-text search vector creation
        - Tag creation

        Args:
            content: Text content of the memory
            memory_type: Type of memory (fact, pattern, preference, error, insight, context)
            scope: Scope (global, project, session)
            project_id: Project ID (required if scope=project)
            session_id: Session ID (optional, for tracking)
            category: Category name (auto-classified if not provided)
            subcategory: Sub-category name (auto-classified if not provided)
            structured_data: Optional structured data (JSON)
            source_agent_id: ID of the agent that created this memory
            source_tool: Tool that generated this memory
            importance: Importance score (0.0-1.0, auto-set if not provided)
            tags: List of tags
            file_path: File path associated with this memory
            generate_embedding: Whether to generate embedding

        Returns:
            Created MemoryEntry
        """
        if not self._initialized:
            await self.initialize()

        # Normalize scope
        if isinstance(scope, MemoryScope):
            scope = scope.value

        # Validate scope
        if scope == MemoryScope.PROJECT.value and project_id is None:
            raise ValueError("project_id is required when scope is 'project'")

        async with get_db_session() as db:
            # Auto-classify if category not provided
            if not category:
                category, subcategory = self.category_manager.classify_content(
                    content=content,
                    memory_type=memory_type,
                    source_tool=source_tool,
                    file_path=file_path,
                )

            # Get or create category
            category_id = None
            subcategory_id = None
            if category and scope == MemoryScope.PROJECT.value and project_id:
                cat = await self.category_manager.get_or_create_category(
                    db, project_id, category
                )
                category_id = cat.id

                if subcategory:
                    sub = await self.category_manager.get_or_create_subcategory(
                        db, project_id, category, subcategory
                    )
                    subcategory_id = sub.id

            # Auto-set importance if not provided
            if importance is None and category:
                importance = await self.category_manager.get_category_importance(
                    db, category
                )
            elif importance is None:
                importance = 0.5

            # Create full-text search vector (simplified, can be enhanced)
            search_vector = self._create_search_vector(content, tags or [])

            # Create memory entry
            memory = MemoryEntry(
                content=content,
                content_structured=structured_data,
                memory_type=memory_type,
                scope=scope,
                project_id=project_id,
                session_id=session_id,
                category_id=category_id,
                subcategory_id=subcategory_id,
                importance=importance,
                source_agent_id=source_agent_id,
                source_tool=source_tool,
                search_vector=search_vector,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )

            db.add(memory)
            await db.flush()  # Get memory.id

            # Generate and save embedding
            if generate_embedding:
                try:
                    embedding_vector = await self.embedding_service.generate_embedding(content)
                    if embedding_vector:
                        memory_embedding = MemoryEmbedding(
                            memory_id=memory.id,
                            vector=embedding_vector,
                            embedding_model="default",
                        )
                        db.add(memory_embedding)
                except Exception as e:
                    _logger.warning(
                        "embedding_generation_failed",
                        memory_id=memory.id,
                        error=str(e),
                    )

            # Save tags
            if tags:
                for tag in tags:
                    memory_tag = MemoryTag(
                        memory_id=memory.id,
                        tag=tag.lower().strip(),
                        scope=scope,
                    )
                    db.add(memory_tag)

            await db.commit()

            _logger.info(
                "memory_saved",
                memory_id=memory.id,
                memory_type=memory_type,
                scope=scope,
                category=category,
                importance=importance,
            )

            return memory

    async def search_memories(
        self,
        query: str,
        scope: str | MemoryScope | None = None,
        project_id: int | None = None,
        categories: list[str] | None = None,
        memory_types: list[str] | None = None,
        tags: list[str] | None = None,
        min_importance: float = 0.0,
        search_mode: SearchMode = SearchMode.HYBRID,
        limit: int = 10,
    ) -> list[MemorySearchResult]:
        """Search memories using multiple strategies.

        Args:
            query: Search query text
            scope: Filter by scope (global, project, session)
            project_id: Filter by project ID
            categories: Filter by category names
            memory_types: Filter by memory types
            tags: Filter by tags
            min_importance: Minimum importance score
            search_mode: Search strategy (semantic, fulltext, hybrid)
            limit: Maximum number of results

        Returns:
            List of MemorySearchResult
        """
        if not self._initialized:
            await self.initialize()

        if search_mode == SearchMode.SEMANTIC:
            return await self._semantic_search(
                query, scope, project_id, categories, memory_types,
                tags, min_importance, limit
            )
        elif search_mode == SearchMode.FULLTEXT:
            return await self._fulltext_search(
                query, scope, project_id, categories, memory_types,
                tags, min_importance, limit
            )
        else:  # HYBRID
            return await self._hybrid_search(
                query, scope, project_id, categories, memory_types,
                tags, min_importance, limit
            )

    async def _semantic_search(
        self,
        query: str,
        scope: str | MemoryScope | None,
        project_id: int | None,
        categories: list[str] | None,
        memory_types: list[str] | None,
        tags: list[str] | None,
        min_importance: float,
        limit: int,
    ) -> list[MemorySearchResult]:
        """Search by embedding similarity."""
        try:
            # Generate query embedding
            query_vector = await self.embedding_service.generate_embedding(query)

            if not query_vector:
                return []

            async with get_db_session() as db:
                # Build base query
                stmt = (
                    select(MemoryEntry, MemoryEmbedding.vector)
                    .join(MemoryEmbedding, MemoryEntry.id == MemoryEmbedding.memory_id)
                    .where(MemoryEntry.importance >= min_importance)
                )

                # Apply filters
                if scope:
                    scope_value = scope.value if isinstance(scope, MemoryScope) else scope
                    stmt = stmt.where(MemoryEntry.scope == scope_value)

                if project_id:
                    stmt = stmt.where(MemoryEntry.project_id == project_id)

                if memory_types:
                    stmt = stmt.where(MemoryEntry.memory_type.in_(memory_types))

                # Category filter requires join
                if categories:
                    stmt = stmt.join(
                        MemoryCategory, MemoryEntry.category_id == MemoryCategory.id
                    ).where(MemoryCategory.name.in_(categories))

                # Tags filter
                if tags:
                    stmt = stmt.join(
                        MemoryTag, MemoryEntry.id == MemoryTag.memory_id
                    ).where(MemoryTag.tag.in_([t.lower() for t in tags]))

                # Order by cosine distance and limit
                # Using pgvector's cosine distance operator
                stmt = (
                    stmt.order_by(
                        MemoryEmbedding.vector.cosine_distance(query_vector)
                    )
                    .limit(limit)
                )

                result = await db.execute(stmt)
                rows = result.all()

                results = []
                for row in rows:
                    memory, vector = row
                    # Calculate cosine similarity score
                    # score = 1 - cosine_distance (pgvector returns distance, we want similarity)
                    if vector and query_vector:
                        # Calculate dot product and magnitudes
                        dot_product = sum(a * b for a, b in zip(vector, query_vector))
                        magnitude_vector = sum(a * a for a in vector) ** 0.5
                        magnitude_query = sum(b * b for b in query_vector) ** 0.5
                        
                        if magnitude_vector > 0 and magnitude_query > 0:
                            cosine_similarity = dot_product / (magnitude_vector * magnitude_query)
                            score = (cosine_similarity + 1) / 2  # Normalize to 0-1
                        else:
                            score = 0.0
                    else:
                        score = 0.0
                    
                    results.append(MemorySearchResult(memory, round(score, 4), "semantic"))

                return results

        except Exception as e:
            _logger.error("semantic_search_failed", error=str(e))
            return []

    async def _fulltext_search(
        self,
        query: str,
        scope: str | MemoryScope | None,
        project_id: int | None,
        categories: list[str] | None,
        memory_types: list[str] | None,
        tags: list[str] | None,
        min_importance: float,
        limit: int,
    ) -> list[MemorySearchResult]:
        """Search by full-text."""
        async with get_db_session() as db:
            # Build query with to_tsquery
            ts_query = func.plainto_tsquery("portuguese", query)

            stmt = (
                select(
                    MemoryEntry,
                    func.ts_rank(MemoryEntry.search_vector, ts_query).label("rank")
                )
                .where(
                    MemoryEntry.search_vector.op("@@")(ts_query),
                    MemoryEntry.importance >= min_importance,
                )
            )

            # Apply filters
            if scope:
                scope_value = scope.value if isinstance(scope, MemoryScope) else scope
                stmt = stmt.where(MemoryEntry.scope == scope_value)

            if project_id:
                stmt = stmt.where(MemoryEntry.project_id == project_id)

            if memory_types:
                stmt = stmt.where(MemoryEntry.memory_type.in_(memory_types))

            if categories:
                stmt = stmt.join(
                    MemoryCategory, MemoryEntry.category_id == MemoryCategory.id
                ).where(MemoryCategory.name.in_(categories))

            if tags:
                stmt = stmt.join(
                    MemoryTag, MemoryEntry.id == MemoryTag.memory_id
                ).where(MemoryTag.tag.in_([t.lower() for t in tags]))

            stmt = stmt.order_by(text("rank DESC")).limit(limit)

            result = await db.execute(stmt)
            rows = result.all()

            return [
                MemorySearchResult(row[0], float(row[1]), "fulltext")
                for row in rows
            ]

    async def _hybrid_search(
        self,
        query: str,
        scope: str | MemoryScope | None,
        project_id: int | None,
        categories: list[str] | None,
        memory_types: list[str] | None,
        tags: list[str] | None,
        min_importance: float,
        limit: int,
    ) -> list[MemorySearchResult]:
        """Combine semantic and full-text search with re-ranking."""
        # Get results from both methods
        semantic_results = await self._semantic_search(
            query, scope, project_id, categories, memory_types,
            tags, min_importance, limit * 2
        )

        fulltext_results = await self._fulltext_search(
            query, scope, project_id, categories, memory_types,
            tags, min_importance, limit * 2
        )

        # Combine and deduplicate
        all_results: dict[int, MemorySearchResult] = {}

        for result in semantic_results:
            if result.memory.id not in all_results:
                all_results[result.memory.id] = result
            else:
                # Boost score if found in both
                existing = all_results[result.memory.id]
                if existing.search_type != "hybrid":
                    existing.score = (existing.score + result.score) / 2 * 1.1  # 10% boost
                    existing.search_type = "hybrid"

        for result in fulltext_results:
            if result.memory.id not in all_results:
                all_results[result.memory.id] = result
            else:
                # Boost score if found in both
                existing = all_results[result.memory.id]
                if existing.search_type != "hybrid":
                    existing.score = (existing.score + result.score) / 2 * 1.1
                    existing.search_type = "hybrid"

        # Sort by score and return top results
        sorted_results = sorted(
            all_results.values(),
            key=lambda x: x.score,
            reverse=True
        )

        return sorted_results[:limit]

    async def get_memory(
        self,
        memory_id: int,
        increment_access: bool = True,
    ) -> MemoryEntry | None:
        """Get a memory by ID.

        Args:
            memory_id: Memory entry ID
            increment_access: Whether to increment access count

        Returns:
            MemoryEntry or None if not found
        """
        async with get_db_session() as db:
            result = await db.execute(
                select(MemoryEntry).where(MemoryEntry.id == memory_id)
            )
            memory = result.scalar_one_or_none()

            if memory and increment_access:
                memory.access_count += 1
                memory.last_accessed = datetime.now(UTC)
                await db.commit()

            return memory

    async def update_memory(
        self,
        memory_id: int,
        content: str | None = None,
        importance: float | None = None,
        tags: list[str] | None = None,
    ) -> MemoryEntry | None:
        """Update a memory entry.

        Args:
            memory_id: Memory entry ID
            content: New content (optional)
            importance: New importance (optional)
            tags: New tags (optional, replaces existing)

        Returns:
            Updated MemoryEntry or None if not found
        """
        async with get_db_session() as db:
            result = await db.execute(
                select(MemoryEntry).where(MemoryEntry.id == memory_id)
            )
            memory = result.scalar_one_or_none()

            if not memory:
                return None

            if content is not None:
                memory.content = content
                memory.search_vector = self._create_search_vector(content, tags or [])

                # Update embedding
                try:
                    embedding_vector = await self.embedding_service.generate_embedding(content)
                    if embedding_vector:
                        # Delete old embedding and create new
                        await db.execute(
                            text("DELETE FROM memory_embeddings WHERE memory_id = :memory_id"),
                            {"memory_id": memory_id}
                        )
                        new_embedding = MemoryEmbedding(
                            memory_id=memory_id,
                            vector=embedding_vector,
                            embedding_model="default",
                        )
                        db.add(new_embedding)
                except Exception as e:
                    _logger.warning(
                        "embedding_update_failed",
                        memory_id=memory_id,
                        error=str(e),
                    )

            if importance is not None:
                memory.importance = importance

            if tags is not None:
                # Delete old tags
                await db.execute(
                    text("DELETE FROM memory_tags WHERE memory_id = :memory_id"),
                    {"memory_id": memory_id}
                )
                # Add new tags
                for tag in tags:
                    new_tag = MemoryTag(
                        memory_id=memory_id,
                        tag=tag.lower().strip(),
                        scope=memory.scope,
                    )
                    db.add(new_tag)

            memory.updated_at = datetime.now(UTC)
            await db.commit()

            return memory

    async def delete_memory(self, memory_id: int) -> bool:
        """Delete a memory entry.

        Args:
            memory_id: Memory entry ID

        Returns:
            True if deleted, False if not found
        """
        async with get_db_session() as db:
            result = await db.execute(
                select(MemoryEntry).where(MemoryEntry.id == memory_id)
            )
            memory = result.scalar_one_or_none()

            if not memory:
                return False

            await db.delete(memory)
            await db.commit()

            _logger.info("memory_deleted", memory_id=memory_id)
            return True

    def _create_search_vector(self, content: str, tags: list[str]) -> str:
        """Create full-text search vector from content and tags.

        This is a simplified implementation. For production,
        consider using PostgreSQL's to_tsvector function.

        Args:
            content: Text content
            tags: List of tags

        Returns:
            Search vector string
        """
        # Combine content and tags
        all_text = content + " " + " ".join(tags)

        # Simple normalization (remove special chars, lower case)
        normalized = "".join(
            c.lower() if c.isalnum() or c.isspace() else " "
            for c in all_text
        )

        return normalized

    async def get_stats(self) -> dict[str, Any]:
        """Get memory system statistics.

        Returns:
            Dictionary with statistics
        """
        async with get_db_session() as db:
            # Total memories
            total_result = await db.execute(select(func.count(MemoryEntry.id)))
            total = total_result.scalar() or 0

            # By scope
            scope_result = await db.execute(
                select(MemoryEntry.scope, func.count(MemoryEntry.id))
                .group_by(MemoryEntry.scope)
            )
            by_scope = dict(scope_result.all())

            # By type
            type_result = await db.execute(
                select(MemoryEntry.memory_type, func.count(MemoryEntry.id))
                .group_by(MemoryEntry.memory_type)
            )
            by_type = dict(type_result.all())

            # Total embeddings
            embedding_result = await db.execute(
                select(func.count(MemoryEmbedding.id))
            )
            total_embeddings = embedding_result.scalar() or 0

            return {
                "total_memories": total,
                "total_embeddings": total_embeddings,
                "by_scope": by_scope,
                "by_type": by_type,
            }
