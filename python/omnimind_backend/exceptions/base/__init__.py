"""Base exception classes for OmniMind.

Root exceptions that all other system exceptions inherit from.
"""

from .core import OmniMindError, SystemError
from .business import BusinessLogicError

__all__ = [
    "OmniMindError",
    "SystemError", 
    "BusinessLogicError",
]
