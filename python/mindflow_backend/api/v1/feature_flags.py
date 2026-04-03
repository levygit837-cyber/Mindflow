"""Feature Flags API endpoints.

Provides REST API for managing feature flags.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.runtime.feature_flags_v2 import (
    ABExperiment,
    ABVariant,
    FeatureFlagV2,
    FeatureFlagsV2,
    get_feature_flags_v2,
)

_logger = get_logger(__name__)

router = APIRouter(prefix="/features", tags=["feature-flags"])


class FeatureFlagResponse(BaseModel):
    """Response model para feature flag."""
    name: str
    enabled: bool
    status: str
    rollout_percentage: float
    dependencies: list[str]
    description: str
    has_experiment: bool
    overridden: bool


class OverrideRequest(BaseModel):
    """Request para override de feature flag."""
    enabled: bool = Field(..., description="Se a flag deve ser habilitada")


class RegisterFlagRequest(BaseModel):
    """Request para registrar uma nova feature flag."""
    name: str = Field(..., description="Nome da flag")
    enabled: bool = Field(default=False, description="Se a flag está habilitada")
    rollout_percentage: float = Field(default=100.0, description="Percentual de rollout (0-100)")
    dependencies: list[str] = Field(default_factory=list, description="Flags dependentes")
    description: str = Field(default="", description="Descrição da flag")


@router.get("", response_model=dict[str, FeatureFlagResponse])
async def list_features() -> dict[str, FeatureFlagResponse]:
    """Lista todas as feature flags.

    GET /api/v1/features
    """
    try:
        ff = get_feature_flags_v2()
        all_flags = ff.get_all_flags()

        return {
            name: FeatureFlagResponse(**data) for name, data in all_flags.items()
        }

    except Exception as e:
        _logger.error("list_features_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{flag_name}/status", response_model=FeatureFlagResponse)
async def feature_status(flag_name: str) -> FeatureFlagResponse:
    """Retorna status detalhado de uma feature flag.

    GET /api/v1/features/{flag_name}/status
    """
    try:
        ff = get_feature_flags_v2()
        all_flags = ff.get_all_flags()

        if flag_name not in all_flags:
            raise HTTPException(
                status_code=404, detail=f"Feature flag '{flag_name}' not found"
            )

        return FeatureFlagResponse(**all_flags[flag_name])

    except HTTPException:
        raise
    except Exception as e:
        _logger.error("feature_status_error", flag=flag_name, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{flag_name}/override")
async def override_feature(flag_name: str, request: OverrideRequest) -> dict[str, str]:
    """Override local de uma feature flag.

    POST /api/v1/features/{flag_name}/override

    Request:
    {
        "enabled": true
    }
    """
    try:
        ff = get_feature_flags_v2()
        ff.override(flag_name, request.enabled)

        _logger.info(
            "feature_override_api",
            flag=flag_name,
            enabled=request.enabled,
        )

        return {
            "message": f"Feature flag '{flag_name}' overridden to {request.enabled}",
            "flag": flag_name,
            "enabled": str(request.enabled),
        }

    except Exception as e:
        _logger.error("override_feature_error", flag=flag_name, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{flag_name}/override")
async def clear_override(flag_name: str) -> dict[str, str]:
    """Remove override de uma feature flag.

    DELETE /api/v1/features/{flag_name}/override
    """
    try:
        ff = get_feature_flags_v2()
        ff.clear_override(flag_name)

        _logger.info("feature_override_cleared", flag=flag_name)

        return {
            "message": f"Override cleared for feature flag '{flag_name}'",
            "flag": flag_name,
        }

    except Exception as e:
        _logger.error("clear_override_error", flag=flag_name, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/register")
async def register_feature(request: RegisterFlagRequest) -> dict[str, str]:
    """Registra uma nova feature flag.

    POST /api/v1/features/register

    Request:
    {
        "name": "NEW_FEATURE",
        "enabled": true,
        "rollout_percentage": 50.0,
        "dependencies": ["BASE_FEATURE"],
        "description": "New experimental feature"
    }
    """
    try:
        ff = get_feature_flags_v2()

        flag = FeatureFlagV2(
            name=request.name,
            enabled=request.enabled,
            rollout_percentage=request.rollout_percentage,
            dependencies=request.dependencies,
            description=request.description,
        )

        ff.register(flag)

        _logger.info(
            "feature_registered_api",
            name=request.name,
            enabled=request.enabled,
            rollout=request.rollout_percentage,
        )

        return {
            "message": f"Feature flag '{request.name}' registered successfully",
            "name": request.name,
        }

    except Exception as e:
        _logger.error("register_feature_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{flag_name}")
async def unregister_feature(flag_name: str) -> dict[str, str]:
    """Remove uma feature flag.

    DELETE /api/v1/features/{flag_name}
    """
    try:
        ff = get_feature_flags_v2()
        ff.unregister(flag_name)

        _logger.info("feature_unregistered_api", name=flag_name)

        return {
            "message": f"Feature flag '{flag_name}' unregistered",
            "name": flag_name,
        }

    except Exception as e:
        _logger.error("unregister_feature_error", flag=flag_name, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def feature_flags_health() -> dict[str, str]:
    """Health check do sistema de feature flags."""
    return {"status": "healthy", "module": "feature_flags_v2"}