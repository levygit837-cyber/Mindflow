"""Storage layer for Project Memory.

Handles persistence of code elements across multiple backends:
- PostgreSQL + pgvector (data + embeddings)
- KuzuDB (dependency graph)
- JSON cache (fast access)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from mindflow_backend.memory.project_memory.models import CodeElement, CodeType, ProjectMemory

logger = logging.getLogger(__name__)


class ProjectMemoryStorage:
    """Persistent storage for Project Memory.
    
    Uses JSON files for simplicity. Can be extended to PostgreSQL/pgvector
    and KuzuDB for production use.
    """
    
    def __init__(self, project_id: str, storage_dir: str = ".mindflow/project_memory"):
        self.project_id = project_id
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.elements_file = self.storage_dir / f"{project_id}_elements.json"
        self.index_file = self.storage_dir / f"{project_id}_index.json"
        
        # In-memory cache
        self._memory: Optional[ProjectMemory] = None
    
    async def save_element(self, element: CodeElement) -> None:
        """Save a single code element."""
        # Load current memory
        memory = await self.load_memory()
        
        # Add element
        memory.add_element(element)
        
        # Persist
        await self._save_memory(memory)
    
    async def save_elements(self, elements: list[CodeElement]) -> None:
        """Save multiple code elements."""
        memory = await self.load_memory()
        
        for element in elements:
            memory.add_element(element)
        
        await self._save_memory(memory)
        logger.info(f"Saved {len(elements)} elements to Project Memory")
    
    async def get_element(self, element_id: str) -> Optional[CodeElement]:
        """Get element by ID."""
        memory = await self.load_memory()
        return memory.elements_by_id.get(element_id)
    
    async def search_by_name(self, name: str) -> list[CodeElement]:
        """Search elements by exact name."""
        memory = await self.load_memory()
        return memory.get_by_name(name)
    
    async def search_by_file(self, file_path: str) -> list[CodeElement]:
        """Get all elements in a file."""
        memory = await self.load_memory()
        return memory.get_by_file(file_path)
    
    async def search_by_type(self, code_type: CodeType) -> list[CodeElement]:
        """Get all elements of a type."""
        memory = await self.load_memory()
        return memory.get_by_type(code_type)
    
    async def search_by_embedding(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        min_similarity: float = 0.7,
    ) -> list[tuple[CodeElement, float]]:
        """Search by embedding similarity (cosine).
        
        Requires elements to have embeddings stored.
        """
        memory = await self.load_memory()
        
        results = []
        for element in memory.elements_by_id.values():
            if element.embedding is None:
                continue
            
            similarity = _cosine_similarity(query_embedding, element.embedding)
            if similarity >= min_similarity:
                results.append((element, similarity))
        
        # Sort by similarity descending
        results.sort(key=lambda x: -x[1])
        return results[:top_k]
    
    async def load_memory(self) -> ProjectMemory:
        """Load project memory from disk."""
        if self._memory is not None:
            return self._memory
        
        if self.index_file.exists():
            try:
                with open(self.index_file, "r") as f:
                    data = json.load(f)
                
                self._memory = ProjectMemory(
                    project_id=data["project_id"],
                    project_path=data.get("project_path", ""),
                    name=data.get("name", ""),
                    total_elements=data.get("total_elements", 0),
                    total_functions=data.get("total_functions", 0),
                    total_classes=data.get("total_classes", 0),
                    total_methods=data.get("total_methods", 0),
                    total_lines_indexed=data.get("total_lines_indexed", 0),
                    created_at=data.get("created_at", ""),
                    last_updated=data.get("last_updated", ""),
                )
                
                # Load elements
                if self.elements_file.exists():
                    with open(self.elements_file, "r") as f:
                        elements_data = json.load(f)
                    
                    for elem_data in elements_data:
                        element = CodeElement.from_dict(elem_data)
                        self._memory.elements_by_id[element.id] = element
                        self._memory.elements_by_name.setdefault(
                            element.name, []
                        ).append(element.id)
                        self._memory.elements_by_file.setdefault(
                            element.file_path, []
                        ).append(element.id)
                        self._memory.elements_by_type.setdefault(
                            element.type.value, []
                        ).append(element.id)
                
                logger.info(
                    f"Loaded Project Memory: {self._memory.total_elements} elements"
                )
                
            except Exception as e:
                logger.warning(f"Could not load Project Memory: {e}")
                self._memory = ProjectMemory(
                    project_id=self.project_id,
                    project_path="",
                    name="",
                )
        else:
            self._memory = ProjectMemory(
                project_id=self.project_id,
                project_path="",
                name="",
            )
        
        return self._memory
    
    async def _save_memory(self, memory: ProjectMemory) -> None:
        """Save memory to disk."""
        self._memory = memory
        
        # Save index
        index_data = memory.to_summary()
        index_data["project_path"] = memory.project_path
        index_data["name"] = memory.name
        
        with open(self.index_file, "w") as f:
            json.dump(index_data, f, indent=2)
        
        # Save elements (without embeddings to save space)
        elements_data = []
        for element in memory.elements_by_id.values():
            elem_dict = element.to_dict()
            # Don't save embeddings in JSON (too large)
            elem_dict.pop("embedding", None)
            elements_data.append(elem_dict)
        
        with open(self.elements_file, "w") as f:
            json.dump(elements_data, f, indent=2)
        
        logger.debug(f"Saved {len(elements_data)} elements to disk")
    
    async def clear(self) -> None:
        """Clear all stored data."""
        self._memory = None
        if self.elements_file.exists():
            self.elements_file.unlink()
        if self.index_file.exists():
            self.index_file.unlink()
    
    async def get_stats(self) -> dict[str, Any]:
        """Get storage statistics."""
        memory = await self.load_memory()
        return memory.to_summary()


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    if len(a) != len(b):
        return 0.0
    
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return dot_product / (norm_a * norm_b)