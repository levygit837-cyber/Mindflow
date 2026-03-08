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


def configure_logging(level: int = 20) -> None:
    """Configure structlog + stdlib logging.
    
    DEPRECATED: Use mindflow_backend.infra.logging.structured.configure_logging() instead.
    
    Args:
        level: Logging level to configure
    """
    warnings.warn(
        "infra.logging.configure_logging() is deprecated. Use infra.logging.structured.configure_logging() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return _configure_logging(level)


@lru_cache(maxsize=1)
def get_logger(name: str):
    """Return a structlog bound logger with the given name.
    
    DEPRECATED: Use mindflow_backend.infra.logging.structured.get_logger() instead.
    
    Args:
        name: Logger name
        
    Returns:
        Structlog bound logger
    """
    warnings.warn(
        "infra.logging.get_logger() is deprecated. Use infra.logging.structured.get_logger() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return _get_logger(name)


def reset_logging() -> None:
    """Reset the configured flag (for testing).
    
    DEPRECATED: Use mindflow_backend.infra.logging.structured.reset_logging() instead.
    """
    warnings.warn(
        "infra.logging.reset_logging() is deprecated. Use infra.logging.structured.reset_logging() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return _reset_logging()
