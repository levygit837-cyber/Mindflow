"""Project Memory — Persistent code index with exact and semantic search.

This module provides a persistent index of all code elements (functions, classes,
methods) in a project, enabling:
- Exact search by name
- Semantic search by similarity
- Full source code retrieval
"""

from mindflow_backend.memory.project_memory.models import (
    CodeElement,
    CodeType,
    ProjectMemory,
)
from mindflow_backend.memory.project_memory.search import ProjectMemorySearch
from mindflow_backend.memory.project_memory.storage import ProjectMemoryStorage

__all__ = [
    "CodeElement",
    "CodeType",
    "ProjectMemory",
    "ProjectMemorySearch",
    "ProjectMemoryStorage",
]