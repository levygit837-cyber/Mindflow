"""Environment profiles for gRPC configuration.

Provides environment-specific configuration profiles with
inheritance, overrides, and validation for different deployment
environments.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

from mindflow_backend.grpc.config import GrpcConfig
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


@dataclass
class ProfileConfig:
    """Configuration for an environment profile."""
    name: str
    description: str
    parent_profile: str | None = None
    overrides: dict[str, Any] = None
    
    def __post_init__(self):
        if self.overrides is None:
            self.overrides = {}


class EnvironmentProfile(ABC):
    """Abstract base class for environment profiles."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    @abstractmethod
    def get_overrides(self) -> dict[str, Any]:
        """Get configuration overrides for this profile."""
        pass
    
    def get_inherited_overrides(self) -> dict[str, Any]:
        """Get overrides including inherited from parent profile."""
        overrides = self.get_overrides()
        
        # Apply parent profile overrides if specified
        parent_name = self.get_parent_profile()
        if parent_name:
            parent_profile = EnvironmentProfileRegistry.get_profile(parent_name)
            if parent_profile:
                parent_overrides = parent_profile.get_inherited_overrides()
                # Merge with child overrides taking precedence
                overrides = {**parent_overrides, **overrides}
        
        return overrides
    
    def get_parent_profile(self) -> str | None:
        """Get parent profile name."""
        return getattr(self, 'parent_profile', None)
    
    def validate_environment(self) -> bool:
        """Validate if this profile is suitable for current environment."""
        return True


class DevelopmentProfile(EnvironmentProfile):
    """Development environment configuration profile."""
    
    def __init__(self):
        super().__init__(
            name="development",
            description="Development environment with debugging enabled"
        )
    
    def get_overrides(self) -> dict[str, Any]:
        return {
            # Server settings
            "debug_mode": True,
            "reflection_enabled": True,
            "secure": False,
            
            # Monitoring settings
            "enable_metrics": True,
            "enable_health_check": True,
            "health_check_interval_seconds": 10,  # More frequent for debugging
            
            # Performance settings
            "max_connections": 50,  # Lower for development
            "connection_timeout_seconds": 10,
            "default_timeout_seconds": 60,
            
            # Retry settings
            "max_attempts": 2,  # Fewer retries for faster debugging
            "retry_jitter": False,  # Predictable for debugging
            
            # Message sizes
            "max_receive_message_length": 2 * 1024 * 1024,  # 2MB
            "max_send_message_length": 2 * 1024 * 1024,     # 2MB
            
            # Circuit breaker
            "circuit_breaker_threshold": 3,  # More sensitive for testing
            "circuit_breaker_recovery_timeout": 30,  # Faster recovery
            
            # Logging
            "log_level": "DEBUG",
            "enable_performance_logging": True,
        }


class TestingProfile(EnvironmentProfile):
    """Testing environment configuration profile."""
    
    def __init__(self):
        super().__init__(
            name="testing",
            description="Testing environment with minimal configuration"
        )
        self.parent_profile = "development"
    
    def get_overrides(self) -> dict[str, Any]:
        return {
            # Server settings
            "debug_mode": False,
            "reflection_enabled": False,
            "secure": False,
            
            # Monitoring settings
            "enable_metrics": False,  # Disabled for clean test output
            "enable_health_check": True,
            "health_check_interval_seconds": 5,
            
            # Performance settings
            "max_connections": 10,  # Minimal for testing
            "connection_timeout_seconds": 5,
            "default_timeout_seconds": 30,
            
            # Retry settings
            "max_attempts": 1,  # No retries for predictable tests
            "retry_jitter": False,
            
            # Message sizes
            "max_receive_message_length": 1024 * 1024,  # 1MB
            "max_send_message_length": 1024 * 1024,     # 1MB
            
            # Circuit breaker
            "circuit_breaker_enabled": False,  # Disabled for testing
            
            # Logging
            "log_level": "ERROR",  # Minimal logging for tests
            "enable_performance_logging": False,
        }


class StagingProfile(EnvironmentProfile):
    """Staging environment configuration profile."""
    
    def __init__(self):
        super().__init__(
            name="staging",
            description="Staging environment with production-like settings"
        )
        self.parent_profile = "production"
    
    def get_overrides(self) -> dict[str, Any]:
        return {
            # Server settings
            "debug_mode": True,  # Keep debugging for staging
            "reflection_enabled": False,
            "secure": True,
            
            # Monitoring settings
            "enable_metrics": True,
            "enable_health_check": True,
            "health_check_interval_seconds": 30,
            
            # Performance settings
            "max_connections": 500,  # Medium capacity
            "connection_timeout_seconds": 30,
            "default_timeout_seconds": 300,
            
            # Retry settings
            "max_attempts": 3,
            "retry_jitter": True,
            
            # Message sizes
            "max_receive_message_length": 8 * 1024 * 1024,  # 8MB
            "max_send_message_length": 8 * 1024 * 1024,     # 8MB
            
            # Circuit breaker
            "circuit_breaker_threshold": 8,  # More lenient than production
            "circuit_breaker_recovery_timeout": 45,
            
            # Logging
            "log_level": "INFO",
            "enable_performance_logging": True,
        }


class ProductionProfile(EnvironmentProfile):
    """Production environment configuration profile."""
    
    def __init__(self):
        super().__init__(
            name="production",
            description="Production environment optimized for security and performance"
        )
    
    def get_overrides(self) -> dict[str, Any]:
        return {
            # Server settings
            "debug_mode": False,
            "reflection_enabled": False,
            "secure": True,
            
            # Monitoring settings
            "enable_metrics": True,
            "enable_health_check": True,
            "health_check_interval_seconds": 30,
            
            # Performance settings
            "max_connections": 1000,  # High capacity
            "connection_timeout_seconds": 30,
            "default_timeout_seconds": 300,
            
            # Retry settings
            "max_attempts": 3,
            "retry_jitter": True,
            
            # Message sizes
            "max_receive_message_length": 16 * 1024 * 1024,  # 16MB
            "max_send_message_length": 16 * 1024 * 1024,     # 16MB
            
            # Circuit breaker
            "circuit_breaker_threshold": 10,  # More resilient
            "circuit_breaker_recovery_timeout": 60,
            
            # Logging
            "log_level": "WARNING",  # Minimal logging in production
            "enable_performance_logging": False,
        }


class LocalProfile(EnvironmentProfile):
    """Local development profile."""
    
    def __init__(self):
        super().__init__(
            name="local",
            description="Local development profile with relaxed settings"
        )
        self.parent_profile = "development"
    
    def get_overrides(self) -> dict[str, Any]:
        return {
            # Server settings
            "host": "127.0.0.1",  # Localhost only
            "port": 50051,
            "debug_mode": True,
            "reflection_enabled": True,
            "secure": False,
            
            # Monitoring settings
            "enable_metrics": True,
            "enable_health_check": True,
            "health_check_interval_seconds": 15,
            
            # Performance settings
            "max_connections": 20,  # Very low for local
            "connection_timeout_seconds": 5,
            "default_timeout_seconds": 30,
            
            # Retry settings
            "max_attempts": 2,
            "retry_jitter": False,
            
            # Message sizes
            "max_receive_message_length": 1024 * 1024,  # 1MB
            "max_send_message_length": 1024 * 1024,     # 1MB
            
            # Circuit breaker
            "circuit_breaker_threshold": 2,  # Very sensitive for local debugging
            "circuit_breaker_recovery_timeout": 10,
            
            # Logging
            "log_level": "DEBUG",
            "enable_performance_logging": True,
        }


class EnvironmentProfileRegistry:
    """Registry for environment profiles."""
    
    _profiles: dict[str, EnvironmentProfile] = {}
    
    @classmethod
    def register_profile(cls, profile: EnvironmentProfile) -> None:
        """Register an environment profile."""
        cls._profiles[profile.name] = profile
        _logger.info("environment_profile_registered", name=profile.name)
    
    @classmethod
    def get_profile(cls, name: str) -> EnvironmentProfile | None:
        """Get environment profile by name."""
        return cls._profiles.get(name)
    
    @classmethod
    def get_all_profiles(cls) -> dict[str, EnvironmentProfile]:
        """Get all registered profiles."""
        return cls._profiles.copy()
    
    @classmethod
    def list_profile_names(cls) -> List[str]:
        """List all available profile names."""
        return list(cls._profiles.keys())
    
    @classmethod
    def validate_profile_name(cls, name: str) -> bool:
        """Check if profile name exists."""
        return name in cls._profiles


# Register default profiles
def _register_default_profiles():
    """Register default environment profiles."""
    profiles = [
        DevelopmentProfile(),
        TestingProfile(),
        StagingProfile(),
        ProductionProfile(),
        LocalProfile(),
    ]
    
    for profile in profiles:
        EnvironmentProfileRegistry.register_profile(profile)


# Auto-register default profiles
_register_default_profiles()


class EnvironmentLoader:
    """Loads and applies environment profiles to configuration."""
    
    def __init__(self):
        self.registry = EnvironmentProfileRegistry
    
    async def load_profile_config(self, profile_name: str, base_config: GrpcConfig) -> GrpcConfig:
        """Load configuration with profile overrides applied."""
        profile = self.registry.get_profile(profile_name)
        if not profile:
            _logger.error("profile_not_found", name=profile_name)
            return base_config
        
        # Get inherited overrides
        overrides = profile.get_inherited_overrides()
        
        # Apply overrides to base configuration
        config_dict = base_config.dict()
        config_dict.update(overrides)
        
        try:
            updated_config = GrpcConfig(**config_dict)
            _logger.info(
                "profile_config_loaded",
                profile=profile_name,
                overrides_count=len(overrides),
                parent_profile=profile.get_parent_profile()
            )
            return updated_config
            
        except Exception as exc:
            _logger.error("profile_config_apply_failed", profile=profile_name, error=str(exc))
            return base_config
    
    def get_profile_info(self, profile_name: str) -> dict[str, Any] | None:
        """Get information about a profile."""
        profile = self.registry.get_profile(profile_name)
        if not profile:
            return None
        
        return {
            "name": profile.name,
            "description": profile.description,
            "parent_profile": profile.get_parent_profile(),
            "overrides": profile.get_overrides(),
            "inherited_overrides": profile.get_inherited_overrides(),
        }
    
    def list_profiles(self) -> List[dict[str, Any]]:
        """List all available profiles with information."""
        profiles_info = []
        for profile_name in self.registry.list_profile_names():
            profile_info = self.get_profile_info(profile_name)
            if profile_info:
                profiles_info.append(profile_info)
        
        return profiles_info
    
    async def detect_environment(self) -> str:
        """Detect current environment from environment variables."""
        import os
        
        # Check explicit environment variable
        env = os.getenv("APP_ENV", "").lower()
        if env in self.registry.list_profile_names():
            return env
        
        # Check common environment indicators
        if os.getenv("PYTHONPATH", "").endswith("test"):
            return "testing"
        
        if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
            return "testing"
        
        if os.getenv("STAGING") or os.getenv("STAGE"):
            return "staging"
        
        if os.getenv("PRODUCTION") or os.getenv("PROD"):
            return "production"
        
        # Default to development for local
        return "development"
    
    async def auto_load_profile(self, base_config: GrpcConfig) -> GrpcConfig:
        """Auto-detect and load appropriate profile."""
        detected_env = await self.detect_environment()
        _logger.info("auto_detecting_environment", environment=detected_env)
        
        return await self.load_profile_config(detected_env, base_config)


# Global environment loader instance
_environment_loader: EnvironmentLoader | None = None


def get_environment_loader() -> EnvironmentLoader:
    """Get global environment loader instance."""
    global _environment_loader
    if _environment_loader is None:
        _environment_loader = EnvironmentLoader()
    return _environment_loader


# Utility functions
def create_profile_config(profile_name: str, **overrides) -> ProfileConfig:
    """Create a custom profile configuration."""
    return ProfileConfig(
        name=profile_name,
        description=f"Custom profile: {profile_name}",
        overrides=overrides
    )


def register_custom_profile(name: str, description: str, overrides: dict[str, Any], 
                          parent_profile: str | None = None) -> EnvironmentProfile:
    """Register a custom environment profile."""
    
    class CustomProfile(EnvironmentProfile):
        def __init__(self, name: str, description: str, overrides: dict[str, Any], parent: str | None = None):
            super().__init__(name, description)
            self._overrides = overrides
            self.parent_profile = parent
        
        def get_overrides(self) -> dict[str, Any]:
            return self._overrides
    
    profile = CustomProfile(name, description, overrides, parent_profile)
    EnvironmentProfileRegistry.register_profile(profile)
    return profile
