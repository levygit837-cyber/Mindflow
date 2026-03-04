"""Infrastructure interfaces.

Provides contracts for backend operations, storage,
and other infrastructure components.
"""

from .backend import BackendProtocol

__all__ = [
    "BackendProtocol",
]
