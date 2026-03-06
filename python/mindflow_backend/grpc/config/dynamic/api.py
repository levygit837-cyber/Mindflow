"""Configuration API for dynamic gRPC configuration management.

Provides REST API endpoints for managing gRPC configuration,
feature flags, and monitoring configuration changes.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from mindflow_backend.grpc.config.dynamic.manager import DynamicConfigManager, get_config_manager
from mindflow_backend.grpc.config.dynamic.validator import ValidationResult
from mindflow_backend.grpc.config.features import FeatureToggles, get_feature_toggles, FeatureEvaluationContext
from mindflow_backend.grpc.config.profiles import EnvironmentLoader, get_environment_loader
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

# API Router
router = APIRouter(prefix="/api/v1/config", tags=["configuration"])


# Pydantic models for API
class ConfigUpdateRequest(BaseModel):
    """Request model for configuration updates."""
    updates: Dict[str, Any] = Field(..., description="Configuration updates")
    validate_only: bool = Field(default=False, description="Only validate, don't apply")
    description: Optional[str] = Field(default=None, description="Update description")


class ConfigResponse(BaseModel):
    """Response model for configuration data."""
    config: Dict[str, Any]
    profile: Optional[str] = None
    version: str
    last_updated: float
    auto_reload: bool
    validation_result: Optional[Dict[str, Any]] = None


class ConfigHistoryResponse(BaseModel):
    """Response model for configuration history."""
    history: List[Dict[str, Any]]
    total_count: int


class FeatureFlagRequest(BaseModel):
    """Request model for feature flag updates."""
    enabled: Optional[bool] = None
    rollout_percentage: Optional[float] = Field(None, ge=0, le=100)
    description: Optional[str] = None


class FeatureFlagResponse(BaseModel):
    """Response model for feature flag data."""
    name: str
    description: str
    state: str
    rollout_percentage: float
    dependencies: List[str]
    requires_restart: bool
    metadata: Dict[str, Any]


class ProfileResponse(BaseModel):
    """Response model for environment profile."""
    name: str
    description: str
    parent_profile: Optional[str]
    overrides: Dict[str, Any]
    inherited_overrides: Dict[str, Any]


class ValidationRequest(BaseModel):
    """Request model for configuration validation."""
    config: Dict[str, Any]
    profile: Optional[str] = None


class ValidationResponse(BaseModel):
    """Response model for validation results."""
    is_valid: bool
    errors: List[Dict[str, str]]
    warnings: List[Dict[str, str]]
    info: List[Dict[str, str]]


# Dependency injection
async def get_config_manager_dep() -> DynamicConfigManager:
    """Get configuration manager dependency."""
    return await get_config_manager()


async def get_feature_toggles_dep() -> FeatureToggles:
    """Get feature toggles dependency."""
    return await get_feature_toggles()


async def get_env_loader_dep() -> EnvironmentLoader:
    """Get environment loader dependency."""
    return get_environment_loader()


# Configuration endpoints
@router.get("/", response_model=ConfigResponse)
async def get_current_config(
    include_sensitive: bool = Query(default=False, description="Include sensitive configuration"),
    manager: DynamicConfigManager = Depends(get_config_manager_dep)
) -> ConfigResponse:
    """Get current gRPC configuration."""
    try:
        config = await manager.get_current_config()
        if not config:
            raise HTTPException(status_code=404, detail="No configuration available")
        
        config_dict = config.dict()
        
        # Filter sensitive fields if requested
        if not include_sensitive:
            config_dict = _filter_sensitive_fields(config_dict)
        
        stats = await manager.get_statistics()
        
        return ConfigResponse(
            config=config_dict,
            version=stats["current_version"],
            last_updated=stats["last_updated"],
            auto_reload=True,  # TODO: Get from actual config
        )
        
    except Exception as exc:
        _logger.error("get_current_config_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to get configuration")


@router.put("/", response_model=Dict[str, Any])
async def update_config(
    request: ConfigUpdateRequest,
    manager: DynamicConfigManager = Depends(get_config_manager_dep)
) -> Dict[str, Any]:
    """Update gRPC configuration."""
    try:
        if request.validate_only:
            # Only validate updates
            validation_result = await manager.validator.validate_partial_update(request.updates)
            
            return {
                "valid": validation_result.is_valid,
                "errors": [{"field": e.field, "message": e.message} for e in validation_result.errors],
                "warnings": [{"field": e.field, "message": e.message} for e in validation_result.warnings],
                "info": [{"field": e.field, "message": e.message} for e in validation_result.info],
            }
        
        # Apply updates
        success = await manager.update_config(request.updates)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to update configuration")
        
        stats = await manager.get_statistics()
        
        return {
            "success": True,
            "version": stats["current_version"],
            "updated_fields": list(request.updates.keys()),
            "description": request.description or "Configuration update",
        }
        
    except Exception as exc:
        _logger.error("update_config_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to update configuration")


@router.post("/reload", response_model=Dict[str, Any])
async def reload_config(
    manager: DynamicConfigManager = Depends(get_config_manager_dep)
) -> Dict[str, Any]:
    """Reload configuration from storage."""
    try:
        success = await manager.reload_configuration()
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to reload configuration")
        
        stats = await manager.get_statistics()
        
        return {
            "success": True,
            "version": stats["current_version"],
            "timestamp": stats["last_updated"],
        }
        
    except Exception as exc:
        _logger.error("reload_config_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to reload configuration")


@router.get("/history", response_model=ConfigHistoryResponse)
async def get_config_history(
    limit: int = Query(default=10, ge=1, le=100, description="Number of history entries to return"),
    manager: DynamicConfigManager = Depends(get_config_manager_dep)
) -> ConfigHistoryResponse:
    """Get configuration history."""
    try:
        history = await manager.get_config_history(limit)
        
        return ConfigHistoryResponse(
            history=history,
            total_count=len(history)
        )
        
    except Exception as exc:
        _logger.error("get_config_history_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to get configuration history")


@router.get("/history/{version}", response_model=Dict[str, Any])
async def get_config_snapshot(
    version: str,
    manager: DynamicConfigManager = Depends(get_config_manager_dep)
) -> Dict[str, Any]:
    """Get specific configuration snapshot."""
    try:
        snapshot = await manager.get_config_snapshot(version)
        
        if not snapshot:
            raise HTTPException(status_code=404, detail="Configuration version not found")
        
        return snapshot
        
    except HTTPException:
        raise
    except Exception as exc:
        _logger.error("get_config_snapshot_failed", version=version, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to get configuration snapshot")


@router.post("/rollback/{version}", response_model=Dict[str, Any])
async def rollback_config(
    version: str,
    manager: DynamicConfigManager = Depends(get_config_manager_dep)
) -> Dict[str, Any]:
    """Rollback configuration to specific version."""
    try:
        success = await manager.rollback_config(version)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to rollback configuration")
        
        stats = await manager.get_statistics()
        
        return {
            "success": True,
            "target_version": version,
            "current_version": stats["current_version"],
            "timestamp": stats["last_updated"],
        }
        
    except Exception as exc:
        _logger.error("rollback_config_failed", version=version, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to rollback configuration")


# Validation endpoints
@router.post("/validate", response_model=ValidationResponse)
async def validate_config(
    request: ValidationRequest,
    manager: DynamicConfigManager = Depends(get_config_manager_dep),
    env_loader: EnvironmentLoader = Depends(get_env_loader_dep)
) -> ValidationResponse:
    """Validate configuration without applying it."""
    try:
        # Apply profile if specified
        config_dict = request.config.copy()
        if request.profile:
            base_config = manager.current_config or await manager.storage.load_config()
            profile_config = await env_loader.load_profile_config(request.profile, base_config)
            config_dict.update(profile_config.dict())
        
        # Create config object
        from mindflow_backend.grpc.config import GrpcConfig
        config = GrpcConfig(**config_dict)
        
        # Validate configuration
        validation_result = await manager.validator.validate_config(config)
        
        return ValidationResponse(
            is_valid=validation_result.is_valid,
            errors=[{"field": e.field, "message": e.message} for e in validation_result.errors],
            warnings=[{"field": e.field, "message": e.message} for e in validation_result.warnings],
            info=[{"field": e.field, "message": e.message} for e in validation_result.info],
        )
        
    except Exception as exc:
        _logger.error("validate_config_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to validate configuration")


# Feature flags endpoints
@router.get("/features", response_model=List[FeatureFlagResponse])
async def get_feature_flags(
    toggles: FeatureToggles = Depends(get_feature_toggles_dep)
) -> List[FeatureFlagResponse]:
    """Get all feature flags."""
    try:
        flags = await toggles.registry.get_all_flags()
        
        return [
            FeatureFlagResponse(
                name=flag.name,
                description=flag.description,
                state=flag.current_state.value,
                rollout_percentage=flag.rollout_percentage,
                dependencies=flag.dependencies,
                requires_restart=flag.requires_restart,
                metadata=flag.metadata,
            )
            for flag in flags.values()
        ]
        
    except Exception as exc:
        _logger.error("get_feature_flags_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to get feature flags")


@router.get("/features/{flag_name}", response_model=FeatureFlagResponse)
async def get_feature_flag(
    flag_name: str,
    toggles: FeatureToggles = Depends(get_feature_toggles_dep)
) -> FeatureFlagResponse:
    """Get specific feature flag."""
    try:
        flag = await toggles.registry.get_flag(flag_name)
        
        if not flag:
            raise HTTPException(status_code=404, detail="Feature flag not found")
        
        return FeatureFlagResponse(
            name=flag.name,
            description=flag.description,
            state=flag.current_state.value,
            rollout_percentage=flag.rollout_percentage,
            dependencies=flag.dependencies,
            requires_restart=flag.requires_restart,
            metadata=flag.metadata,
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        _logger.error("get_feature_flag_failed", flag=flag_name, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to get feature flag")


@router.put("/features/{flag_name}", response_model=Dict[str, Any])
async def update_feature_flag(
    flag_name: str,
    request: FeatureFlagRequest,
    toggles: FeatureToggles = Depends(get_feature_toggles_dep)
) -> Dict[str, Any]:
    """Update feature flag."""
    try:
        updates = {}
        
        if request.enabled is not None:
            from mindflow_backend.grpc.config.features import FeatureState
            updates["current_state"] = FeatureState.ENABLED if request.enabled else FeatureState.DISABLED
        
        if request.rollout_percentage is not None:
            success = await toggles.set_percentage_rollout(flag_name, request.rollout_percentage)
            if not success:
                raise HTTPException(status_code=400, detail="Failed to set percentage rollout")
        
        if request.description is not None:
            updates["description"] = request.description
        
        if updates:
            success = await toggles.registry.update_flag(flag_name, **updates)
            if not success:
                raise HTTPException(status_code=400, detail="Failed to update feature flag")
        
        flag = await toggles.registry.get_flag(flag_name)
        if not flag:
            raise HTTPException(status_code=404, detail="Feature flag not found")
        
        return {
            "success": True,
            "flag": flag.to_dict(),
        }
        
    except HTTPException:
        raise
    except Exception as exc:
        _logger.error("update_feature_flag_failed", flag=flag_name, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to update feature flag")


@router.get("/features/{flag_name}/enabled")
async def is_feature_enabled(
    flag_name: str,
    user_id: Optional[str] = Query(None, description="User ID for evaluation context"),
    session_id: Optional[str] = Query(None, description="Session ID for evaluation context"),
    toggles: FeatureToggles = Depends(get_feature_toggles_dep)
) -> Dict[str, Any]:
    """Check if feature flag is enabled."""
    try:
        context = FeatureEvaluationContext(
            user_id=user_id,
            session_id=session_id,
        )
        
        enabled = await toggles.is_enabled(flag_name, context)
        
        return {
            "flag": flag_name,
            "enabled": enabled,
            "context": {
                "user_id": user_id,
                "session_id": session_id,
            }
        }
        
    except Exception as exc:
        _logger.error("is_feature_enabled_failed", flag=flag_name, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to check feature flag")


# Environment profiles endpoints
@router.get("/profiles", response_model=List[ProfileResponse])
async def get_environment_profiles(
    env_loader: EnvironmentLoader = Depends(get_env_loader_dep)
) -> List[ProfileResponse]:
    """Get available environment profiles."""
    try:
        profiles = env_loader.list_profiles()
        
        return [
            ProfileResponse(
                name=profile["name"],
                description=profile["description"],
                parent_profile=profile.get("parent_profile"),
                overrides=profile["overrides"],
                inherited_overrides=profile["inherited_overrides"],
            )
            for profile in profiles
        ]
        
    except Exception as exc:
        _logger.error("get_environment_profiles_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to get environment profiles")


@router.get("/profiles/{profile_name}", response_model=ProfileResponse)
async def get_environment_profile(
    profile_name: str,
    env_loader: EnvironmentLoader = Depends(get_env_loader_dep)
) -> ProfileResponse:
    """Get specific environment profile."""
    try:
        profile_info = env_loader.get_profile_info(profile_name)
        
        if not profile_info:
            raise HTTPException(status_code=404, detail="Environment profile not found")
        
        return ProfileResponse(
            name=profile_info["name"],
            description=profile_info["description"],
            parent_profile=profile_info.get("parent_profile"),
            overrides=profile_info["overrides"],
            inherited_overrides=profile_info["inherited_overrides"],
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        _logger.error("get_environment_profile_failed", profile=profile_name, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to get environment profile")


@router.post("/profiles/{profile_name}/apply", response_model=Dict[str, Any])
async def apply_environment_profile(
    profile_name: str,
    manager: DynamicConfigManager = Depends(get_config_manager_dep),
    env_loader: EnvironmentLoader = Depends(get_env_loader_dep)
) -> Dict[str, Any]:
    """Apply environment profile to current configuration."""
    try:
        current_config = await manager.get_current_config()
        if not current_config:
            raise HTTPException(status_code=404, detail="No current configuration available")
        
        # Apply profile
        updated_config = await env_loader.load_profile_config(profile_name, current_config)
        
        # Update configuration
        config_dict = updated_config.dict()
        current_dict = current_config.dict()
        updates = {k: v for k, v in config_dict.items() if k in current_dict and current_dict[k] != v}
        
        success = await manager.update_config(updates)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to apply profile")
        
        stats = await manager.get_statistics()
        
        return {
            "success": True,
            "profile": profile_name,
            "version": stats["current_version"],
            "updated_fields": list(updates.keys()),
        }
        
    except HTTPException:
        raise
    except Exception as exc:
        _logger.error("apply_environment_profile_failed", profile=profile_name, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to apply environment profile")


# Statistics endpoint
@router.get("/stats", response_model=Dict[str, Any])
async def get_config_statistics(
    manager: DynamicConfigManager = Depends(get_config_manager_dep),
    toggles: FeatureToggles = Depends(get_feature_toggles_dep)
) -> Dict[str, Any]:
    """Get configuration management statistics."""
    try:
        config_stats = await manager.get_statistics()
        feature_stats = await toggles.get_statistics()
        
        return {
            "config_manager": config_stats,
            "feature_toggles": feature_stats,
        }
        
    except Exception as exc:
        _logger.error("get_config_statistics_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to get configuration statistics")


# Utility functions
def _filter_sensitive_fields(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Filter sensitive configuration fields."""
    sensitive_fields = {
        "tls_cert_path",
        "tls_key_path",
        "tls_ca_path",
        "database_url",
        "api_key",
        "secret",
        "password",
        "token",
    }
    
    filtered = config_dict.copy()
    
    for field in sensitive_fields:
        if field in filtered:
            filtered[field] = "***REDACTED***"
    
    return filtered


# Health check endpoint
@router.get("/health", response_model=Dict[str, Any])
async def config_health_check(
    manager: DynamicConfigManager = Depends(get_config_manager_dep),
    toggles: FeatureToggles = Depends(get_feature_toggles_dep)
) -> Dict[str, Any]:
    """Health check for configuration management."""
    try:
        config_stats = await manager.get_statistics()
        feature_stats = await toggles.get_statistics()
        
        # Basic health checks
        issues = []
        
        if not config_stats.get("current_version"):
            issues.append("No configuration version available")
        
        if feature_stats.get("total_flags", 0) == 0:
            issues.append("No feature flags available")
        
        return {
            "status": "healthy" if not issues else "unhealthy",
            "issues": issues,
            "config_manager": {
                "initialized": bool(config_stats.get("current_version")),
                "version": config_stats.get("current_version"),
                "last_updated": config_stats.get("last_updated"),
            },
            "feature_toggles": {
                "initialized": feature_stats.get("total_flags", 0) > 0,
                "total_flags": feature_stats.get("total_flags", 0),
                "enabled_flags": feature_stats.get("enabled_flags", 0),
            },
        }
        
    except Exception as exc:
        _logger.error("config_health_check_failed", error=str(exc))
        return {
            "status": "error",
            "error": str(exc),
        }
