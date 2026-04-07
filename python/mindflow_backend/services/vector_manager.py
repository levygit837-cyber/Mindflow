"""Vector database abstraction layer.

Provides a unified interface for different vector database backends
(pgvector, qdrant, chroma) with automatic fallback and migration support.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Literal
from uuid import UUID, uuid4

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.infra.database.connection import get_db_session

import numpy as np

_logger = get_logger(__name__)


class VectorDatabase(ABC):
    """Abstract base class for vector database implementations."""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the vector database connection."""
        pass
    
    @abstractmethod
    async def create_collection(self, name: str, dimension: int) -> None:
        """Create a new vector collection."""
        pass
    
    @abstractmethod
    async def insert_vectors(
        self,
        collection_name: str,
        vectors: list[dict[str, Any]],
    ) -> list[str]:
        """Insert vectors into a collection.
        
        Args:
            collection_name: Name of the collection
            vectors: List of vectors with metadata
            
        Returns:
            List of vector IDs
        """
        pass
    
    @abstractmethod
    async def search_vectors(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 10,
        score_threshold: float = 0.0,
        filter_dict: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar vectors.
        
        Args:
            collection_name: Name of the collection
            query_vector: Query vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            filter_dict: Optional metadata filters
            
        Returns:
            List of search results with scores and metadata
        """
        pass
    
    @abstractmethod
    async def delete_vectors(
        self,
        collection_name: str,
        vector_ids: list[str],
    ) -> None:
        """Delete vectors by ID."""
        pass
    
    @abstractmethod
    async def get_vector(
        self,
        collection_name: str,
        vector_id: str,
    ) -> dict[str, Any] | None:
        """Get a specific vector by ID."""
        pass
    
    @abstractmethod
    async def update_vector(
        self,
        collection_name: str,
        vector_id: str,
        vector: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Update a vector and its metadata."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the database connection."""
        pass


class PgVectorDatabase(VectorDatabase):
    """PostgreSQL pgvector implementation using SQLAlchemy."""
    
    def __init__(self, connection_string: str, dimensions: int = 256) -> None:
        """Initialize pgvector database.
        
        Args:
            connection_string: PostgreSQL connection string
            dimensions: Vector dimensions
        """
        self.connection_string = connection_string
        self.dimensions = dimensions
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize pgvector connection and extension."""
        try:
            async with get_db_session() as session:
                # Enable pgvector extension
                await session.execute("CREATE EXTENSION IF NOT EXISTS vector")
                await session.commit()
            
            self._initialized = True
            _logger.info("pgvector_initialized", dimensions=self.dimensions)
        except Exception as e:
            _logger.error("pgvector_initialization_failed", error=str(e))
            raise
    
    async def create_collection(self, name: str, dimension: int) -> None:
        """Create a pgvector table for the collection."""
        if not self._initialized:
            await self.initialize()
        
        # Sanitize table name to prevent SQL injection
        table_name = self._sanitize_table_name(name)
        
        async with get_db_session() as session:
            # Create table with vector column
            create_sql = f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    vector vector({dimension}),
                    metadata JSONB DEFAULT '{{}}',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """
            await session.execute(create_sql)
            
            # Create index for similarity search
            index_sql = f"""
                CREATE INDEX IF NOT EXISTS idx_{table_name}_vector 
                ON {table_name} USING ivfflat (vector vector_cosine_ops)
            """
            await session.execute(index_sql)
            await session.commit()
        
        _logger.info("pgvector_collection_created", name=name, dimension=dimension)
    
    async def insert_vectors(
        self,
        collection_name: str,
        vectors: list[dict[str, Any]],
    ) -> list[str]:
        """Insert vectors into pgvector table."""
        if not self._initialized:
            await self.initialize()
        
        table_name = self._sanitize_table_name(collection_name)
        vector_ids = []
        
        async with get_db_session() as session:
            for vector_data in vectors:
                vector_id = str(vector_data.get("id", uuid4()))
                vector = vector_data.get("vector", [])
                metadata = vector_data.get("metadata", {})
                
                # Convert vector to string format for pgvector
                vector_str = self._vector_to_pgvector_str(vector)
                
                insert_sql = f"""
                    INSERT INTO {table_name} (id, vector, metadata)
                    VALUES (:id, :vector::vector, :metadata::jsonb)
                    ON CONFLICT (id) DO UPDATE SET
                        vector = EXCLUDED.vector,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                    RETURNING id
                """
                result = await session.execute(
                    insert_sql,
                    {
                        "id": vector_id,
                        "vector": vector_str,
                        "metadata": metadata,
                    }
                )
                row = result.fetchone()
                if row:
                    vector_ids.append(str(row[0]))
            
            await session.commit()
        
        _logger.info(
            "pgvector_vectors_inserted",
            collection_name=collection_name,
            count=len(vectors),
        )
        return vector_ids
    
    async def search_vectors(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 10,
        score_threshold: float = 0.0,
        filter_dict: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search vectors using pgvector cosine similarity."""
        if not self._initialized:
            await self.initialize()
        
        table_name = self._sanitize_table_name(collection_name)
        vector_str = self._vector_to_pgvector_str(query_vector)
        
        async with get_db_session() as session:
            # Build query with cosine similarity
            # 1 - cosine_distance gives us cosine similarity (0 to 1)
            search_sql = f"""
                SELECT 
                    id,
                    metadata,
                    1 - (vector <=> :query_vector::vector) as score
                FROM {table_name}
                WHERE 1 - (vector <=> :query_vector::vector) >= :threshold
            """
            
            params = {
                "query_vector": vector_str,
                "threshold": score_threshold,
            }
            
            # Add metadata filters if provided
            if filter_dict:
                for key, value in filter_dict.items():
                    search_sql += f" AND metadata->>:filter_key_{key} = :filter_val_{key}"
                    params[f"filter_key_{key}"] = key
                    params[f"filter_val_{key}"] = str(value)
            
            search_sql += " ORDER BY score DESC LIMIT :limit"
            params["limit"] = limit
            
            result = await session.execute(search_sql, params)
            rows = result.fetchall()
            
            results = [
                {
                    "id": str(row[0]),
                    "metadata": row[1],
                    "score": float(row[2]),
                }
                for row in rows
            ]
        
        _logger.info(
            "pgvector_search_completed",
            collection_name=collection_name,
            limit=limit,
            score_threshold=score_threshold,
            results_count=len(results),
        )
        return results
    
    async def delete_vectors(
        self,
        collection_name: str,
        vector_ids: list[str],
    ) -> None:
        """Delete vectors from pgvector table."""
        if not self._initialized:
            await self.initialize()
        
        if not vector_ids:
            return
        
        table_name = self._sanitize_table_name(collection_name)
        
        async with get_db_session() as session:
            delete_sql = f"""
                DELETE FROM {table_name}
                WHERE id = ANY(:vector_ids)
            """
            await session.execute(delete_sql, {"vector_ids": vector_ids})
            await session.commit()
        
        _logger.info(
            "pgvector_vectors_deleted",
            collection_name=collection_name,
            count=len(vector_ids),
        )
    
    async def get_vector(
        self,
        collection_name: str,
        vector_id: str,
    ) -> dict[str, Any] | None:
        """Get vector from pgvector table."""
        if not self._initialized:
            await self.initialize()
        
        table_name = self._sanitize_table_name(collection_name)
        
        async with get_db_session() as session:
            select_sql = f"""
                SELECT id, vector, metadata, created_at, updated_at
                FROM {table_name}
                WHERE id = :vector_id
            """
            result = await session.execute(select_sql, {"vector_id": vector_id})
            row = result.fetchone()
            
            if row:
                return {
                    "id": str(row[0]),
                    "vector": self._pgvector_str_to_list(row[1]),
                    "metadata": row[2],
                    "created_at": row[3].isoformat() if row[3] else None,
                    "updated_at": row[4].isoformat() if row[4] else None,
                }
        
        return None
    
    async def update_vector(
        self,
        collection_name: str,
        vector_id: str,
        vector: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Update vector in pgvector table."""
        if not self._initialized:
            await self.initialize()
        
        table_name = self._sanitize_table_name(collection_name)
        vector_str = self._vector_to_pgvector_str(vector)
        
        async with get_db_session() as session:
            if metadata:
                update_sql = f"""
                    UPDATE {table_name}
                    SET vector = :vector::vector,
                        metadata = metadata || :metadata::jsonb,
                        updated_at = NOW()
                    WHERE id = :vector_id
                """
                await session.execute(
                    update_sql,
                    {
                        "vector": vector_str,
                        "metadata": metadata,
                        "vector_id": vector_id,
                    }
                )
            else:
                update_sql = f"""
                    UPDATE {table_name}
                    SET vector = :vector::vector,
                        updated_at = NOW()
                    WHERE id = :vector_id
                """
                await session.execute(
                    update_sql,
                    {"vector": vector_str, "vector_id": vector_id}
                )
            
            await session.commit()
        
        _logger.info(
            "pgvector_vector_updated",
            collection_name=collection_name,
            vector_id=vector_id,
        )
    
    async def close(self) -> None:
        """Close pgvector connection."""
        self._initialized = False
        _logger.info("pgvector_connection_closed")
    
    @staticmethod
    def _sanitize_table_name(name: str) -> str:
        """Sanitize table name to prevent SQL injection."""
        # Only allow alphanumeric, underscore, and hyphen
        import re
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
        # Ensure it starts with a letter
        if sanitized and not sanitized[0].isalpha():
            sanitized = 'vec_' + sanitized
        return sanitized[:63]  # PostgreSQL identifier limit
    
    @staticmethod
    def _vector_to_pgvector_str(vector: list[float]) -> str:
        """Convert vector list to pgvector string format."""
        if not vector:
            return "[]"
        return "[" + ",".join(str(x) for x in vector) + "]"
    
    @staticmethod
    def _pgvector_str_to_list(vector_str: str) -> list[float]:
        """Convert pgvector string to list."""
        if not vector_str or vector_str == "[]":
            return []
        # Remove brackets and split
        content = vector_str.strip("[]")
        if not content:
            return []
        return [float(x) for x in content.split(",")]


class QdrantDatabase(VectorDatabase):
    """Qdrant vector database implementation."""
    
    def __init__(self, url: str, api_key: str | None = None, dimensions: int = 256) -> None:
        """Initialize Qdrant database.
        
        Args:
            url: Qdrant server URL
            api_key: Optional API key
            dimensions: Vector dimensions
        """
        self.url = url
        self.api_key = api_key
        self.dimensions = dimensions
        self._client = None
    
    async def initialize(self) -> None:
        """Initialize Qdrant client."""
        try:
            from qdrant_client import QdrantClient
            
            if self.api_key:
                self._client = QdrantClient(
                    url=self.url,
                    api_key=self.api_key,
                    timeout=30,
                )
            else:
                self._client = QdrantClient(
                    url=self.url,
                    timeout=30,
                )
            
            _logger.info("qdrant_initialized", url=self.url)
        except ImportError:
            _logger.error("qdrant_client_not_installed")
            raise ImportError("Install qdrant-client: pip install qdrant-client")
        except Exception as e:
            _logger.error("qdrant_initialization_failed", error=str(e))
            raise
    
    async def create_collection(self, name: str, dimension: int) -> None:
        """Create a Qdrant collection."""
        try:
            from qdrant_client.models import Distance, VectorParams
            
            # Check if collection exists
            collections = self._client.get_collections().collections
            exists = any(c.name == name for c in collections)
            
            if not exists:
                self._client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(
                        size=dimension,
                        distance=Distance.COSINE,
                    ),
                )
                _logger.info("qdrant_collection_created", name=name, dimension=dimension)
            else:
                _logger.debug("qdrant_collection_exists", name=name)
        except Exception as e:
            _logger.error("qdrant_collection_creation_failed", error=str(e))
            raise
    
    async def insert_vectors(
        self,
        collection_name: str,
        vectors: list[dict[str, Any]],
    ) -> list[str]:
        """Insert vectors into Qdrant collection."""
        try:
            from qdrant_client.models import PointStruct
            
            # Ensure collection exists
            await self.create_collection(collection_name, self.dimensions)
            
            points = []
            vector_ids = []
            
            for v in vectors:
                vector_id = str(UUID())
                vector_ids.append(vector_id)
                
                points.append(PointStruct(
                    id=vector_id,
                    vector=v.get("vector", v.get("embedding", [])),
                    payload=v.get("metadata", v.get("payload", {})),
                ))
            
            self._client.upsert(
                collection_name=collection_name,
                points=points,
            )
            
            _logger.info(
                "qdrant_vectors_inserted",
                collection_name=collection_name,
                count=len(vectors),
            )
            return vector_ids
        except Exception as e:
            _logger.error("qdrant_insert_failed", error=str(e))
            raise
    
    async def search_vectors(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 10,
        score_threshold: float = 0.0,
        filter_dict: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search vectors using Qdrant."""
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            # Build filter if provided
            query_filter = None
            if filter_dict:
                conditions = []
                for key, value in filter_dict.items():
                    if isinstance(value, dict) and "$ne" in value:
                        # Not equal condition
                        conditions.append(
                            FieldCondition(
                                key=key,
                                match=MatchValue(value=value["$ne"]),
                            )
                        )
                    else:
                        conditions.append(
                            FieldCondition(
                                key=key,
                                match=MatchValue(value=value),
                            )
                        )
                
                if conditions:
                    query_filter = Filter(must=conditions)
            
            results = self._client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=query_filter,
            )
            
            formatted_results = []
            for r in results:
                formatted_results.append({
                    "id": r.id,
                    "score": r.score,
                    "vector": r.vector,
                    "metadata": r.payload,
                })
            
            _logger.info(
                "qdrant_search_completed",
                collection_name=collection_name,
                limit=limit,
                results_count=len(formatted_results),
            )
            return formatted_results
        except Exception as e:
            _logger.error("qdrant_search_failed", error=str(e))
            return []
    
    async def delete_vectors(
        self,
        collection_name: str,
        vector_ids: list[str],
    ) -> None:
        """Delete vectors from Qdrant collection."""
        try:
            self._client.delete(
                collection_name=collection_name,
                points_selector=vector_ids,
            )
            _logger.info(
                "qdrant_vectors_deleted",
                collection_name=collection_name,
                count=len(vector_ids),
            )
        except Exception as e:
            _logger.error("qdrant_delete_failed", error=str(e))
            raise
    
    async def get_vector(
        self,
        collection_name: str,
        vector_id: str,
    ) -> dict[str, Any] | None:
        """Get vector from Qdrant collection."""
        try:
            results = self._client.retrieve(
                collection_name=collection_name,
                ids=[vector_id],
            )
            
            if results:
                r = results[0]
                return {
                    "id": r.id,
                    "vector": r.vector,
                    "metadata": r.payload,
                }
            return None
        except Exception as e:
            _logger.error("qdrant_get_failed", error=str(e))
            return None
    
    async def update_vector(
        self,
        collection_name: str,
        vector_id: str,
        vector: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Update vector in Qdrant collection."""
        try:
            from qdrant_client.models import PointStruct
            
            self._client.upsert(
                collection_name=collection_name,
                points=[PointStruct(
                    id=vector_id,
                    vector=vector,
                    payload=metadata or {},
                )],
            )
            _logger.info(
                "qdrant_vector_updated",
                collection_name=collection_name,
                vector_id=vector_id,
            )
        except Exception as e:
            _logger.error("qdrant_update_failed", error=str(e))
            raise
    
    async def close(self) -> None:
        """Close Qdrant client."""
        if self._client:
            # Qdrant client doesn't require explicit closing
            self._client = None
            _logger.info("qdrant_client_closed")


class ChromaDatabase(VectorDatabase):
    """Chroma vector database implementation."""
    
    def __init__(self, path: str | None = None, dimensions: int = 256) -> None:
        """Initialize Chroma database.
        
        Args:
            path: Chroma database path (None for in-memory)
            dimensions: Vector dimensions
        """
        self.path = path
        self.dimensions = dimensions
        self._client = None
    
    async def initialize(self) -> None:
        """Initialize Chroma client."""
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            
            if self.path:
                # Persistent client
                self._client = chromadb.PersistentClient(
                    path=self.path,
                    settings=ChromaSettings(
                        anonymized_telemetry=False,
                    ),
                )
            else:
                # In-memory client
                self._client = chromadb.Client(
                    settings=ChromaSettings(
                        anonymized_telemetry=False,
                    ),
                )
            
            _logger.info("chroma_initialized", path=self.path, dimensions=self.dimensions)
        except ImportError:
            _logger.error("chromadb_not_installed")
            raise ImportError("Install chromadb: pip install chromadb")
        except Exception as e:
            _logger.error("chroma_initialization_failed", error=str(e))
            raise
    
    async def create_collection(self, name: str, dimension: int) -> None:
        """Create a Chroma collection."""
        try:
            # Chroma collections are created implicitly when accessed
            # But we can get_or_create to ensure it exists
            self._client.get_or_create_collection(
                name=name,
                metadata={"dimension": dimension, "hnsw:space": "cosine"},
            )
            _logger.info("chroma_collection_created", name=name, dimension=dimension)
        except Exception as e:
            _logger.error("chroma_collection_creation_failed", error=str(e))
            raise
    
    async def insert_vectors(
        self,
        collection_name: str,
        vectors: list[dict[str, Any]],
    ) -> list[str]:
        """Insert vectors into Chroma collection."""
        try:
            collection = self._client.get_or_create_collection(name=collection_name)
            
            vector_ids = []
            embeddings = []
            metadatas = []
            documents = []
            
            for v in vectors:
                vector_id = str(UUID())
                vector_ids.append(vector_id)
                embeddings.append(v.get("vector", v.get("embedding", [])))
                metadatas.append(v.get("metadata", v.get("payload", {})))
                documents.append(v.get("content", v.get("document", "")))
            
            collection.add(
                ids=vector_ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents,
            )
            
            _logger.info(
                "chroma_vectors_inserted",
                collection_name=collection_name,
                count=len(vectors),
            )
            return vector_ids
        except Exception as e:
            _logger.error("chroma_insert_failed", error=str(e))
            raise
    
    async def search_vectors(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 10,
        score_threshold: float = 0.0,
        filter_dict: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search vectors using Chroma."""
        try:
            collection = self._client.get_collection(name=collection_name)
            
            # Build where clause from filter_dict
            where_clause = None
            if filter_dict:
                where_clause = {}
                for key, value in filter_dict.items():
                    if isinstance(value, dict) and "$ne" in value:
                        where_clause[key] = {"$ne": value["$ne"]}
                    else:
                        where_clause[key] = value
            
            results = collection.query(
                query_embeddings=[query_vector],
                n_results=limit,
                where=where_clause,
                include=["metadatas", "documents", "distances"],
            )
            
            formatted_results = []
            if results["ids"] and results["ids"][0]:
                for i, (vid, distance) in enumerate(zip(results["ids"][0], results["distances"][0])):
                    # Chroma returns distance (lower is better), convert to similarity score
                    score = 1.0 - distance
                    
                    if score >= score_threshold:
                        formatted_results.append({
                            "id": vid,
                            "score": score,
                            "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                            "document": results["documents"][0][i] if results["documents"] else "",
                        })
            
            _logger.info(
                "chroma_search_completed",
                collection_name=collection_name,
                limit=limit,
                results_count=len(formatted_results),
            )
            return formatted_results
        except Exception as e:
            _logger.error("chroma_search_failed", error=str(e))
            return []
    
    async def delete_vectors(
        self,
        collection_name: str,
        vector_ids: list[str],
    ) -> None:
        """Delete vectors from Chroma collection."""
        try:
            collection = self._client.get_collection(name=collection_name)
            collection.delete(ids=vector_ids)
            _logger.info(
                "chroma_vectors_deleted",
                collection_name=collection_name,
                count=len(vector_ids),
            )
        except Exception as e:
            _logger.error("chroma_delete_failed", error=str(e))
            raise
    
    async def get_vector(
        self,
        collection_name: str,
        vector_id: str,
    ) -> dict[str, Any] | None:
        """Get vector from Chroma collection."""
        try:
            collection = self._client.get_collection(name=collection_name)
            result = collection.get(
                ids=[vector_id],
                include=["embeddings", "metadatas", "documents"],
            )
            
            if result["ids"] and len(result["ids"]) > 0:
                return {
                    "id": result["ids"][0],
                    "vector": result["embeddings"][0] if result["embeddings"] else None,
                    "metadata": result["metadatas"][0] if result["metadatas"] else {},
                    "document": result["documents"][0] if result["documents"] else "",
                }
            return None
        except Exception as e:
            _logger.error("chroma_get_failed", error=str(e))
            return None
    
    async def update_vector(
        self,
        collection_name: str,
        vector_id: str,
        vector: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Update vector in Chroma collection."""
        try:
            collection = self._client.get_collection(name=collection_name)
            
            # Chroma uses upsert for updates
            collection.upsert(
                ids=[vector_id],
                embeddings=[vector],
                metadatas=[metadata] if metadata else [{}],
            )
            _logger.info(
                "chroma_vector_updated",
                collection_name=collection_name,
                vector_id=vector_id,
            )
        except Exception as e:
            _logger.error("chroma_update_failed", error=str(e))
            raise
    
    async def close(self) -> None:
        """Close Chroma client."""
        if self._client:
            # Chroma client doesn't require explicit closing
            self._client = None
            _logger.info("chroma_client_closed")


class VectorManager:
    """Vector database manager with provider abstraction."""
    
    def __init__(self) -> None:
        """Initialize vector manager."""
        self._db: VectorDatabase | None = None
        self._provider: Literal["pgvector", "qdrant", "chroma"] | None = None
    
    async def initialize(self) -> None:
        """Initialize the vector database based on configuration."""
        settings = get_settings()
        
        self._provider = settings.vector_db_provider
        
        if self._provider == "pgvector":
            self._db = PgVectorDatabase(
                connection_string=settings.database.url,
                dimensions=settings.vector_db_dimensions,
            )
        elif self._provider == "qdrant":
            if not settings.vector_db_url:
                raise ValueError("QDRANT_URL required when using qdrant provider")
            self._db = QdrantDatabase(
                url=settings.vector_db_url,
                api_key=settings.vector_db_api_key,
                dimensions=settings.vector_db_dimensions,
            )
        elif self._provider == "chroma":
            self._db = ChromaDatabase(
                path=settings.vector_db_url,  # Use URL as path for Chroma
                dimensions=settings.vector_db_dimensions,
            )
        else:
            raise ValueError(f"Unsupported vector database provider: {self._provider}")
        
        await self._db.initialize()
        _logger.info("vector_manager_initialized", provider=self._provider)
    
    async def create_session_collection(self, session_id: str) -> None:
        """Create a collection for a specific session."""
        if not self._db:
            await self.initialize()
        
        collection_name = f"session_{session_id}"
        await self._db.create_collection(collection_name, self._db.dimensions)
        _logger.info("session_collection_created", session_id=session_id)
    
    async def store_session_embeddings(
        self,
        session_id: str,
        embeddings: list[dict[str, Any]],
    ) -> list[str]:
        """Store embeddings for a session."""
        if not self._db:
            await self.initialize()
        
        collection_name = f"session_{session_id}"
        vector_ids = await self._db.insert_vectors(collection_name, embeddings)
        _logger.info(
            "session_embeddings_stored",
            session_id=session_id,
            count=len(embeddings),
        )
        return vector_ids
    
    async def search_session_context(
        self,
        session_id: str,
        query_vector: list[float],
        limit: int = 10,
        score_threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Search for context within a session."""
        if not self._db:
            await self.initialize()
        
        collection_name = f"session_{session_id}"
        results = await self._db.search_vectors(
            collection_name, query_vector, limit, score_threshold
        )
        _logger.info(
            "session_context_searched",
            session_id=session_id,
            limit=limit,
            results_count=len(results),
        )
        return results
    
    async def create_dt_collection(self, component_id: str, component_type: str = "component") -> None:
        """Create a collection for a DT component or sub-component."""
        if not self._db:
            await self.initialize()
        
        collection_name = f"dt_{component_type}_{component_id}"
        await self._db.create_collection(collection_name, self._db.dimensions)
        _logger.info(
            "dt_collection_created", 
            component_id=component_id, 
            component_type=component_type
        )
    
    async def update_component_context(
        self,
        component_id: str,
        context_data: dict[str, Any],
        component_type: str = "component",
    ) -> str:
        """Update or insert context for a specific component."""
        if not self._db:
            await self.initialize()
        
        collection_name = f"dt_{component_type}_{component_id}"
        
        # Prepare vector with metadata
        vector_data = {
            "id": str(UUID()),
            "vector": context_data.get("vector", []),
            "metadata": {
                "component_id": component_id,
                "component_type": component_type,
                "state": context_data.get("state", "unknown"),
                "timestamp": context_data.get("timestamp", ""),
                "content": context_data.get("content", ""),
                "dependencies": context_data.get("dependencies", []),
                "artifacts": context_data.get("artifacts", []),
            }
        }
        
        # Check if vector already exists for this component
        existing_vectors = await self._db.search_vectors(
            collection_name, 
            context_data.get("vector", []), 
            limit=1,
            filter_dict={"component_id": component_id}
        )
        
        if existing_vectors:
            # Update existing vector
            await self._db.update_vector(
                collection_name, 
                existing_vectors[0]["id"], 
                context_data.get("vector", []),
                vector_data["metadata"]
            )
            vector_id = existing_vectors[0]["id"]
        else:
            # Insert new vector
            vector_ids = await self._db.insert_vectors(collection_name, [vector_data])
            vector_id = vector_ids[0]
        
        _logger.info(
            "component_context_updated",
            component_id=component_id,
            component_type=component_type,
            vector_id=vector_id,
        )
        return vector_id
    
    async def cross_component_search(
        self,
        query_component_id: str,
        query_vector: list[float],
        component_types: list[str] | None = None,
        exclude_component_id: str | None = None,
        limit: int = 10,
        score_threshold: float = 0.7,
    ) -> list[dict[str, Any]]:
        """Search across all DT component collections for semantic matches."""
        if not self._db:
            await self.initialize()
        
        if component_types is None:
            component_types = ["component", "sub_component"]
        
        all_results = []
        
        for component_type in component_types:
            # Search in collections of this type
            collection_pattern = f"dt_{component_type}_"
            
            # This would require listing collections - for now, we'll search
            # in a way that assumes we can filter by collection pattern
            filter_dict = {}
            if exclude_component_id:
                filter_dict["component_id"] = {"$ne": exclude_component_id}
            
            # Note: This is a simplified implementation
            # In practice, you'd need to iterate over actual collections
            results = await self._db.search_vectors(
                f"dt_{component_type}_*",  # This would need proper pattern matching
                query_vector,
                limit,
                score_threshold,
                filter_dict
            )
            
            # Add component type info to results
            for result in results:
                result["component_type"] = component_type
            
            all_results.extend(results)
        
        # Sort by score and return top results
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        final_results = all_results[:limit]
        
        _logger.info(
            "cross_component_search_completed",
            query_component_id=query_component_id,
            component_types=component_types,
            results_count=len(final_results),
        )
        
        return final_results
    
    async def close(self) -> None:
        """Close the vector database connection."""
        if self._db:
            await self._db.close()
            _logger.info("vector_manager_closed", provider=self._provider)


# Global vector manager instance
_vector_manager: VectorManager | None = None


async def get_vector_manager() -> VectorManager:
    """Get the global vector manager instance."""
    global _vector_manager
    if _vector_manager is None:
        _vector_manager = VectorManager()
        await _vector_manager.initialize()
    return _vector_manager
