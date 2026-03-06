"""Provider API endpoints."""

from fastapi import APIRouter

from mindflow_backend.api.controllers.provider_controller import ProviderController
from mindflow_backend.api.schemas.requests import ProviderConfigRequest, ProviderTestRequest

router = APIRouter(prefix="/providers", tags=["providers"])

# Initialize controller
provider_controller = ProviderController()


@router.get("/")
async def list_providers():
    """List available LLM providers."""
    return await provider_controller.list_providers()


@router.get("/{provider_id}/models")
async def get_provider_models(provider_id: str):
    """Get available models for a provider."""
    return await provider_controller.get_provider_models(provider_id)


@router.post("/{provider_id}/test")
async def test_provider(provider_id: str, request: ProviderTestRequest = None):
    """Test connection to a provider."""
    if request is None:
        request = ProviderTestRequest(provider_id=provider_id)
    return await provider_controller.test_provider(request)


@router.get("/{provider_id}/config")
async def get_provider_config(provider_id: str):
    """Get provider configuration."""
    return await provider_controller.get_provider_config(provider_id)


@router.put("/{provider_id}/config")
async def update_provider_config(provider_id: str, request: ProviderConfigRequest):
    """Update provider configuration."""
    return await provider_controller.update_provider_config(provider_id, request)


@router.get("/fallback-chain")
async def get_fallback_chain():
    """Get provider fallback chain."""
    return await provider_controller.get_fallback_chain()


@router.post("/{provider_id}/handle-failure")
async def handle_provider_failure(provider_id: str, error: str):
    """Handle provider failure and trigger fallback."""
    return await provider_controller.handle_provider_failure(provider_id, error)


@router.get("/health-check")
async def health_check_all_providers():
    """Health check all providers."""
    return await provider_controller.health_check_all_providers()
