"""Context providers for QueryEngine.

Each provider fetches contextual data from a different source:
- GitProvider: git status, diffs, branch info
- FileProvider: file contents, directory listings
- MemoryProvider: session/project memory retrieval

Providers implement the ContextProvider protocol from engine.py.
"""

from mindflow_backend.query.providers.base import BaseContextProvider
from mindflow_backend.query.providers.git_provider import GitProvider
from mindflow_backend.query.providers.file_provider import FileProvider
from mindflow_backend.query.providers.memory_provider import MemoryProvider

__all__ = [
    "BaseContextProvider",
    "GitProvider",
    "FileProvider",
    "MemoryProvider",
]