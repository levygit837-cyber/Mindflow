"""Configuration exceptions.

Exceptions for configuration loading, validation,
and environment setup errors.
"""

from __future__ import annotations

from omnimind_backend.exceptions.base.core import ConfigurationError as BaseConfigurationError


class ConfigurationError(BaseConfigurationError):
    """Infrastructure configuration error."""
    
    def __init__(
        self,
        message: str,
        *,
        config_source: str | None = None,
        environment: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            component="infrastructure",
            **kwargs
        )
        self.config_source = config_source
        self.environment = environment
