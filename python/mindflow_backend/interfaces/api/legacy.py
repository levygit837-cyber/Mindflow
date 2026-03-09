"""Legacy API interfaces for controllers and services.

This module provides backward compatibility for API interfaces
that have been migrated to specific modules.
"""

from .controllers import ControllerInterface
from .services import ServiceInterface

__all__ = ["ControllerInterface", "ServiceInterface"]
