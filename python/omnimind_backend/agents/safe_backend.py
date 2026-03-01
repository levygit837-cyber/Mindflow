"""Backward-compatible shim — canonical location: omnimind_backend.runtime.safe_backend"""

from omnimind_backend.runtime.safe_backend import (  # noqa: F401
    BackendProtocol,
    ExecuteResult,
    SafeBackend,
)

__all__ = ["BackendProtocol", "ExecuteResult", "SafeBackend"]
