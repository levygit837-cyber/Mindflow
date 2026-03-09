"""Shared Core Interfaces.

Interfaces base, tipos e exceções compartilhadas entre todos os tipos de memória.
"""

from .interfaces import MemoryServiceInterface
from .types import MemoryRetrievalResult
from .exceptions import MemoryError, RetrievalError

__all__ = [
    "MemoryServiceInterface",
    "MemoryRetrievalResult",
    "MemoryError", 
    "RetrievalError",
]
