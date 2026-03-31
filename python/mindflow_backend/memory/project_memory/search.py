"""Search API for Project Memory.

Provides exact and semantic search over indexed code elements.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from mindflow_backend.memory.project_memory.models import CodeElement, CodeType
from mindflow_backend.memory.project_memory.storage import ProjectMemoryStorage

logger = logging.getLogger(__name__)


class ProjectMemorySearch:
    """Search interface for Project Memory.
    
    Supports:
    - Exact search by name
    - Semantic search by similarity
    - Filtered search by type or file
    - Full source code retrieval
    """
    
    def __init__(self, storage: ProjectMemoryStorage):
        self.storage = storage
    
    async def find_exact(
        self,
        name: str,
        code_type: Optional[CodeType] = None,
        file_path: Optional[str] = None,
    ) -> list[CodeElement]:
        """Search by exact name.
        
        Args:
            name: Exact name to search for
            code_type: Optional filter by type
            file_path: Optional filter by file
            
        Returns:
            List of matching elements
            
        Examples:
            await search.find_exact("authenticate_user")
            await search.find_exact("UserModel", code_type=CodeType.CLASS)
        """
        results = await self.storage.search_by_name(name)
        
        if code_type:
            results = [r for r in results if r.type == code_type]
        if file_path:
            results = [r for r in results if r.file_path == file_path]
        
        return results
    
    async def find_similar(
        self,
        query: str,
        top_k: int = 10,
        min_similarity: float = 0.7,
        code_type: Optional[CodeType] = None,
    ) -> list[tuple[CodeElement, float]]:
        """Semantic search by similarity.
        
        Uses cosine similarity on embeddings to find code elements
        that semantically match the query.
        
        Args:
            query: Natural language query
            top_k: Maximum results to return
            min_similarity: Minimum similarity score (0-1)
            code_type: Optional filter by type
            
        Returns:
            List of (element, similarity_score) tuples
            
        Examples:
            await search.find_similar("função que valida email")
            await search.find_similar("classe de conexão com banco")
        """
        # Note: This requires an embedding service to convert query to vector
        # For now, return empty if no embeddings available
        memory = await self.storage.load_memory()
        
        # Simple text-based similarity as fallback
        results = []
        query_lower = query.lower()
        
        for element in memory.elements_by_id.values():
            if code_type and element.type != code_type:
                continue
            
            # Text similarity (simple keyword matching)
            searchable = element.to_searchable_text().lower()
            score = _text_similarity(query_lower, searchable)
            
            if score >= min_similarity:
                results.append((element, score))
        
        results.sort(key=lambda x: -x[1])
        return results[:top_k]
    
    async def get_full_source(self, element_id: str) -> Optional[str]:
        """Get full source code of an element.
        
        Args:
            element_id: ID of the element
            
        Returns:
            Full source code or None if not found
        """
        element = await self.storage.get_element(element_id)
        return element.full_source if element else None
    
    async def get_by_file(self, file_path: str) -> list[CodeElement]:
        """Get all elements in a file."""
        return await self.storage.search_by_file(file_path)
    
    async def get_by_type(self, code_type: CodeType) -> list[CodeElement]:
        """Get all elements of a type."""
        return await self.storage.search_by_type(code_type)
    
    async def get_dependencies(self, element_id: str) -> list[CodeElement]:
        """Get dependencies of an element."""
        element = await self.storage.get_element(element_id)
        if not element:
            return []
        
        deps = []
        for dep_name in element.dependencies:
            found = await self.storage.search_by_name(dep_name)
            deps.extend(found)
        
        return deps


def _text_similarity(query: str, text: str) -> float:
    """Simple text similarity based on word overlap."""
    query_words = set(query.split())
    text_words = set(text.split())
    
    if not query_words or not text_words:
        return 0.0
    
    intersection = query_words & text_words
    union = query_words | text_words
    
    return len(intersection) / len(union) if union else 0.0