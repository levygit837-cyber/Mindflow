"""KuzuDB vector store implementation.

Provides vector storage and search capabilities using KuzuDB graph database.
"""

from __future__ import annotations

import asyncio
import json
import numpy as np
from typing import Any, Dict, List, Optional
from uuid import uuid4

from mindflow_backend.agents.core.interfaces import VectorStore
from mindflow_backend.exceptions import AgentVectorStoreError
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

try:
    import kuzu
    KUZU_AVAILABLE = True
except ImportError:
    KUZU_AVAILABLE = False
    _logger.warning("KuzuDB not available. Install with: pip install kuzu")


class KuzuDBVectorStore(VectorStore):
    """KuzuDB-based vector store for context retrieval."""
    
    def __init__(self, database_path: str = None, dimension: int = 256):
        if not KUZU_AVAILABLE:
            raise AgentVectorStoreError("KuzuDB not installed. Run: pip install kuzu")
        
        self.dimension = dimension
        self.database_path = database_path or "data/mindflow_vectors"
        self._db = None
        self._connection = None
        self._lock = asyncio.Lock()
        
    async def initialize(self) -> None:
        """Initialize the KuzuDB connection and create schema."""
        async with self._lock:
            if self._connection is not None:
                return
            
            try:
                self._db = kuzu.Database(self.database_path)
                self._connection = kuzu.Connection(self._db)
                
                # Create vector schema
                await self._create_schema()
                
                _logger.info(f"KuzuDB vector store initialized at {self.database_path}")
                
            except Exception as e:
                raise AgentVectorStoreError(f"Failed to initialize KuzuDB: {e}")
    
    async def _create_schema(self) -> None:
        """Create the necessary schema for vector storage."""
        # Create node tables
        node_tables = [
            """
            CREATE NODE TABLE IF NOT EXISTS VectorNode (
                id STRING,
                session_id STRING,
                content TEXT,
                metadata JSON,
                created_at TIMESTAMP,
                PRIMARY KEY (id)
            )
            """,
            """
            CREATE NODE TABLE IF NOT EXISTS Session (
                session_id STRING,
                created_at TIMESTAMP,
                PRIMARY KEY (session_id)
            )
            """
        ]
        
        for table_sql in node_tables:
            try:
                self._connection.execute(table_sql)
            except Exception as e:
                _logger.warning(f"Schema creation note: {e}")
        
        # Create relationship tables for vector connections
        rel_tables = [
            """
            CREATE REL TABLE IF NOT EXISTS HasVector (
                FROM Session TO VectorNode,
                created_at TIMESTAMP
            )
            """
        ]
        
        for rel_sql in rel_tables:
            try:
                self._connection.execute(rel_sql)
            except Exception as e:
                _logger.warning(f"Relationship creation note: {e}")
    
    async def store_vectors(
        self,
        session_id: str,
        vectors: List[List[float]],
        contents: List[str],
        metadata: List[Dict[str, Any]] = None,
    ) -> List[str]:
        """Store vectors with associated content and metadata."""
        await self.initialize()
        
        if len(vectors) != len(contents):
            raise AgentVectorStoreError("Number of vectors must match number of contents")
        
        if metadata is None:
            metadata = [{} for _ in contents]
        
        vector_ids = []
        
        async with self._lock:
            try:
                # Ensure session exists
                await self._ensure_session(session_id)
                
                for i, (vector, content, meta) in enumerate(zip(vectors, contents, metadata)):
                    vector_id = str(uuid4())
                    
                    # Store vector node
                    query = """
                    CREATE (v:VectorNode {
                        id: $id,
                        session_id: $session_id,
                        content: $content,
                        metadata: $metadata,
                        created_at: $created_at
                    })
                    """
                    
                    self._connection.execute(
                        query,
                        {
                            "id": vector_id,
                            "session_id": session_id,
                            "content": content,
                            "metadata": json.dumps(meta),
                            "created_at": str(np.datetime64('now'))
                        }
                    )
                    
                    # Create relationship to session
                    rel_query = """
                    MATCH (s:Session {session_id: $session_id})
                    CREATE (v:VectorNode {id: $vector_id})
                    CREATE (s)-[:HasVector {created_at: $created_at}]->(v)
                    """
                    
                    self._connection.execute(
                        rel_query,
                        {
                            "session_id": session_id,
                            "vector_id": vector_id,
                            "created_at": str(np.datetime64('now'))
                        }
                    )
                    
                    vector_ids.append(vector_id)
                
                _logger.info(f"Stored {len(vector_ids)} vectors for session {session_id}")
                return vector_ids
                
            except Exception as e:
                raise AgentVectorStoreError(f"Failed to store vectors: {e}")
    
    async def search_session_context(
        self,
        session_id: str,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors in session context."""
        await self.initialize()
        
        async with self._lock:
            try:
                # For now, implement a simple text-based search
                # In a full implementation, you'd use KuzuDB's vector similarity capabilities
                # or integrate with a specialized vector search library
                
                query = """
                MATCH (s:Session {session_id: $session_id})-[:HasVector]->(v:VectorNode)
                RETURN v.id as id, v.content as content, v.metadata as metadata, 
                       v.created_at as created_at
                ORDER BY v.created_at DESC
                LIMIT $limit
                """
                
                result = self._connection.execute(
                    query,
                    {"session_id": session_id, "limit": limit}
                )
                
                results = []
                while result.hasNext():
                    row = result.getNext()
                    metadata = json.loads(row[2]) if row[2] else {}
                    
                    results.append({
                        "id": row[0],
                        "content": row[1],
                        "metadata": metadata,
                        "created_at": row[3],
                        "score": 1.0  # Placeholder score
                    })
                
                return results
                
            except Exception as e:
                raise AgentVectorStoreError(f"Failed to search vectors: {e}")
    
    async def search_similar_vectors(
        self,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: float = 0.7,
        session_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors across all sessions or specific session."""
        await self.initialize()
        
        async with self._lock:
            try:
                if session_filter:
                    query = """
                    MATCH (s:Session {session_id: $session_id})-[:HasVector]->(v:VectorNode)
                    RETURN v.id as id, v.content as content, v.metadata as metadata,
                           v.session_id as session_id, v.created_at as created_at
                    ORDER BY v.created_at DESC
                    LIMIT $limit
                    """
                    params = {"session_id": session_filter, "limit": limit}
                else:
                    query = """
                    MATCH (s:Session)-[:HasVector]->(v:VectorNode)
                    RETURN v.id as id, v.content as content, v.metadata as metadata,
                           v.session_id as session_id, v.created_at as created_at
                    ORDER BY v.created_at DESC
                    LIMIT $limit
                    """
                    params = {"limit": limit}
                
                result = self._connection.execute(query, params)
                
                results = []
                while result.hasNext():
                    row = result.getNext()
                    metadata = json.loads(row[2]) if row[2] else {}
                    
                    results.append({
                        "id": row[0],
                        "content": row[1],
                        "metadata": metadata,
                        "session_id": row[3],
                        "created_at": row[4],
                        "score": 1.0  # Placeholder score
                    })
                
                return results
                
            except Exception as e:
                raise AgentVectorStoreError(f"Failed to search similar vectors: {e}")
    
    async def delete_session_vectors(self, session_id: str) -> int:
        """Delete all vectors for a session."""
        await self.initialize()
        
        async with self._lock:
            try:
                query = """
                MATCH (s:Session {session_id: $session_id})-[:HasVector]->(v:VectorNode)
                DETACH DELETE v
                """
                
                self._connection.execute(query, {"session_id": session_id})
                
                _logger.info(f"Deleted all vectors for session {session_id}")
                return 0  # KuzuDB doesn't return count in the same way
                
            except Exception as e:
                raise AgentVectorStoreError(f"Failed to delete session vectors: {e}")
    
    async def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session's vectors."""
        await self.initialize()
        
        async with self._lock:
            try:
                query = """
                MATCH (s:Session {session_id: $session_id})-[:HasVector]->(v:VectorNode)
                RETURN COUNT(v) as vector_count
                """
                
                result = self._connection.execute(query, {"session_id": session_id})
                
                if result.hasNext():
                    row = result.getNext()
                    return {
                        "session_id": session_id,
                        "vector_count": row[0],
                        "dimension": self.dimension
                    }
                
                return {"session_id": session_id, "vector_count": 0, "dimension": self.dimension}
                
            except Exception as e:
                raise AgentVectorStoreError(f"Failed to get session stats: {e}")
    
    async def _ensure_session(self, session_id: str) -> None:
        """Ensure a session node exists."""
        query = """
        MERGE (s:Session {session_id: $session_id})
        ON CREATE SET s.created_at = $created_at
        """
        
        self._connection.execute(
            query,
            {
                "session_id": session_id,
                "created_at": str(np.datetime64('now'))
            }
        )
    
    async def close(self) -> None:
        """Close the KuzuDB connection."""
        async with self._lock:
            if self._connection:
                self._connection.close()
                self._connection = None
            if self._db:
                # KuzuDB doesn't have explicit close method for database
                self._db = None
            
            _logger.info("KuzuDB vector store closed")


class KuzuDBVectorManager:
    """Manager class for KuzuDB vector operations."""
    
    def __init__(self):
        settings = get_settings()
        self.vector_store = KuzuDBVectorStore(
            database_path="data/mindflow_vectors",
            dimension=256  # Default dimension, can be made configurable
        )
    
    async def initialize(self) -> None:
        """Initialize the vector store."""
        await self.vector_store.initialize()
    
    async def store_context(
        self,
        session_id: str,
        content: str,
        metadata: Dict[str, Any] = None,
    ) -> str:
        """Store context with automatic embedding."""
        # For now, create a simple embedding (in real implementation, use actual embedding model)
        embedding = self._create_simple_embedding(content)
        
        vector_ids = await self.vector_store.store_vectors(
            session_id=session_id,
            vectors=[embedding],
            contents=[content],
            metadata=[metadata or {}]
        )
        
        return vector_ids[0] if vector_ids else None
    
    async def search_context(
        self,
        session_id: str,
        query: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search for similar context."""
        query_embedding = self._create_simple_embedding(query)
        
        return await self.vector_store.search_session_context(
            session_id=session_id,
            query_vector=query_embedding,
            limit=limit
        )
    
    def _create_simple_embedding(self, text: str) -> List[float]:
        """Create a simple embedding based on text hash (placeholder)."""
        # This is a very simple placeholder - in real implementation use proper embeddings
        import hashlib
        
        hash_obj = hashlib.md5(text.encode())
        hash_hex = hash_obj.hexdigest()
        
        # Convert hash to float values
        embedding = []
        for i in range(0, len(hash_hex), 2):
            byte_pair = hash_hex[i:i+2]
            val = int(byte_pair, 16) / 255.0  # Normalize to [0, 1]
            embedding.append(val)
        
        # Pad or truncate to desired dimension
        while len(embedding) < 256:
            embedding.append(0.0)
        
        return embedding[:256]
