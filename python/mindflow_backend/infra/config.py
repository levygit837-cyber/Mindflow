"""Legacy configuration wrapper.

DEPRECATED: This module provides backward compatibility while migrating
to the new modular configuration in infra/config/.

Use mindflow_backend.infra.config.settings.get_settings() instead.
"""

import warnings
from functools import lru_cache

# Import new modular configuration
from mindflow_backend.infra.config.settings import Settings, get_settings as _get_settings

# Legacy exports for backward compatibility
__all__ = ["Settings", "get_settings"]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance.
    
    DEPRECATED: Use mindflow_backend.infra.config.settings.get_settings() instead.
    
    Returns:
        Settings instance with configuration loaded.
    """
    warnings.warn(
        "infra.config.get_settings() is deprecated. Use infra.config.settings.get_settings() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return _get_settings()
