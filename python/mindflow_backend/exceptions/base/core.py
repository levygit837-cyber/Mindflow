"""Backward-compatibility shim for exceptions.base.core.

Re-exports all classes from core_new.py. New code should import
directly from `mindflow_backend.exceptions.base.core_new` or the
top-level `mindflow_backend.exceptions` package.
"""

from .core_new import (
    MindFlowError,
    SystemError,
    BusinessLogicError,
    InfrastructureError,
    NetworkError,
    TimeoutError,
    ResourceError,
    ErrorFactory,
)

__all__ = [
    "MindFlowError",
    "SystemError",
    "BusinessLogicError",
    "InfrastructureError",
    "NetworkError",
    "TimeoutError",
    "ResourceError",
    "ErrorFactory",
]
