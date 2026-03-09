"""Legacy configuration wrapper.

DEPRECATED: This module is deprecated and will be removed in v2.0.
Use mindflow_backend.infra.config.settings.get_settings() instead.

For backward compatibility, this module will redirect to the new system.
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
    
    DEPRECATED: This function is deprecated. Use mindflow_backend.infra.config.settings.get_settings() instead.
    Will be removed in v2.0.
    
    Returns:
        Settings instance with configuration loaded.
    """
    warnings.warn(
        "infra.config.get_settings() is deprecated and will be removed in v2.0. "
        "Use infra.config.settings.get_settings() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return _get_settings()
