"""Dynamic configuration API endpoints.

Provides REST API for managing gRPC configuration dynamically
without application restarts, including feature flags, profiles,
and configuration updates.
"""

from __future__ import annotations

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from mindflow_backend.grpc.config import GrpcConfig
from mindflow_backend.grpc.config.dynamic.manager import get_config_manager
from mindflow_backend.grpc.config.profiles import get_environment_loader
from mindflow_backend.grpc.config.features import get_feature_toggles
from mindflow_backend.infra.logging import get_logger

router = APIRouter(prefix="/config", tags=["Configuration"])
_logger = get_logger(__name__)


class ConfigurationUpdateRequest(BaseModel):
    """Request model for configuration updates."""
    updates: Dict[str, Any] = Field(description="Configuration updates to apply")
    description: str = Field(default="", description="Description of the change")


class ConfigurationResponse(BaseModel):
    """Response model for configuration data."""
    config: Dict[str, Any] = Field(description="Current configuration")
    version: str = Field(description="Configuration version")
    timestamp: float = Field(description="Last update timestamp")
    profile: str = Field(description="Active profile")


class FeatureFlagRequest(BaseModel):
    """Request model for feature flag operations."""
    enabled: bool = Field(description="Whether to enable the feature")
    rollout_percentage: float = Field(default=100.0, description="Rollout percentage (0-100)")


class ProfileApplyRequest(BaseModel):
    """Request model for profile application."""
    profile_name: str = Field(description="Profile name to apply")
    force: bool = Field(default=False, description="Force application even if validation fails")


def get_config_manager_dependency():
    """Dependency to get configuration manager."""
    from fastapi import Request
    def dependency(request: Request):
        if not hasattr(request.app.state, 'config_manager'):
            raise HTTPException(status_code=503, detail="Configuration manager not available")
        return request.app.state.config_manager
    return dependency


@router.get("/", response_model=ConfigurationResponse)
async def get_current_configuration(
    config_manager=Depends(get_config_manager_dependency())
) -> ConfigurationResponse:
    """Get current gRPC configuration."""
    try:
        current_config = await config_manager.get_current_config()
        if not current_config:
            raise HTTPException(status_code=404, detail="No configuration found")
        
        stats = await config_manager.get_statistics()
        
        return ConfigurationResponse(
            config=current_config.get_effective_config(),
            version=stats.get('current_version', 'unknown'),
            timestamp=stats.get('last_update_timestamp', 0.0),
            profile=current_config.profile or 'default'
        )
    except Exception as exc:
        _logger.error("get_config_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Failed to get configuration: {str(exc)}")


@router.put("/")
async def update_configuration(
    request: ConfigurationUpdateRequest,
    config_manager=Depends(get_config_manager_dependency())
) -> Dict[str, Any]:
    """Update gRPC configuration dynamically."""
    try:
        # Validate updates
        validation_result = await config_manager.validator.validate_partial_update(request.updates)
        if not validation_result.is_valid:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Validation failed",
                    "errors": [
                        {"field": error.field, "message": error.message}
                        for error in validation_result.errors
                    ]
                }
            )
        
        # Apply updates
        success = await config_manager.update_config(
            request.updates,
            description=request.description or "Manual configuration update"
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to apply configuration updates")
        
        # Get updated configuration
        updated_config = await config_manager.get_current_config()
        
        return {
            "message": "Configuration updated successfully",
            "version": updated_config.version if hasattr(updated_config, 'version') else 'unknown',
            "timestamp": updated_config.timestamp if hasattr(updated_config, 'timestamp') else 0.0,
            "applied_updates": list(request.updates.keys())
        }
        
    except HTTPException:
        raise
    except Exception as exc:
        _logger.error("update_config_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {str(exc)}")


@router.get("/history")
async def get_configuration_history(
    limit: int = Query(default=50, ge=1, le=1000),
    config_manager=Depends(get_config_manager_dependency())
) -> Dict[str, Any]:
    """Get configuration change history."""
    try:
        history = await config_manager.get_config_history(limit=limit)
        
        return {
            "history": [
                {
                    "version": snapshot['version'],
                    "timestamp": snapshot['timestamp'],
                    "change_type": snapshot['change_type'],
                    "description": snapshot['description'],
                    "changed_fields": snapshot['changed_fields']
                }
                for snapshot in history
            ],
            "total_count": len(history)
        }
        
    except Exception as exc:
        _logger.error("get_config_history_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(exc)}")


@router.post("/reload")
async def reload_configuration(
    config_manager=Depends(get_config_manager_dependency())
) -> Dict[str, Any]:
    """Trigger configuration reload from storage."""
    try:
        success = await config_manager.reload_from_storage()
        
        return {
            "message": "Configuration reload triggered",
            "success": success,
            "timestamp": config_manager.get_current_timestamp()
        }
        
    except Exception as exc:
        _logger.error("reload_config_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Failed to reload configuration: {str(exc)}")


@router.post("/rollback/{version}")
async def rollback_configuration(
    version: str,
    config_manager=Depends(get_config_manager_dependency())
) -> Dict[str, Any]:
    """Rollback configuration to a specific version."""
    try:
        success = await config_manager.rollback_to_version(version)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Version {version} not found")
        
        current_config = await config_manager.get_current_config()
        
        return {
            "message": f"Configuration rolled back to version {version}",
            "current_version": current_config.version if hasattr(current_config, 'version') else 'unknown',
            "timestamp": current_config.timestamp if hasattr(current_config, 'timestamp') else 0.0
        }
        
    except HTTPException:
        raise
    except Exception as exc:
        _logger.error("rollback_config_failed", error=str(exc), version=version)
        raise HTTPException(status_code=500, detail=f"Failed to rollback: {str(exc)}")


# Feature Flags Endpoints

@router.get("/features", tags=["Feature Flags"])
async def get_feature_flags(
    config_manager=Depends(get_config_manager_dependency())
) -> Dict[str, Any]:
    """Get all feature flags and their states."""
    try:
        feature_toggles = await get_feature_toggles()
        flags = await feature_toggles.registry.get_all_flags()
        
        return {
            "flags": {
                name: {
                    "enabled": flag.current_state.value,
                    "description": flag.description,
                    "rollout_percentage": getattr(flag, 'rollout_percentage', 100.0)
                }
                for name, flag in flags.items()
            }
        }
        
    except Exception as exc:
        _logger.error("get_feature_flags_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Failed to get feature flags: {str(exc)}")


@router.put("/features/{flag_name}", tags=["Feature Flags"])
async def update_feature_flag(
    flag_name: str,
    request: FeatureFlagRequest,
    config_manager=Depends(get_config_manager_dependency())
) -> Dict[str, Any]:
    """Update a specific feature flag."""
    try:
        feature_toggles = await get_feature_toggles()
        
        if request.enabled:
            success = await feature_toggles.enable_flag(flag_name)
            if request.rollout_percentage < 100.0:
                await feature_toggles.set_percentage_rollout(flag_name, request.rollout_percentage)
        else:
            success = await feature_toggles.disable_flag(flag_name)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Feature flag {flag_name} not found")
        
        return {
            "message": f"Feature flag {flag_name} updated successfully",
            "enabled": request.enabled,
            "rollout_percentage": request.rollout_percentage
        }
        
    except HTTPException:
        raise
    except Exception as exc:
        _logger.error("update_feature_flag_failed", error=str(exc), flag=flag_name)
        raise HTTPException(status_code=500, detail=f"Failed to update feature flag: {str(exc)}")


@router.get("/features/{flag_name}/enabled", tags=["Feature Flags"])
async def check_feature_flag(
    flag_name: str,
    config_manager=Depends(get_config_manager_dependency())
) -> Dict[str, Any]:
    """Check if a feature flag is enabled for the current context."""
    try:
        feature_toggles = await get_feature_toggles()
        from mindflow_backend.grpc.config.features import FeatureEvaluationContext
        
        context = FeatureEvaluationContext(
            user_id="api-check",
            session_id="api-session",
            environment="api"
        )
        
        enabled = await feature_toggles.is_enabled(flag_name, context)
        
        return {
            "flag": flag_name,
            "enabled": enabled,
            "context": {
                "user_id": context.user_id,
                "session_id": context.session_id,
                "environment": context.environment
            }
        }
        
    except Exception as exc:
        _logger.error("check_feature_flag_failed", error=str(exc), flag=flag_name)
        raise HTTPException(status_code=500, detail=f"Failed to check feature flag: {str(exc)}")


# Environment Profiles Endpoints

@router.get("/profiles", tags=["Profiles"])
async def get_environment_profiles() -> Dict[str, Any]:
    """Get available environment profiles."""
    try:
        env_loader = get_environment_loader()
        profiles = env_loader.list_profiles()
        
        return {
            "profiles": profiles,
            "total_count": len(profiles)
        }
        
    except Exception as exc:
        _logger.error("get_profiles_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Failed to get profiles: {str(exc)}")


@router.post("/profiles/{profile_name}/apply", tags=["Profiles"])
async def apply_environment_profile(
    profile_name: str,
    request: ProfileApplyRequest,
    config_manager=Depends(get_config_manager_dependency())
) -> Dict[str, Any]:
    """Apply an environment profile."""
    try:
        env_loader = get_environment_loader()
        
        # Get current configuration as base
        current_config = await config_manager.get_current_config()
        if not current_config:
            current_config = GrpcConfig()
        
        # Load profile configuration
        profile_config = await env_loader.load_profile_config(profile_name, current_config)
        
        # Validate for environment
        issues = profile_config.validate_for_environment(profile_name)
        if issues and not request.force:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": f"Profile validation failed for {profile_name}",
                    "issues": issues
                }
            )
        
        # Apply profile configuration
        config_dict = profile_config.get_effective_config()
        success = await config_manager.update_config(
            config_dict,
            description=f"Applied {profile_name} profile"
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to apply profile")
        
        return {
            "message": f"Profile {profile_name} applied successfully",
            "profile": profile_name,
            "config": config_dict,
            "validation_issues": issues if request.force else []
        }
        
    except HTTPException:
        raise
    except Exception as exc:
        _logger.error("apply_profile_failed", error=str(exc), profile=profile_name)
        raise HTTPException(status_code=500, detail=f"Failed to apply profile: {str(exc)}")


@router.get("/stats")
async def get_configuration_statistics(
    config_manager=Depends(get_config_manager_dependency())
) -> Dict[str, Any]:
    """Get configuration system statistics."""
    try:
        stats = await config_manager.get_statistics()
        
        # Add feature flags statistics
        feature_toggles = await get_feature_toggles()
        feature_stats = await feature_toggles.get_statistics()
        
        return {
            "config_manager": stats,
            "feature_flags": feature_stats,
            "timestamp": config_manager.get_current_timestamp()
        }
        
    except Exception as exc:
        _logger.error("get_config_stats_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(exc)}")
