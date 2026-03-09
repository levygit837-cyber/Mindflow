"""Legacy logging wrapper.

DEPRECATED: This module provides backward compatibility while migrating
to the new modular logging infrastructure in infra/logging/.

Use mindflow_backend.infra.logging.structured.get_logger() instead.
"""

import warnings
from functools import lru_cache

# Import new modular logging
from mindflow_backend.infra.logging.structured import (
    configure_logging as _configure_logging,
    get_logger as _get_logger,
    reset_logging as _reset_logging,
)

# Legacy exports for backward compatibility
__all__ = ["configure_logging", "get_logger", "reset_logging"]


def configure_logging(level: str = "INFO"):
    """Configure structured logging with given level."""
    from mindflow_backend.infra.logging.structured import configure_logging as _configure_structured_logging
    
    _configure_structured_logging(level)


@lru_cache(maxsize=1)
def get_logger(name: str):
    """Return a structlog bound logger with given name."""
    from mindflow_backend.infra.logging.structured import get_logger as _get_structured_logger
    
    return _get_structured_logger(name)


def reset_logging() -> None:
    """Reset logging configuration (for testing)."""
    from mindflow_backend.infra.logging.structured import reset_logging as _reset_structured_logging
    
    _reset_structured_logging()
