"""Configuration management interfaces.

Provides standardized interfaces for dynamic configuration management,
validation, and monitoring of component configurations.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Any, Union
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class ConfigValidationResult(Enum):
    """Result of configuration validation."""
    
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"
    REQUIRES_RESTART = "requires_restart"


@dataclass
class ConfigValidationError:
    """Configuration validation error details."""
    
    field: str
    message: str
    severity: str  # "error", "warning", "info"
    current_value: Any | None = None
    expected_value: Any | None = None
    suggested_fix: str | None = None


@dataclass
class ConfigValidationReport:
    """Complete configuration validation report."""
    
    result: ConfigValidationResult
    errors: list[ConfigValidationError]
    timestamp: datetime
    config_hash: str
    
    @property
    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return self.result in [ConfigValidationResult.VALID, ConfigValidationResult.WARNING]
    
    @property
    def has_errors(self) -> bool:
        """Check if there are any validation errors."""
        return any(error.severity == "error" for error in self.errors)


@dataclass
class ConfigChange:
    """Details of a configuration change."""
    
    field: str
    old_value: Any
    new_value: Any
    timestamp: datetime
    source: str  # "api", "file", "env", "database"
    requires_restart: bool = False


@runtime_checkable
class ConfigurableInterface(Protocol):
    """Interface for components that support dynamic configuration.
    
    Provides standardized methods for updating configuration,
    validating changes, and monitoring configuration state.
    """
    
    def update_config(self, config: dict[str, Any], source: str = "api") -> bool:
        """Update component configuration.
        
        Args:
            config: New configuration values
            source: Source of the configuration change
            
        Returns:
            True if configuration was updated successfully
            
        Raises:
            Exception: If configuration update fails
        """
        ...
    
    def get_config(self) -> dict[str, Any]:
        """Get current component configuration.
        
        Returns:
            Dictionary containing current configuration values
        """
        ...
    
    def validate_config(self, config: dict[str, Any]) -> ConfigValidationReport:
        """Validate configuration changes.
        
        Args:
            config: Configuration to validate
            
        Returns:
            Detailed validation report
        """
        ...
    
    def get_config_schema(self) -> dict[str, Any]:
        """Get the configuration schema for this component.
        
        Returns:
            JSON schema defining the expected configuration structure
        """
        ...
    
    def get_default_config(self) -> dict[str, Any]:
        """Get default configuration values.
        
        Returns:
            Dictionary containing default configuration values
        """
        ...
    
    def reset_config(self, fields: list[str] | None = None) -> bool:
        """Reset configuration to default values.
        
        Args:
            fields: Specific fields to reset, or None to reset all
            
        Returns:
            True if reset was successful
        """
        ...
    
    def get_config_changes(self, since: datetime | None = None) -> list[ConfigChange]:
        """Get history of configuration changes.
        
        Args:
            since: Get changes since this timestamp
            
        Returns:
            List of configuration changes
        """
        ...
    
    def reload_config(self) -> bool:
        """Reload configuration from source.
        
        Returns:
            True if reload was successful
        """
        ...


@runtime_checkable
class HotReloadableInterface(ConfigurableInterface, Protocol):
    """Interface for components that support hot configuration reloading.
    
    Extends ConfigurableInterface with capabilities for reloading
    configuration without requiring component restart.
    """
    
    def can_hot_reload(self, field: str) -> bool:
        """Check if a specific field can be hot reloaded.
        
        Args:
            field: Configuration field name
            
        Returns:
            True if field supports hot reload
        """
        ...
    
    async def hot_reload_config(self, config: dict[str, Any]) -> bool:
        """Hot reload configuration without restart.
        
        Args:
            config: New configuration values
            
        Returns:
            True if hot reload was successful
        """
        ...
    
    def get_hot_reloadable_fields(self) -> list[str]:
        """Get list of fields that support hot reload.
        
        Returns:
            List of field names that support hot reload
        """
        ...
    
    async def apply_config_change(self, change: ConfigChange) -> bool:
        """Apply a single configuration change.
        
        Args:
            change: Configuration change to apply
            
        Returns:
            True if change was applied successfully
        """
        ...


@runtime_checkable
class ConfigurableWithSecretsInterface(ConfigurableInterface, Protocol):
    """Interface for components that handle sensitive configuration.
    
    Extends ConfigurableInterface with capabilities for secure handling
    of secrets, API keys, and other sensitive configuration values.
    """
    
    def update_secret(self, secret_name: str, secret_value: str) -> bool:
        """Update a secret value.
        
        Args:
            secret_name: Name of the secret
            secret_value: New secret value
            
        Returns:
            True if secret was updated successfully
        """
        ...
    
    def get_secret_names(self) -> list[str]:
        """Get list of secret names this component uses.
        
        Returns:
            List of secret field names
        """
        ...
    
    def validate_secrets(self) -> ConfigValidationReport:
        """Validate all secrets are present and valid.
        
        Returns:
            Validation report for secrets
        """
        ...
    
    def rotate_secret(self, secret_name: str) -> bool:
        """Rotate a secret value.
        
        Args:
            secret_name: Name of the secret to rotate
            
        Returns:
            True if rotation was successful
        """
        ...
    
    def mask_secrets_in_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """Mask secret values in configuration for logging.
        
        Args:
            config: Configuration to mask
            
        Returns:
            Configuration with secrets masked
        """
        ...


@runtime_checkable
class ConfigurableWithEnvironmentInterface(ConfigurableInterface, Protocol):
    """Interface for components that support environment-specific configuration.
    
    Extends ConfigurableInterface with capabilities for managing different
    configuration environments (dev, staging, prod, etc.).
    """
    
    def get_environment(self) -> str:
        """Get current environment name.
        
        Returns:
            Current environment (e.g., 'dev', 'staging', 'prod')
        """
        ...
    
    def switch_environment(self, environment: str) -> bool:
        """Switch to a different environment configuration.
        
        Args:
            environment: Target environment
            
        Returns:
            True if switch was successful
        """
        ...
    
    def get_available_environments(self) -> list[str]:
        """Get list of available environments.
        
        Returns:
            List of environment names
        """
        ...
    
    def get_environment_config(self, environment: str) -> dict[str, Any]:
        """Get configuration for a specific environment.
        
        Args:
            environment: Environment name
            
        Returns:
            Configuration for the specified environment
        """
        ...
    
    def validate_environment_config(self, environment: str) -> ConfigValidationReport:
        """Validate configuration for a specific environment.
        
        Args:
            environment: Environment to validate
            
        Returns:
            Validation report for the environment
        """
        ...
