"""Simple Memory Service for MindFlow.

Lightweight memory storage and retrieval using SQLite + NumPy
for efficient context management across sessions.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.interfaces.services.memory import MemoryServiceInterface
from mindflow_backend.services.interfaces.base_interfaces import BaseAbstractService

from ..nlp_embeddings import EmbeddingMethod, NLPEmbeddingService, create_embedding_service

_logger = get_logger(__name__)


class MemoryConfig:
    """Configuration for memory service."""
    
    def __init__(
        self,
        db_path: str = "memory.db",
        embedding_method: EmbeddingMethod = EmbeddingMethod.TFIDF,
        max_context_length: int = 100000,
        cleanup_threshold: int = 1000000,
        similarity_threshold: float = 0.3,
        **embedding_kwargs: Any,
    ) -> None:
        """Initialize memory configuration.
        
        Args:
            db_path: SQLite database path.
            embedding_method: Embedding generation method.
            max_context_length: Maximum context length per session.
            cleanup_threshold: Threshold for automatic cleanup.
            similarity_threshold: Minimum similarity for retrieval.
            **embedding_kwargs: Additional embedding configuration.
        """
        self.db_path = db_path
        self.embedding_method = embedding_method
        self.max_context_length = max_context_length
        self.cleanup_threshold = cleanup_threshold
        self.similarity_threshold = similarity_threshold
        self.embedding_kwargs = embedding_kwargs


class ContextEntry:
    """Single context entry in memory."""
    
    def __init__(
        self,
        id: str,
        session_id: str,
        agent_id: str,
        content: str,
        embedding: list[float] | None,
        token_start: int,
        token_end: int,
        timestamp: datetime,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Initialize context entry.
        
        Args:
            id: Unique entry ID.
            session_id: Session identifier.
            agent_id: Agent identifier.
            content: Text content.
            embedding: Vector embedding.
            token_start: Start token position.
            token_end: End token position.
            timestamp: Creation timestamp.
            metadata: Additional metadata.
        """
        self.id = id
        self.session_id = session_id
        self.agent_id = agent_id
        self.content = content
        self.embedding = embedding
        self.token_start = token_start
        self.token_end = token_end
        self.timestamp = timestamp
        self.metadata = metadata or {}
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.
        
        Returns:
            Dictionary representation.
        """
        return {
            "id": self.id,
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "content": self.content,
            "embedding": json.dumps(self.embedding) if self.embedding else None,
            "token_start": self.token_start,
            "token_end": self.token_end,
            "timestamp": self.timestamp.isoformat(),
            "metadata": json.dumps(self.metadata) if self.metadata else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContextEntry:
        """Create from dictionary.
        
        Args:
            data: Dictionary data.
            
        Returns:
            Context entry instance.
        """
        return cls(
            id=data["id"],
            session_id=data["session_id"],
            agent_id=data["agent_id"],
            content=data["content"],
            embedding=json.loads(data["embedding"]) if data["embedding"] else None,
            token_start=data["token_start"],
            token_end=data["token_end"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=json.loads(data["metadata"]) if data["metadata"] else None,
        )


class ContextStorage:
    """SQLite-based context storage."""
    
    def __init__(self, db_path: str) -> None:
        """Initialize context storage.
        
        Args:
            db_path: SQLite database path.
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection: sqlite3.Connection | None = None
    
    async def initialize(self) -> None:
        """Initialize database and create tables."""
        loop = asyncio.get_event_loop()
        
        def _init():
            self._connection = sqlite3.connect(self.db_path)
            self._connection.row_factory = sqlite3.Row
            
            # Create tables
            self._connection.execute("""
                CREATE TABLE IF NOT EXISTS context_entries (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    embedding TEXT,
                    token_start INTEGER NOT NULL,
                    token_end INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            self._connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_id ON context_entries(session_id)
            """)
            
            self._connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_token_range ON context_entries(token_start, token_end)
            """)
            
            self._connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON context_entries(timestamp)
            """)
            
            self._connection.commit()
        
        await loop.run_in_executor(None, _init)
        _logger.info(f"Context storage initialized: {self.db_path}")
    
    async def store_context(self, entry: ContextEntry) -> bool:
        """Store context entry.
        
        Args:
            entry: Context entry to store.
            
        Returns:
            True if successful.
        """
        if not self._connection:
            await self.initialize()
        
        loop = asyncio.get_event_loop()
        
        def _store():
            try:
                self._connection.execute("""
                    INSERT OR REPLACE INTO context_entries
                    (id, session_id, agent_id, content, embedding, token_start, token_end, timestamp, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry.id,
                    entry.session_id,
                    entry.agent_id,
                    entry.content,
                    json.dumps(entry.embedding) if entry.embedding else None,
                    entry.token_start,
                    entry.token_end,
                    entry.timestamp.isoformat(),
                    json.dumps(entry.metadata) if entry.metadata else None,
                ))
                self._connection.commit()
                return True
            except Exception as e:
                _logger.error(f"Failed to store context: {e}")
                return False
        
        return await loop.run_in_executor(None, _store)
    
    async def get_context_by_range(
        self,
        session_id: str,
        token_start: int | None = None,
        token_end: int | None = None,
        limit: int | None = None,
    ) -> list[ContextEntry]:
        """Get context entries by token range.
        
        Args:
            session_id: Session identifier.
            token_start: Start token position.
            token_end: End token position.
            limit: Maximum number of entries.
            
        Returns:
            List of context entries.
        """
        if not self._connection:
            await self.initialize()
        
        loop = asyncio.get_event_loop()
        
        def _query():
            query = "SELECT * FROM context_entries WHERE session_id = ?"
            params = [session_id]
            
            if token_start is not None:
                query += " AND token_start >= ?"
                params.append(token_start)
            
            if token_end is not None:
                query += " AND token_end <= ?"
                params.append(token_end)
            
            query += " ORDER BY token_start"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor = self._connection.execute(query, params)
            rows = cursor.fetchall()
            
            return [ContextEntry.from_dict(dict(row)) for row in rows]
        
        return await loop.run_in_executor(None, _query)
    
    async def get_context_by_id(self, context_id: str) -> ContextEntry | None:
        """Get context entry by ID.
        
        Args:
            context_id: Context entry ID.
            
        Returns:
            Context entry if found.
        """
        if not self._connection:
            await self.initialize()
        
        loop = asyncio.get_event_loop()
        
        def _query():
            cursor = self._connection.execute(
                "SELECT * FROM context_entries WHERE id = ?",
                (context_id,)
            )
            row = cursor.fetchone()
            
            return ContextEntry.from_dict(dict(row)) if row else None
        
        return await loop.run_in_executor(None, _query)
    
    async def search_context(
        self,
        session_id: str,
        query_embedding: list[float],
        limit: int = 10,
        min_similarity: float = 0.3,
    ) -> list[tuple[ContextEntry, float]]:
        """Search context by embedding similarity.
        
        Args:
            session_id: Session identifier.
            query_embedding: Query embedding vector.
            limit: Maximum results.
            min_similarity: Minimum similarity score.
            
        Returns:
            List of (context_entry, similarity) tuples.
        """
        if not self._connection:
            await self.initialize()
        
        loop = asyncio.get_event_loop()
        
        def _search():
            cursor = self._connection.execute(
                "SELECT * FROM context_entries WHERE session_id = ? AND embedding IS NOT NULL ORDER BY token_start",
                (session_id,)
            )
            rows = cursor.fetchall()
            
            if not rows:
                return []
            
            # Calculate similarities
            results = []
            query_array = np.array(query_embedding)
            
            for row in rows:
                entry = ContextEntry.from_dict(dict(row))
                if entry.embedding:
                    entry_array = np.array(entry.embedding)
                    
                    # Cosine similarity
                    similarity = np.dot(query_array, entry_array) / (
                        np.linalg.norm(query_array) * np.linalg.norm(entry_array)
                    )
                    
                    if similarity >= min_similarity:
                        results.append((entry, float(similarity)))
            
            # Sort by similarity
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:limit]
        
        return await loop.run_in_executor(None, _search)
    
    async def get_session_stats(self, session_id: str) -> dict[str, Any]:
        """Get session statistics.
        
        Args:
            session_id: Session identifier.
            
        Returns:
            Session statistics.
        """
        if not self._connection:
            await self.initialize()
        
        loop = asyncio.get_event_loop()
        
        def _stats():
            cursor = self._connection.execute(
                "SELECT COUNT(*) as count, MIN(token_start) as min_token, MAX(token_end) as max_token FROM context_entries WHERE session_id = ?",
                (session_id,)
            )
            row = cursor.fetchone()
            
            return {
                "entry_count": row["count"] or 0,
                "min_token": row["min_token"] or 0,
                "max_token": row["max_token"] or 0,
                "total_tokens": (row["max_token"] or 0) - (row["min_token"] or 0),
            }
        
        return await loop.run_in_executor(None, _stats)
    
    async def cleanup_old_context(self, session_id: str, keep_recent: int = 100000) -> int:
        """Clean up old context entries.
        
        Args:
            session_id: Session identifier.
            keep_recent: Number of recent tokens to keep.
            
        Returns:
            Number of entries removed.
        """
        if not self._connection:
            await self.initialize()
        
        loop = asyncio.get_event_loop()
        
        def _cleanup():
            # Find cutoff token
            cursor = self._connection.execute(
                "SELECT MAX(token_end) as max_token FROM context_entries WHERE session_id = ?",
                (session_id,)
            )
            row = cursor.fetchone()
            
            if not row or row["max_token"] is None:
                return 0
            
            max_token = row["max_token"]
            cutoff_token = max(0, max_token - keep_recent)
            
            # Delete old entries
            cursor = self._connection.execute(
                "DELETE FROM context_entries WHERE session_id = ? AND token_end < ?",
                (session_id, cutoff_token)
            )
            
            deleted_count = cursor.rowcount
            self._connection.commit()
            
            return deleted_count
        
        return await loop.run_in_executor(None, _cleanup)


class ContextRetriever:
    """Context retrieval service."""
    
    def __init__(
        self,
        storage: ContextStorage,
        embedding_service: NLPEmbeddingService,
        similarity_threshold: float = 0.3,
    ) -> None:
        """Initialize context retriever.
        
        Args:
            storage: Context storage instance.
            embedding_service: Embedding service.
            similarity_threshold: Minimum similarity threshold.
        """
        self.storage = storage
        self.embedding_service = embedding_service
        self.similarity_threshold = similarity_threshold
    
    async def get_context_by_tokens(
        self,
        session_id: str,
        token_start: int | None = None,
        token_end: int | None = None,
        limit: int | None = None,
    ) -> list[ContextEntry]:
        """Get context by token range.
        
        Args:
            session_id: Session identifier.
            token_start: Start token position.
            token_end: End token position.
            limit: Maximum entries.
            
        Returns:
            Context entries in token range.
        """
        return await self.storage.get_context_by_range(
            session_id, token_start, token_end, limit
        )
    
    async def search_context(
        self,
        session_id: str,
        query: str,
        token_range: tuple[int, int] | None = None,
        limit: int = 10,
    ) -> list[tuple[ContextEntry, float]]:
        """Search context by semantic similarity.
        
        Args:
            session_id: Session identifier.
            query: Search query.
            token_range: Optional token range filter.
            limit: Maximum results.
            
        Returns:
            List of (context_entry, similarity) tuples.
        """
        # Generate query embedding
        query_embedding = await self.embedding_service.generate_embeddings(query)
        
        # Search by similarity
        results = await self.storage.search_context(
            session_id,
            query_embedding[0],
            limit,
            self.similarity_threshold,
        )
        
        # Filter by token range if specified
        if token_range:
            token_start, token_end = token_range
            filtered_results = []
            
            for entry, similarity in results:
                if (entry.token_start >= token_start and 
                    entry.token_end <= token_end):
                    filtered_results.append((entry, similarity))
            
            results = filtered_results
        
        return results
    
    async def get_recent_context(
        self,
        session_id: str,
        token_count: int = 1000,
        limit: int = 10,
    ) -> list[ContextEntry]:
        """Get recent context by token count.
        
        Args:
            session_id: Session identifier.
            token_count: Number of recent tokens.
            limit: Maximum entries.
            
        Returns:
            Recent context entries.
        """
        # Get session stats
        stats = await self.storage.get_session_stats(session_id)
        max_token = stats["max_token"]
        
        # Get recent entries
        return await self.get_context_by_tokens(
            session_id,
            max(0, max_token - token_count),
            max_token,
            limit,
        )


class MemoryService(BaseAbstractService, MemoryServiceInterface):
    """Main memory service combining storage and retrieval."""
    
    def __init__(self, config: MemoryConfig) -> None:
        """Initialize memory service.
        
        Args:
            config: Memory configuration.
        """
        self.config = config
        self.storage = ContextStorage(config.db_path)
        self.embedding_service = create_embedding_service(
            method=config.embedding_method,
            **config.embedding_kwargs
        )
        self.retriever = ContextRetriever(
            self.storage,
            self.embedding_service,
            config.similarity_threshold,
        )
        self.is_initialized = False
    
    async def initialize(self) -> None:
        """Initialize memory service."""
        await self.storage.initialize()
        
        # Fit embedding service if needed
        if self.config.embedding_method == EmbeddingMethod.TFIDF:
            # Get some sample texts for fitting
            sample_entries = await self.storage.get_context_by_range("", limit=100)
            if sample_entries:
                sample_texts = [entry.content for entry in sample_entries]
                await self.embedding_service.fit(sample_texts)
        
        self.is_initialized = True
        _logger.info("Memory service initialized")
    
    async def store_context(
        self,
        session_id: str,
        agent_id: str,
        content: str,
        token_start: int,
        token_end: int,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store context entry.
        
        Args:
            session_id: Session identifier.
            agent_id: Agent identifier.
            content: Text content.
            token_start: Start token position.
            token_end: End token position.
            metadata: Additional metadata.
            
        Returns:
            Context entry ID.
        """
        if not self.is_initialized:
            await self.initialize()
        
        # Generate embedding
        embedding = await self.embedding_service.generate_embeddings(content)
        
        # Create context entry
        entry = ContextEntry(
            id=str(uuid4()),
            session_id=session_id,
            agent_id=agent_id,
            content=content,
            embedding=embedding[0] if embedding else None,
            token_start=token_start,
            token_end=token_end,
            timestamp=datetime.utcnow(),
            metadata=metadata,
        )
        
        # Store entry
        success = await self.storage.store_context(entry)
        
        if success:
            _logger.info(f"Context stored: {entry.id} for session {session_id}")
            return entry.id
        else:
            raise RuntimeError("Failed to store context")
    
    async def get_context(
        self,
        session_id: str,
        token_start: int | None = None,
        token_end: int | None = None,
    ) -> list[ContextEntry]:
        """Get context by token range.
        
        Args:
            session_id: Session identifier.
            token_start: Start token position.
            token_end: End token position.
            
        Returns:
            Context entries in range.
        """
        if not self.is_initialized:
            await self.initialize()
        
        return await self.retriever.get_context_by_tokens(
            session_id, token_start, token_end
        )
    
    async def search_context(
        self,
        session_id: str,
        query: str,
        token_range: tuple[int, int] | None = None,
        limit: int = 10,
    ) -> list[tuple[ContextEntry, float]]:
        """Search context by semantic similarity.
        
        Args:
            session_id: Session identifier.
            query: Search query.
            token_range: Optional token range filter.
            limit: Maximum results.
            
        Returns:
            Search results with similarity scores.
        """
        if not self.is_initialized:
            await self.initialize()
        
        return await self.retriever.search_context(
            session_id, query, token_range, limit
        )
    
    async def get_session_stats(self, session_id: str) -> dict[str, Any]:
        """Get session statistics.
        
        Args:
            session_id: Session identifier.
            
        Returns:
            Session statistics.
        """
        if not self.is_initialized:
            await self.initialize()
        
        return await self.storage.get_session_stats(session_id)
    
    async def cleanup_session(self, session_id: str) -> int:
        """Clean up old context in session.
        
        Args:
            session_id: Session identifier.
            
        Returns:
            Number of entries removed.
        """
        if not self.is_initialized:
            await self.initialize()
        
        return await self.storage.cleanup_old_context(
            session_id, self.config.max_context_length
        )


def create_memory_service(
    db_path: str = "memory.db",
    embedding_method: EmbeddingMethod = EmbeddingMethod.TFIDF,
    **kwargs: Any,
) -> MemoryService:
    """Create memory service with configuration.
    
    Args:
        db_path: Database path.
        embedding_method: Embedding method.
        **kwargs: Additional configuration.
        
    Returns:
        Configured memory service.
    """
    config = MemoryConfig(
        db_path=db_path,
        embedding_method=embedding_method,
        **kwargs
    )
    
    return MemoryService(config)
