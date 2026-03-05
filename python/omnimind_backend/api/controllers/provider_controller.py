"""Provider controller for managing LLM providers and model configurations."""

from __future__ import annotations

from typing import Any
from fastapi import Request

from omnimind_backend.api.controllers.base_controller import BaseController, require_auth, audit_log
from omnimind_backend.api.schemas.requests import ProviderConfigRequest, ProviderTestRequest
from omnimind_backend.api.schemas.responses import (
    ProviderResponse,
    ProviderListResponse,
    ProviderTestResponse
)
from omnimind_backend.api.services.provider_service import ProviderService


class ProviderController(BaseController):
    """Controller for provider management operations."""
    
    def __init__(self):
        super().__init__()
        self.provider_service = ProviderService()
    
    @require_auth
    @audit_log("provider_list")
    async def list_providers(self, req: Request) -> ProviderListResponse:
        """List available LLM providers."""
        try:
            self.log_request(req, "list_providers")
            
            providers_data = await self.provider_service.list_providers()
            
            provider_responses = []
            for provider_data in providers_data:
                provider_responses.append(ProviderResponse(
                    success=True,
                    provider_id=provider_data["id"],
                    name=provider_data["name"],
                    status=provider_data["status"],
                    models=provider_data.get("models", []),
                    config=provider_data.get("config", {}),
                    metadata=provider_data
                ))
            
            return ProviderListResponse(
                success=True,
                message="Providers retrieved successfully",
                providers=provider_responses,
                total=len(provider_responses)
            )
            
        except Exception as e:
            raise self.handle_error(e, "list_providers")
    
    @require_auth
    @audit_log("provider_models")
    async def get_provider_models(self, provider_id: str, req: Request) -> ProviderResponse:
        """Get available models for a provider."""
        try:
            self.log_request(req, "get_provider_models", provider_id=provider_id)
            
            models_data = await self.provider_service.get_provider_models(provider_id)
            
            return ProviderResponse(
                success=True,
                message=f"Models retrieved for {provider_id}",
                provider_id=provider_id,
                models=models_data,
                metadata={"models": models_data}
            )
            
        except Exception as e:
            raise self.handle_error(e, "get_provider_models")
    
    @require_auth
    @audit_log("provider_test")
    async def test_provider(self, request: ProviderTestRequest, req: Request) -> ProviderTestResponse:
        """Test connection to a provider."""
        try:
            self.log_request(req, "test_provider", provider_id=request.provider_id)
            
            test_result = await self.provider_service.test_provider_connection(request.provider_id)
            
            return ProviderTestResponse(
                success=test_result["status"] == "success",
                message=f"Test completed for {request.provider_id}",
                provider_id=request.provider_id,
                status=test_result["status"],
                latency_ms=test_result.get("latency_ms"),
                tested_at=test_result.get("tested_at"),
                error=test_result.get("error") if test_result["status"] != "success" else None,
                metadata=test_result
            )
            
        except Exception as e:
            raise self.handle_error(e, "test_provider")
    
    @require_auth
    @audit_log("provider_config_get")
    async def get_provider_config(self, provider_id: str, req: Request) -> ProviderResponse:
        """Get provider configuration."""
        try:
            self.log_request(req, "get_provider_config", provider_id=provider_id)
            
            config_data = await self.provider_service.get_provider_config(provider_id)
            
            return ProviderResponse(
                success=True,
                message=f"Configuration retrieved for {provider_id}",
                provider_id=provider_id,
                config=config_data["config"],
                metadata=config_data
            )
            
        except Exception as e:
            raise self.handle_error(e, "get_provider_config")
    
    @require_auth
    @audit_log("provider_config_update")
    async def update_provider_config(
        self, 
        provider_id: str, 
        request: ProviderConfigRequest, 
        req: Request
    ) -> ProviderResponse:
        """Update provider configuration."""
        try:
            self.log_request(req, "update_provider_config", provider_id=provider_id)
            
            # Build config dict from request
            config = {}
            if request.api_endpoint is not None:
                config["api_endpoint"] = request.api_endpoint
            if request.timeout is not None:
                config["timeout"] = request.timeout
            if request.max_tokens is not None:
                config["max_tokens"] = request.max_tokens
            if request.api_key is not None:
                config["api_key"] = request.api_key
            
            # Add metadata
            config.update(request.metadata)
            
            result = await self.provider_service.update_provider_config(provider_id, config)
            
            return ProviderResponse(
                success=True,
                message=f"Configuration updated for {provider_id}",
                provider_id=provider_id,
                config=result["config"],
                metadata=result
            )
            
        except Exception as e:
            raise self.handle_error(e, "update_provider_config")
    
    @require_auth
    @audit_log("provider_fallback_chain")
    async def get_fallback_chain(self, req: Request) -> dict[str, Any]:
        """Get provider fallback chain."""
        try:
            self.log_request(req, "get_fallback_chain")
            
            chain = await self.provider_service.get_fallback_chain()
            
            return {
                "success": True,
                "message": "Fallback chain retrieved",
                "chain": chain,
                "primary": chain[0] if chain else None,
                "fallbacks": chain[1:] if len(chain) > 1 else [],
                "total_providers": len(chain)
            }
            
        except Exception as e:
            raise self.handle_error(e, "get_fallback_chain")
    
    @require_auth
    @audit_log("provider_failure_handle")
    async def handle_provider_failure(
        self,
        provider_id: str,
        error: str,
        req: Request
    ) -> dict[str, Any]:
        """Handle provider failure and trigger fallback."""
        try:
            self.log_request(req, "handle_provider_failure", provider_id=provider_id)
            
            result = await self.provider_service.handle_provider_failure(provider_id, error)
            
            return {
                "success": True,
                "message": f"Failure handled for {provider_id}",
                "failed_provider": result["failed_provider"],
                "fallback_triggered": result["fallback_triggered"],
                "next_provider": result.get("next_provider"),
                "error": result["error"],
                "metadata": result
            }
            
        except Exception as e:
            raise self.handle_error(e, "handle_provider_failure")
    
    @require_auth
    @audit_log("provider_health_check")
    async def health_check_all_providers(self, req: Request) -> dict[str, Any]:
        """Health check all providers."""
        try:
            self.log_request(req, "health_check_all_providers")
            
            providers_data = await self.provider_service.list_providers()
            health_results = {}
            
            for provider in providers_data:
                provider_id = provider["id"]
                try:
                    test_result = await self.provider_service.test_provider_connection(provider_id)
                    health_results[provider_id] = {
                        "status": test_result["status"],
                        "latency_ms": test_result.get("latency_ms"),
                        "last_check": test_result.get("tested_at"),
                        "available": test_result["status"] == "success"
                    }
                except Exception as e:
                    health_results[provider_id] = {
                        "status": "error",
                        "error": str(e),
                        "available": False
                    }
            
            available_count = len([p for p in health_results.values() if p.get("available")])
            
            return {
                "success": True,
                "message": "Health check completed",
                "providers": health_results,
                "total_providers": len(health_results),
                "available_providers": available_count,
                "unavailable_providers": len(health_results) - available_count,
                "all_available": available_count == len(health_results)
            }
            
        except Exception as e:
            raise self.handle_error(e, "health_check_all_providers")
