"""Feature flags system for gRPC dynamic configuration.

Provides dynamic feature toggling, percentage-based rollouts,
A/B testing support, and feature dependency management.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

from omnimind_backend.grpc.config.dynamic.storage import ConfigStorage, MemoryConfigStorage
from omnimind_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class FeatureState(Enum):
    """Feature flag states."""
    DISABLED = "disabled"
    ENABLED = "enabled"
    PERCENTAGE = "percentage"
    CONDITIONAL = "conditional"


@dataclass
class FeatureFlag:
    """Individual feature flag configuration."""
    name: str
    description: str
    default_state: FeatureState
    current_state: FeatureState
    rollout_percentage: float = 100.0
    dependencies: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    requires_restart: bool = False
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert feature flag to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "default_state": self.default_state.value,
            "current_state": self.current_state.value,
            "rollout_percentage": self.rollout_percentage,
            "dependencies": self.dependencies,
            "conditions": self.conditions,
            "metadata": self.metadata,
            "requires_restart": self.requires_restart,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class FeatureEvaluationContext:
    """Context for feature flag evaluation."""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    environment: str = "development"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_hash_key(self) -> str:
        """Get hash key for percentage-based rollouts."""
        key_parts = [self.user_id or "", self.session_id or "", self.request_id or ""]
        return ":".join(key_parts)


class FeatureRegistry:
    """Registry for gRPC feature flags."""
    
    # Default gRPC feature flags
    DEFAULT_FLAGS = {
        "grpc_monitoring_enabled": {
            "description": "Enable gRPC metrics collection",
            "default_state": FeatureState.ENABLED,
            "dependencies": [],
            "requires_restart": False,
        },
        "grpc_health_check_enabled": {
            "description": "Enable gRPC health check service",
            "default_state": FeatureState.ENABLED,
            "dependencies": [],
            "requires_restart": False,
        },
        "grpc_circuit_breaker_enabled": {
            "description": "Enable circuit breaker protection",
            "default_state": FeatureState.ENABLED,
            "dependencies": ["grpc_monitoring_enabled"],
            "requires_restart": False,
        },
        "grpc_retry_enabled": {
            "description": "Enable retry policies",
            "default_state": FeatureState.ENABLED,
            "dependencies": [],
            "requires_restart": False,
        },
        "grpc_compression_enabled": {
            "description": "Enable message compression",
            "default_state": FeatureState.DISABLED,
            "dependencies": [],
            "requires_restart": False,
        },
        "grpc_tls_enabled": {
            "description": "Enable TLS encryption",
            "default_state": FeatureState.DISABLED,
            "dependencies": [],
            "requires_restart": True,
        },
        "grpc_reflection_enabled": {
            "description": "Enable gRPC reflection service",
            "default_state": FeatureState.DISABLED,
            "dependencies": [],
            "requires_restart": True,
        },
        "grpc_timeout_adaptive": {
            "description": "Enable adaptive timeout management",
            "default_state": FeatureState.ENABLED,
            "dependencies": ["grpc_retry_enabled"],
            "requires_restart": False,
        },
        "grpc_deadline_propagation": {
            "description": "Enable deadline propagation",
            "default_state": FeatureState.ENABLED,
            "dependencies": [],
            "requires_restart": False,
        },
        "grpc_connection_pooling": {
            "description": "Enable connection pooling",
            "default_state": FeatureState.ENABLED,
            "dependencies": [],
            "requires_restart": False,
        },
        "grpc_load_balancing": {
            "description": "Enable client-side load balancing",
            "default_state": FeatureState.DISABLED,
            "dependencies": ["grpc_connection_pooling"],
            "requires_restart": False,
        },
        "grpc_distributed_tracing": {
            "description": "Enable distributed tracing",
            "default_state": FeatureState.DISABLED,
            "dependencies": ["grpc_monitoring_enabled"],
            "requires_restart": False,
        },
    }
    
    def __init__(self):
        self._flags: Dict[str, FeatureFlag] = {}
        self._lock = asyncio.Lock()
        self._initialize_default_flags()
    
    def _initialize_default_flags(self):
        """Initialize default gRPC feature flags."""
        for name, config in self.DEFAULT_FLAGS.items():
            flag = FeatureFlag(
                name=name,
                description=config["description"],
                default_state=config["default_state"],
                current_state=config["default_state"],
                dependencies=config.get("dependencies", []),
                requires_restart=config.get("requires_restart", False),
            )
            self._flags[name] = flag
    
    async def register_flag(self, flag: FeatureFlag) -> bool:
        """Register a new feature flag."""
        async with self._lock:
            if flag.name in self._flags:
                _logger.warning("feature_flag_already_exists", name=flag.name)
                return False
            
            self._flags[flag.name] = flag
            _logger.info("feature_flag_registered", name=flag.name)
            return True
    
    async def update_flag(self, name: str, **updates) -> bool:
        """Update an existing feature flag."""
        async with self._lock:
            if name not in self._flags:
                _logger.error("feature_flag_not_found", name=name)
                return False
            
            flag = self._flags[name]
            
            # Update fields
            for field, value in updates.items():
                if hasattr(flag, field):
                    setattr(flag, field, value)
            
            flag.updated_at = time.time()
            _logger.info("feature_flag_updated", name=name, updates=list(updates.keys()))
            return True
    
    async def get_flag(self, name: str) -> Optional[FeatureFlag]:
        """Get feature flag by name."""
        async with self._lock:
            return self._flags.get(name)
    
    async def get_all_flags(self) -> Dict[str, FeatureFlag]:
        """Get all feature flags."""
        async with self._lock:
            return self._flags.copy()
    
    async def list_flag_names(self) -> List[str]:
        """List all feature flag names."""
        async with self._lock:
            return list(self._flags.keys())


class FeatureToggles:
    """Feature toggle evaluation engine."""
    
    def __init__(self, storage: Optional[ConfigStorage] = None):
        self.storage = storage or MemoryConfigStorage()
        self.registry = FeatureRegistry()
        self._lock = asyncio.Lock()
        self._evaluation_cache: Dict[str, bool] = {}
        self._cache_ttl = 60  # Cache for 60 seconds
        self._cache_timestamps: Dict[str, float] = {}
    
    async def initialize(self) -> bool:
        """Initialize feature toggles from storage."""
        try:
            # Load feature flags from storage
            await self._load_flags_from_storage()
            _logger.info("feature_toggles_initialized")
            return True
        except Exception as exc:
            _logger.error("feature_toggles_initialization_failed", error=str(exc))
            return False
    
    async def is_enabled(self, flag_name: str, context: Optional[FeatureEvaluationContext] = None) -> bool:
        """Check if a feature flag is enabled."""
        # Check cache first
        cache_key = self._get_cache_key(flag_name, context)
        if self._is_cache_valid(cache_key):
            return self._evaluation_cache[cache_key]
        
        async with self._lock:
            try:
                # Get feature flag
                flag = await self.registry.get_flag(flag_name)
                if not flag:
                    _logger.warning("feature_flag_not_found", name=flag_name)
                    return False
                
                # Evaluate feature flag
                result = await self._evaluate_flag(flag, context or FeatureEvaluationContext())
                
                # Cache result
                self._evaluation_cache[cache_key] = result
                self._cache_timestamps[cache_key] = time.time()
                
                return result
                
            except Exception as exc:
                _logger.error("feature_evaluation_failed", flag=flag_name, error=str(exc))
                return False
    
    async def enable_flag(self, flag_name: str, context: Optional[FeatureEvaluationContext] = None) -> bool:
        """Enable a feature flag."""
        return await self._set_flag_state(flag_name, FeatureState.ENABLED, context)
    
    async def disable_flag(self, flag_name: str, context: Optional[FeatureEvaluationContext] = None) -> bool:
        """Disable a feature flag."""
        return await self._set_flag_state(flag_name, FeatureState.DISABLED, context)
    
    async def set_percentage_rollout(self, flag_name: str, percentage: float) -> bool:
        """Set percentage-based rollout for a feature flag."""
        if not (0 <= percentage <= 100):
            _logger.error("invalid_percentage", percentage=percentage)
            return False
        
        success = await self.registry.update_flag(
            flag_name,
            current_state=FeatureState.PERCENTAGE,
            rollout_percentage=percentage,
            updated_at=time.time()
        )
        
        if success:
            await self._save_flags_to_storage()
            # Clear cache for this flag
            await self._clear_flag_cache(flag_name)
            _logger.info("percentage_rollout_set", flag=flag_name, percentage=percentage)
        
        return success
    
    async def get_config_overrides(self) -> Dict[str, Any]:
        """Get configuration overrides based on enabled features."""
        overrides = {}
        flags = await self.registry.get_all_flags()
        
        for flag_name, flag in flags.items():
            if await self.is_enabled(flag_name):
                # Add feature-specific configuration overrides
                flag_overrides = self._get_flag_config_overrides(flag)
                overrides.update(flag_overrides)
        
        return overrides
    
    async def _evaluate_flag(self, flag: FeatureFlag, context: FeatureEvaluationContext) -> bool:
        """Evaluate a feature flag based on its state and context."""
        # Check dependencies first
        for dependency in flag.dependencies:
            if not await self.is_enabled(dependency, context):
                _logger.debug("feature_dependency_disabled", flag=flag_name, dependency=dependency)
                return False
        
        # Evaluate based on current state
        if flag.current_state == FeatureState.DISABLED:
            return False
        
        elif flag.current_state == FeatureState.ENABLED:
            return True
        
        elif flag.current_state == FeatureState.PERCENTAGE:
            return self._evaluate_percentage_rollout(flag, context)
        
        elif flag.current_state == FeatureState.CONDITIONAL:
            return self._evaluate_conditions(flag, context)
        
        return False
    
    def _evaluate_percentage_rollout(self, flag: FeatureFlag, context: FeatureEvaluationContext) -> bool:
        """Evaluate percentage-based rollout."""
        if flag.rollout_percentage >= 100:
            return True
        
        if flag.rollout_percentage <= 0:
            return False
        
        # Use hash of context key for consistent rollout
        hash_key = context.get_hash_key()
        if not hash_key:
            # No context, use random
            import random
            return random.random() * 100 < flag.rollout_percentage
        
        # Use consistent hash
        import hashlib
        hash_value = int(hashlib.md5(hash_key.encode()).hexdigest(), 16)
        return (hash_value % 100) < flag.rollout_percentage
    
    def _evaluate_conditions(self, flag: FeatureFlag, context: FeatureEvaluationContext) -> bool:
        """Evaluate conditional feature flag."""
        conditions = flag.conditions
        
        # Environment conditions
        if "environments" in conditions:
            allowed_envs = conditions["environments"]
            if context.environment not in allowed_envs:
                return False
        
        # User-based conditions
        if "allowed_users" in conditions:
            allowed_users = conditions["allowed_users"]
            if not context.user_id or context.user_id not in allowed_users:
                return False
        
        # Metadata conditions
        for key, value in conditions.items():
            if key.startswith("metadata."):
                metadata_key = key[9:]  # Remove "metadata." prefix
                if context.metadata.get(metadata_key) != value:
                    return False
        
        return True
    
    def _get_flag_config_overrides(self, flag: FeatureFlag) -> Dict[str, Any]:
        """Get configuration overrides for a feature flag."""
        overrides = {}
        
        if flag.name == "grpc_monitoring_enabled":
            overrides.update({
                "enable_metrics": True,
                "grpc_prometheus_port": 9090,
            })
        
        elif flag.name == "grpc_health_check_enabled":
            overrides.update({
                "enable_health_check": True,
                "health_check_interval_seconds": 30,
            })
        
        elif flag.name == "grpc_circuit_breaker_enabled":
            overrides.update({
                "circuit_breaker_enabled": True,
                "circuit_breaker_threshold": 5,
                "circuit_breaker_recovery_timeout": 60,
            })
        
        elif flag.name == "grpc_retry_enabled":
            overrides.update({
                "retry_jitter": True,
                "max_attempts": 3,
            })
        
        elif flag.name == "grpc_compression_enabled":
            overrides.update({
                "compression_algorithm": "gzip",
            })
        
        elif flag.name == "grpc_tls_enabled":
            overrides.update({
                "secure": True,
            })
        
        elif flag.name == "grpc_reflection_enabled":
            overrides.update({
                "reflection_enabled": True,
            })
        
        elif flag.name == "grpc_timeout_adaptive":
            overrides.update({
                "timeout_adaptive": True,
                "timeout_deadline_propagation": True,
            })
        
        elif flag.name == "grpc_connection_pooling":
            overrides.update({
                "pool_size": 10,
                "max_pool_size": 50,
            })
        
        elif flag.name == "grpc_load_balancing":
            overrides.update({
                "load_balancing_policy": "round_robin",
            })
        
        elif flag.name == "grpc_distributed_tracing":
            overrides.update({
                "enable_tracing": True,
                "tracing_sampling_rate": 0.1,
            })
        
        return overrides
    
    async def _set_flag_state(self, flag_name: str, state: FeatureState, context: Optional[FeatureEvaluationContext] = None) -> bool:
        """Set feature flag state."""
        success = await self.registry.update_flag(
            flag_name,
            current_state=state,
            updated_at=time.time()
        )
        
        if success:
            await self._save_flags_to_storage()
            # Clear cache for this flag
            await self._clear_flag_cache(flag_name)
            _logger.info("feature_state_set", flag=flag_name, state=state.value)
        
        return success
    
    def _get_cache_key(self, flag_name: str, context: Optional[FeatureEvaluationContext]) -> str:
        """Get cache key for feature evaluation."""
        if context:
            return f"{flag_name}:{context.get_hash_key()}"
        return flag_name
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is valid."""
        if cache_key not in self._cache_timestamps:
            return False
        
        age = time.time() - self._cache_timestamps[cache_key]
        return age < self._cache_ttl
    
    async def _clear_flag_cache(self, flag_name: str):
        """Clear cache entries for a specific flag."""
        keys_to_remove = [key for key in self._evaluation_cache.keys() if key.startswith(f"{flag_name}:")]
        for key in keys_to_remove:
            self._evaluation_cache.pop(key, None)
            self._cache_timestamps.pop(key, None)
    
    async def _load_flags_from_storage(self):
        """Load feature flags from storage."""
        try:
            # This would load from storage - for now using defaults
            pass
        except Exception as exc:
            _logger.error("load_flags_from_storage_failed", error=str(exc))
    
    async def _save_flags_to_storage(self):
        """Save feature flags to storage."""
        try:
            # This would save to storage - for now using memory
            pass
        except Exception as exc:
            _logger.error("save_flags_to_storage_failed", error=str(exc))
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get feature toggle statistics."""
        flags = await self.registry.get_all_flags()
        
        stats = {
            "total_flags": len(flags),
            "enabled_flags": 0,
            "disabled_flags": 0,
            "percentage_flags": 0,
            "conditional_flags": 0,
            "cache_size": len(self._evaluation_cache),
            "flags": {}
        }
        
        for name, flag in flags.items():
            flag_stats = {
                "state": flag.current_state.value,
                "rollout_percentage": flag.rollout_percentage,
                "dependencies": flag.dependencies,
                "requires_restart": flag.requires_restart,
            }
            stats["flags"][name] = flag_stats
            
            # Count by state
            if flag.current_state == FeatureState.ENABLED:
                stats["enabled_flags"] += 1
            elif flag.current_state == FeatureState.DISABLED:
                stats["disabled_flags"] += 1
            elif flag.current_state == FeatureState.PERCENTAGE:
                stats["percentage_flags"] += 1
            elif flag.current_state == FeatureState.CONDITIONAL:
                stats["conditional_flags"] += 1
        
        return stats


# Global feature toggles instance
_global_feature_toggles: Optional[FeatureToggles] = None


async def get_feature_toggles() -> FeatureToggles:
    """Get global feature toggles instance."""
    global _global_feature_toggles
    if _global_feature_toggles is None:
        _global_feature_toggles = FeatureToggles()
        await _global_feature_toggles.initialize()
    return _global_feature_toggles


def set_feature_toggles(toggles: FeatureToggles) -> None:
    """Set global feature toggles instance."""
    global _global_feature_toggles
    _global_feature_toggles = toggles
