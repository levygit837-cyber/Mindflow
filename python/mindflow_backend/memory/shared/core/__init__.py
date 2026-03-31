"""Shared Core Interfaces.

Interfaces base, tipos e exceções compartilhadas entre todos os tipos de memória.
"""

from .exceptions import MemoryError, RetrievalError
from .interfaces import MemoryServiceInterface
from .types import MemoryRetrievalResult

__all__ = [
    "MemoryServiceInterface",
    "MemoryRetrievalResult",
    "MemoryError", 
    "RetrievalError",
]
