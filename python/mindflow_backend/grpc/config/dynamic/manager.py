"""Dynamic configuration manager for gRPC services.

Provides hot reload, atomic updates, versioning, and subscriber
notifications for configuration changes without application restart.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from mindflow_backend.grpc.config.config import GrpcConfig
from mindflow_backend.grpc.config.dynamic.storage import ConfigStorage, MemoryConfigStorage
from mindflow_backend.grpc.config.dynamic.validator import ConfigValidator, ValidationResult
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class ConfigChangeType(Enum):
    """Types of configuration changes."""
    FULL_RELOAD = "full_reload"
    PARTIAL_UPDATE = "partial_update"
    FEATURE_TOGGLE = "feature_toggle"
    ROLLBACK = "rollback"


@dataclass
class ConfigSnapshot:
    """Snapshot of configuration at a point in time."""
    config: GrpcConfig
    timestamp: float
    version: str
    change_type: ConfigChangeType
    description: str = ""
    changed_fields: set[str] = field(default_factory=set)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert snapshot to dictionary."""
        return {
            "version": self.version,
            "timestamp": self.timestamp,
            "change_type": self.change_type.value,
            "description": self.description,
            "changed_fields": list(self.changed_fields),
            "config": self.config.dict(),
        }


@dataclass
class ConfigChangeEvent:
    """Event representing a configuration change."""
    old_config: GrpcConfig | None
    new_config: GrpcConfig
    snapshot: ConfigSnapshot
    validation_result: ValidationResult


class DynamicConfigManager:
    """Manages dynamic gRPC configuration with hot reload capabilities."""
    
    def __init__(self, storage_backend: ConfigStorage | None = None):
        self.storage = storage_backend or MemoryConfigStorage()
        self.validator = ConfigValidator()
        
        # Current configuration state
        self.current_config: GrpcConfig | None = None
        self.current_version: str = "initial"
        self.last_updated: float = time.time()
        
        # Configuration history
        self.config_history: list[ConfigSnapshot] = []
        self.max_history_size: int = 100
        
        # Subscribers for change notifications
        self._subscribers: list[Callable[[ConfigChangeEvent], None]] = []
        
        # Thread safety
        self._lock = asyncio.Lock()
        self._update_in_progress: bool = False
        
        _logger.info("dynamic_config_manager_initialized", storage_type=type(self.storage).__name__)
    
    async def initialize(self, initial_config: GrpcConfig | None = None) -> bool:
        """Initialize the configuration manager."""
        async with self._lock:
            try:
                if initial_config:
                    # Use provided initial configuration
                    self.current_config = initial_config
                    validation_result = await self.validator.validate_config(initial_config)
                else:
                    # Load configuration from storage
                    self.current_config = await self.storage.load_config()
                    validation_result = await self.validator.validate_config(self.current_config)
                
                if not validation_result.is_valid:
                    _logger.error(
                        "initial_config_validation_failed",
                        errors=[e.message for e in validation_result.errors]
                    )
                    return False
                
                # Create initial snapshot
                initial_snapshot = ConfigSnapshot(
                    config=self.current_config,
                    timestamp=time.time(),
                    version=self.current_version,
                    change_type=ConfigChangeType.FULL_RELOAD,
                    description="Initial configuration"
                )
                self.config_history.append(initial_snapshot)
                
                _logger.info(
                    "dynamic_config_manager_initialized_successfully",
                    version=self.current_version,
                    config_hash=self._get_config_hash(self.current_config)
                )
                
                return True
                
            except Exception as exc:
                _logger.error("config_manager_initialization_failed", error=str(exc))
                return False
    
    async def reload_configuration(self) -> bool:
        """Reload configuration from storage with validation."""
        async with self._lock:
            if self._update_in_progress:
                _logger.warning("config_reload_already_in_progress")
                return False
            
            self._update_in_progress = True
            
            try:
                _logger.info("starting_config_reload")
                
                # Load new configuration
                new_config = await self.storage.load_config()
                
                # Validate new configuration
                validation_result = await self.validator.validate_config(new_config)
                
                if not validation_result.is_valid:
                    _logger.error(
                        "config_validation_failed",
                        errors=[e.message for e in validation_result.errors]
                    )
                    return False
                
                # Log warnings
                if validation_result.warnings:
                    _logger.warning(
                        "config_validation_warnings",
                        warnings=[e.message for e in validation_result.warnings]
                    )
                
                # Apply configuration update
                success = await self._apply_configuration_update(
                    new_config=new_config,
                    change_type=ConfigChangeType.FULL_RELOAD,
                    description="Configuration reload",
                    validation_result=validation_result
                )
                
                if success:
                    _logger.info(
                        "config_reload_completed",
                        version=self.current_version,
                        duration=time.time() - self.last_updated
                    )
                
                return success
                
            except Exception as exc:
                _logger.error("config_reload_failed", error=str(exc))
                return False
            finally:
                self._update_in_progress = False
    
    async def update_config(self, updates: dict[str, Any], validate_only: bool = False) -> bool:
        """Update specific configuration fields."""
        async with self._lock:
            if self._update_in_progress:
                _logger.warning("config_update_already_in_progress")
                return False
            
            self._update_in_progress = True
            
            try:
                if not self.current_config:
                    _logger.error("no_current_config_for_update")
                    return False
                
                # Validate partial updates
                validation_result = await self.validator.validate_partial_update(updates)
                
                if not validation_result.is_valid:
                    _logger.error(
                        "partial_update_validation_failed",
                        errors=[e.message for e in validation_result.errors]
                    )
                    return False
                
                if validate_only:
                    _logger.info("config_validation_only", updates=list(updates.keys()))
                    return True
                
                # Create new configuration with updates
                current_dict = self.current_config.dict()
                updated_dict = {**current_dict, **updates}
                new_config = GrpcConfig(**updated_dict)
                
                # Validate complete configuration
                full_validation = await self.validator.validate_config(new_config)
                if not full_validation.is_valid:
                    _logger.error(
                        "full_config_validation_failed_after_update",
                        errors=[e.message for e in full_validation.errors]
                    )
                    return False
                
                # Apply configuration update
                success = await self._apply_configuration_update(
                    new_config=new_config,
                    change_type=ConfigChangeType.PARTIAL_UPDATE,
                    description=f"Partial update: {', '.join(updates.keys())}",
                    validation_result=full_validation,
                    changed_fields=set(updates.keys())
                )
                
                if success:
                    _logger.info(
                        "config_update_completed",
                        updates=list(updates.keys()),
                        version=self.current_version
                    )
                
                return success
                
            except Exception as exc:
                _logger.error("config_update_failed", error=str(exc), updates=updates)
                return False
            finally:
                self._update_in_progress = False
    
    async def rollback_config(self, target_version: str) -> bool:
        """Rollback configuration to a specific version."""
        async with self._lock:
            if self._update_in_progress:
                _logger.warning("config_rollback_already_in_progress")
                return False
            
            # Find target snapshot
            target_snapshot = None
            for snapshot in self.config_history:
                if snapshot.version == target_version:
                    target_snapshot = snapshot
                    break
            
            if not target_snapshot:
                _logger.error("target_version_not_found", version=target_version)
                return False
            
            self._update_in_progress = True
            
            try:
                # Validate rollback configuration
                validation_result = await self.validator.validate_config(target_snapshot.config)
                
                if not validation_result.is_valid:
                    _logger.error(
                        "rollback_config_validation_failed",
                        errors=[e.message for e in validation_result.errors]
                    )
                    return False
                
                # Apply rollback
                success = await self._apply_configuration_update(
                    new_config=target_snapshot.config,
                    change_type=ConfigChangeType.ROLLBACK,
                    description=f"Rollback to version {target_version}",
                    validation_result=validation_result
                )
                
                if success:
                    _logger.info(
                        "config_rollback_completed",
                        target_version=target_version,
                        current_version=self.current_version
                    )
                
                return success
                
            except Exception as exc:
                _logger.error("config_rollback_failed", error=str(exc), target_version=target_version)
                return False
            finally:
                self._update_in_progress = False
    
    async def get_current_config(self) -> GrpcConfig | None:
        """Get current configuration."""
        async with self._lock:
            return self.current_config
    
    async def get_config_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get configuration history."""
        async with self._lock:
            history = self.config_history[-limit:] if limit > 0 else self.config_history
            return [snapshot.to_dict() for snapshot in reversed(history)]
    
    async def get_config_snapshot(self, version: str) -> dict[str, Any] | None:
        """Get specific configuration snapshot."""
        async with self._lock:
            for snapshot in self.config_history:
                if snapshot.version == version:
                    return snapshot.to_dict()
            return None
    
    def subscribe_to_changes(self, callback: Callable[[ConfigChangeEvent], None]) -> str:
        """Subscribe to configuration changes."""
        subscriber_id = str(uuid.uuid4())
        
        # Wrap callback to handle exceptions
        async def safe_callback(event: ConfigChangeEvent):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as exc:
                _logger.error("config_subscriber_callback_error", subscriber_id=subscriber_id, error=str(exc))
        
        # Store subscriber info
        subscriber_info = {
            "id": subscriber_id,
            "callback": safe_callback,
            "original_callback": callback
        }
        
        if not hasattr(self, '_subscriber_info'):
            self._subscriber_info = {}
        self._subscriber_info[subscriber_id] = subscriber_info
        
        _logger.info("config_subscriber_added", subscriber_id=subscriber_id)
        return subscriber_id
    
    def unsubscribe_from_changes(self, subscriber_id: str) -> bool:
        """Unsubscribe from configuration changes."""
        if hasattr(self, '_subscriber_info') and subscriber_id in self._subscriber_info:
            del self._subscriber_info[subscriber_id]
            _logger.info("config_subscriber_removed", subscriber_id=subscriber_id)
            return True
        return False
    
    async def _apply_configuration_update(
        self,
        new_config: GrpcConfig,
        change_type: ConfigChangeType,
        description: str,
        validation_result: ValidationResult,
        changed_fields: set[str] | None = None
    ) -> bool:
        """Apply configuration update with notifications."""
        try:
            old_config = self.current_config
            
            # Create new version
            new_version = self._generate_version()
            
            # Create snapshot
            snapshot = ConfigSnapshot(
                config=new_config,
                timestamp=time.time(),
                version=new_version,
                change_type=change_type,
                description=description,
                changed_fields=changed_fields or set()
            )
            
            # Update current state
            self.current_config = new_config
            self.current_version = new_version
            self.last_updated = time.time()
            
            # Add to history
            self.config_history.append(snapshot)
            
            # Trim history if needed
            if len(self.config_history) > self.max_history_size:
                self.config_history = self.config_history[-self.max_history_size:]
            
            # Save to storage
            await self.storage.save_config(new_config, new_version)
            
            # Create change event
            change_event = ConfigChangeEvent(
                old_config=old_config,
                new_config=new_config,
                snapshot=snapshot,
                validation_result=validation_result
            )
            
            # Notify subscribers
            await self._notify_subscribers(change_event)
            
            return True
            
        except Exception as exc:
            _logger.error("apply_configuration_update_failed", error=str(exc))
            return False
    
    async def _notify_subscribers(self, event: ConfigChangeEvent):
        """Notify all subscribers of configuration changes."""
        if not hasattr(self, '_subscriber_info'):
            return
        
        notifications = []
        for subscriber_id, subscriber_info in self._subscriber_info.items():
            notifications.append(subscriber_info["callback"](event))
        
        if notifications:
            try:
                await asyncio.gather(*notifications, return_exceptions=True)
            except Exception as exc:
                _logger.error("config_subscriber_notification_error", error=str(exc))
    
    def _generate_version(self) -> str:
        """Generate a unique version identifier."""
        timestamp = int(time.time() * 1000)
        random_suffix = uuid.uuid4().hex[:8]
        return f"v{timestamp}-{random_suffix}"
    
    def _get_config_hash(self, config: GrpcConfig) -> str:
        """Generate hash of configuration for comparison."""
        import hashlib
        config_str = str(sorted(config.dict().items()))
        return hashlib.md5(config_str.encode()).hexdigest()[:8]
    
    async def get_statistics(self) -> dict[str, Any]:
        """Get configuration manager statistics."""
        async with self._lock:
            return {
                "current_version": self.current_version,
                "last_updated": self.last_updated,
                "history_size": len(self.config_history),
                "subscriber_count": len(getattr(self, '_subscriber_info', {})),
                "update_in_progress": self._update_in_progress,
                "storage_type": type(self.storage).__name__,
                "config_hash": self._get_config_hash(self.current_config) if self.current_config else None,
            }


# Global configuration manager instance
_global_config_manager: DynamicConfigManager | None = None


async def get_config_manager() -> DynamicConfigManager:
    """Get global configuration manager instance."""
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = DynamicConfigManager()
        await _global_config_manager.initialize()
    return _global_config_manager


def set_config_manager(manager: DynamicConfigManager) -> None:
    """Set global configuration manager instance."""
    global _global_config_manager
    _global_config_manager = manager
