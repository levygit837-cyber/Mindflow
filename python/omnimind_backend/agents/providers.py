"""Backward-compatible shim — canonical location: omnimind_backend.runtime.providers"""

from omnimind_backend.runtime.providers import get_model_for_provider  # noqa: F401

__all__ = ["get_model_for_provider"]
