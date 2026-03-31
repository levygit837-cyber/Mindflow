"""Context storage implementation for memory service.

Simplified context storage focused on SQLite + NumPy
for efficient memory management.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class SimpleContextStorage:
    """Simplified SQLite-based context storage."""
    
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
            
            # Create simplified context table
            self._connection.execute("""
                CREATE TABLE IF NOT EXISTS context (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    embedding TEXT,
                    token_start INTEGER NOT NULL,
                    token_end INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            self._connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_session ON context(session_id)
            """)
            
            self._connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_tokens ON context(token_start, token_end)
            """)
            
            self._connection.commit()
        
        await loop.run_in_executor(None, _init)
        _logger.info(f"Context storage initialized: {self.db_path}")
    
    async def store(
        self,
        id: str,
        session_id: str,
        agent_id: str,
        content: str,
        embedding: list[float] | None,
        token_start: int,
        token_end: int,
        timestamp: datetime,
    ) -> bool:
        """Store context entry.
        
        Args:
            id: Unique entry ID.
            session_id: Session identifier.
            agent_id: Agent identifier.
            content: Text content.
            embedding: Vector embedding.
            token_start: Start token position.
            token_end: End token position.
            timestamp: Creation timestamp.
            
        Returns:
            True if successful.
        """
        if not self._connection:
            await self.initialize()
        
        loop = asyncio.get_event_loop()
        
        def _store():
            try:
                self._connection.execute("""
                    INSERT OR REPLACE INTO context
                    (id, session_id, agent_id, content, embedding, token_start, token_end, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    id,
                    session_id,
                    agent_id,
                    content,
                    json.dumps(embedding) if embedding else None,
                    token_start,
                    token_end,
                    timestamp.isoformat(),
                ))
                self._connection.commit()
                return True
            except Exception as e:
                _logger.error(f"Failed to store context: {e}")
                return False
        
        return await loop.run_in_executor(None, _store)
    
    async def get_by_token_range(
        self,
        session_id: str,
        token_start: int | None = None,
        token_end: int | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get context entries by token range.
        
        Args:
            session_id: Session identifier.
            token_start: Start token position.
            token_end: End token position.
            limit: Maximum number of entries.
            
        Returns:
            List of context entries as dictionaries.
        """
        if not self._connection:
            await self.initialize()
        
        loop = asyncio.get_event_loop()
        
        def _query():
            query = "SELECT * FROM context WHERE session_id = ?"
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
            
            return [dict(row) for row in rows]
        
        return await loop.run_in_executor(None, _query)
    
    async def search_by_embedding(
        self,
        session_id: str,
        query_embedding: list[float],
        limit: int = 10,
        min_similarity: float = 0.3,
    ) -> list[dict[str, Any]]:
        """Search context by embedding similarity.
        
        Args:
            session_id: Session identifier.
            query_embedding: Query embedding vector.
            limit: Maximum results.
            min_similarity: Minimum similarity score.
            
        Returns:
            List of matching context entries.
        """
        if not self._connection:
            await self.initialize()
        
        loop = asyncio.get_event_loop()
        
        def _search():
            cursor = self._connection.execute(
                "SELECT * FROM context WHERE session_id = ? AND embedding IS NOT NULL ORDER BY token_start",
                (session_id,)
            )
            rows = cursor.fetchall()
            
            if not rows:
                return []
            
            # Calculate similarities
            results = []
            try:
                import numpy as np
                query_array = np.array(query_embedding)
                
                for row in rows:
                    row_dict = dict(row)
                    embedding_data = json.loads(row_dict["embedding"])
                    
                    if embedding_data:
                        entry_array = np.array(embedding_data)
                        
                        # Cosine similarity
                        similarity = np.dot(query_array, entry_array) / (
                            np.linalg.norm(query_array) * np.linalg.norm(entry_array)
                        )
                        
                        if similarity >= min_similarity:
                            row_dict["similarity"] = float(similarity)
                            results.append(row_dict)
                
                # Sort by similarity
                results.sort(key=lambda x: x["similarity"], reverse=True)
                return results[:limit]
                
            except ImportError:
                _logger.warning("NumPy not available, skipping embedding search")
                return []
        
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
                "SELECT COUNT(*) as count, MIN(token_start) as min_token, MAX(token_end) as max_token FROM context WHERE session_id = ?",
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
    
    async def cleanup_old(self, session_id: str, keep_recent: int = 100000) -> int:
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
                "SELECT MAX(token_end) as max_token FROM context WHERE session_id = ?",
                (session_id,)
            )
            row = cursor.fetchone()
            
            if not row or row["max_token"] is None:
                return 0
            
            max_token = row["max_token"]
            cutoff_token = max(0, max_token - keep_recent)
            
            # Delete old entries
            cursor = self._connection.execute(
                "DELETE FROM context WHERE session_id = ? AND token_end < ?",
                (session_id, cutoff_token)
            )
            
            deleted_count = cursor.rowcount
            self._connection.commit()
            
            return deleted_count
        
        return await loop.run_in_executor(None, _cleanup)


# Alias for backward compatibility
ContextStorage = SimpleContextStorage
