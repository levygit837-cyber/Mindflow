"""Memory system exceptions."""


class MemoryError(Exception):
    """Base exception for memory operations."""
    pass


class RetrievalError(MemoryError):
    """Exception for memory retrieval operations."""
    pass
