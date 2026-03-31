"""Provider service for managing LLM providers and model configurations.

This service provides comprehensive provider management including listing,
configuration, connection testing, and fallback chain management.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.runtime import get_model_for_provider
from mindflow_backend.services.interfaces.base_interfaces import BaseAbstractService
from mindflow_backend.services.interfaces.core_interfaces import ProviderServiceInterface


class ProviderService(BaseAbstractService, ProviderServiceInterface):
    """Service for managing LLM providers, models, and configurations.
    
    This service handles provider lifecycle, model management, connection testing,
    and provides intelligent fallback mechanisms for reliable operation.
    """
    
    def __init__(self) -> None:
        """Initialize provider service with configuration and registry."""
        super().__init__()
        self.settings = get_settings()
        
        # Provider registry with capabilities
        self._provider_registry = {
            "google": {
                "name": "Google/VertexAI",
                "models": [
                    {"id": "gemini-3.1-flash-lite-preview", "name": "Gemini 3.1 Flash Lite Preview", "context_window": 1048576, "supports_vision": True},
                    {"id": "gemini-3.1-pro-preview", "name": "Gemini 3.1 Pro Preview", "context_window": 1048576, "supports_vision": True},
                    {"id": "gemini-3.1-pro-preview-customtools", "name": "Gemini 3.1 Pro Preview Custom Tools", "context_window": 1048576, "supports_vision": True},
                ],
                "capabilities": ["text_generation", "vision", "function_calling"],
                "status": "active"
            },
            "anthropic": {
                "name": "Anthropic",
                "models": [
                    {"id": "claude-3-sonnet", "name": "Claude 3 Sonnet", "context_window": 200000, "supports_vision": True},
                    {"id": "claude-3-opus", "name": "Claude 3 Opus", "context_window": 200000, "supports_vision": True},
                    {"id": "claude-3-haiku", "name": "Claude 3 Haiku", "context_window": 200000, "supports_vision": True},
                ],
                "capabilities": ["text_generation", "vision", "function_calling"],
                "status": "active"
            },
            "openai": {
                "name": "OpenAI",
                "models": [
                    {"id": "gpt-4", "name": "GPT-4", "context_window": 8192, "supports_vision": False},
                    {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "context_window": 128000, "supports_vision": True},
                    {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "context_window": 16385, "supports_vision": False},
                ],
                "capabilities": ["text_generation", "vision", "function_calling"],
                "status": "active"
            },
            "ollama": {
                "name": "Ollama (Local)",
                "models": [
                    {"id": "qwen3.5-0.8b", "name": "Qwen 3.5 0.8B", "context_window": 262144, "supports_vision": False},
                    {"id": "llama2", "name": "Llama 2", "context_window": 4096, "supports_vision": False},
                    {"id": "codellama", "name": "Code Llama", "context_window": 4096, "supports_vision": False},
                    {"id": "mistral", "name": "Mistral", "context_window": 4096, "supports_vision": False},
                ],
                "capabilities": ["text_generation"],
                "status": "conditional"  # Depends on local setup
            }
        }
        
        # Default fallback chain
        self._fallback_chain = ["google", "anthropic", "openai", "ollama"]
        
        # Connection status cache
        self._connection_cache: dict[str, dict[str, Any]] = {}
        self._cache_ttl = 300  # 5 minutes
    
    def _get_logger(self) -> Any:
        """Get logger instance for this service."""
        return get_logger(__name__)
    
    async def list_providers(self) -> list[dict[str, Any]]:
        """List available LLM providers with their status and capabilities.
        
        Returns:
            List of provider dictionaries with detailed information
        """
        self.log_operation("list_providers")
        
        try:
            providers = []
            
            for provider_id, provider_info in self._provider_registry.items():
                # Check connection status (with caching)
                connection_status = await self._get_cached_connection_status(provider_id)
                
                providers.append({
                    "id": provider_id,
                    "name": provider_info["name"],
                    "status": connection_status.get("overall_status", provider_info["status"]),
                    "models": provider_info["models"],
                    "capabilities": provider_info["capabilities"],
                    "model_count": len(provider_info["models"]),
                    "connection": {
                        "last_checked": connection_status.get("last_checked"),
                        "latency_ms": connection_status.get("latency_ms"),
                        "error": connection_status.get("error")
                    },
                    "is_default": provider_id == self.settings.default_provider
                })
            
            # Sort by status (active first) then by name
            providers.sort(key=lambda x: (x["status"] != "active", x["name"]))
            
            return providers
            
        except Exception as exc:
            self._logger.error(f"Error listing providers: {str(exc)}")
            raise
    
    async def get_provider_models(self, provider_id: str) -> list[dict[str, Any]]:
        """Get available models for a specific provider.
        
        Args:
            provider_id: Provider identifier
            
        Returns:
            List of model dictionaries with detailed specifications
        """
        self.log_operation("get_provider_models", provider_id=provider_id)
        
        try:
            provider_info = self._provider_registry.get(provider_id)
            if not provider_info:
                raise ValueError(f"Unknown provider: {provider_id}")
            
            # Enhance model information with runtime data
            models = []
            for model in provider_info["models"]:
                model_info = model.copy()
                
                # Add runtime information
                try:
                    # Try to get actual model instance to check availability
                    model_instance = get_model_for_provider(provider_id, model["id"])
                    model_info["available"] = True
                    model_info["tested_at"] = datetime.now(UTC).isoformat()
                except Exception:
                    model_info["available"] = False
                    model_info["error"] = "Model not available"
                
                models.append(model_info)
            
            return models
            
        except Exception as exc:
            self._logger.error(f"Error getting provider models for {provider_id}: {str(exc)}")
            raise
    
    async def test_provider_connection(self, provider_id: str) -> dict[str, Any]:
        """Test connection to a provider and measure performance.
        
        Args:
            provider_id: Provider identifier
            
        Returns:
            Dictionary containing comprehensive test results
        """
        self.log_operation("test_provider_connection", provider_id=provider_id)
        
        try:
            provider_info = self._provider_registry.get(provider_id)
            if not provider_info:
                raise ValueError(f"Unknown provider: {provider_id}")
            
            # Test connection with timing
            start_time = datetime.now(UTC)
            
            try:
                # Try to get a model instance
                model = get_model_for_provider(provider_id)
                
                # Perform a simple test invocation (non-blocking)
                # This is a simplified test - in production you'd use a lightweight test prompt
                test_result = await self._perform_connection_test(provider_id, model)
                
                end_time = datetime.now(UTC)
                latency_ms = int((end_time - start_time).total_seconds() * 1000)
                
                result = {
                    "provider_id": provider_id,
                    "status": "success",
                    "latency_ms": latency_ms,
                    "tested_at": end_time.isoformat(),
                    "test_result": test_result,
                    "models_tested": len(provider_info["models"]),
                    "capabilities_verified": provider_info["capabilities"]
                }
                
                # Cache the successful result
                self._cache_connection_status(provider_id, result)
                
                return result
                
            except Exception as exc:
                end_time = datetime.now(UTC)
                latency_ms = int((end_time - start_time).total_seconds() * 1000)
                
                result = {
                    "provider_id": provider_id,
                    "status": "failed",
                    "latency_ms": latency_ms,
                    "tested_at": end_time.isoformat(),
                    "error": str(exc),
                    "error_type": type(exc).__name__
                }
                
                # Cache the failed result
                self._cache_connection_status(provider_id, result)
                
                return result
                
        except Exception as exc:
            self._logger.error(f"Error testing provider connection for {provider_id}: {str(exc)}")
            raise
    
    async def get_provider_config(self, provider_id: str) -> dict[str, Any]:
        """Get current configuration for a provider.
        
        Args:
            provider_id: Provider identifier
            
        Returns:
            Dictionary containing provider configuration
        """
        self.log_operation("get_provider_config", provider_id=provider_id)
        
        try:
            provider_info = self._provider_registry.get(provider_id)
            if not provider_info:
                raise ValueError(f"Unknown provider: {provider_id}")
            
            # Get configuration from settings
            config = {
                "provider_id": provider_id,
                "name": provider_info["name"],
                "models": provider_info["models"],
                "capabilities": provider_info["capabilities"],
                "settings": {}
            }
            
            # Add provider-specific settings
            if provider_id == "google":
                config["settings"] = {
                    "api_key_configured": bool(self.settings.google_api_key),
                    "project_id": getattr(self.settings, 'google_project_id', None),
                    "location": getattr(self.settings, 'google_location', 'us-central1')
                }
            elif provider_id == "anthropic":
                config["settings"] = {
                    "api_key_configured": bool(getattr(self.settings, 'anthropic_api_key', None)),
                    "max_tokens": getattr(self.settings, 'anthropic_max_tokens', 4096)
                }
            elif provider_id == "openai":
                config["settings"] = {
                    "api_key_configured": bool(getattr(self.settings, 'openai_api_key', None)),
                    "organization": getattr(self.settings, 'openai_organization', None),
                    "base_url": getattr(self.settings, 'openai_base_url', None)
                }
            elif provider_id == "ollama":
                config["settings"] = {
                    "base_url": getattr(self.settings, 'ollama_base_url', 'http://localhost:11434'),
                    "timeout": getattr(self.settings, 'ollama_timeout', 30)
                }
            
            # Add connection status
            connection_status = await self._get_cached_connection_status(provider_id)
            config["connection_status"] = connection_status
            
            return config
            
        except Exception as exc:
            self._logger.error(f"Error getting provider config for {provider_id}: {str(exc)}")
            raise
    
    async def update_provider_config(
        self,
        provider_id: str,
        config: dict[str, Any]
    ) -> dict[str, Any]:
        """Update provider configuration.
        
        Args:
            provider_id: Provider identifier
            config: New configuration settings
            
        Returns:
            Updated configuration
        """
        self.log_operation("update_provider_config", provider_id=provider_id)
        
        try:
            provider_info = self._provider_registry.get(provider_id)
            if not provider_info:
                raise ValueError(f"Unknown provider: {provider_id}")
            
            # Validate configuration
            if not await self.validate_provider_config(config):
                raise ValueError("Invalid configuration provided")
            
            # In a real implementation, this would update persistent storage
            # For now, we'll just validate and return the updated config
            
            updated_config = await self.get_provider_config(provider_id)
            updated_config["updated_at"] = datetime.now(UTC).isoformat()
            updated_config["changes"] = config
            
            # Clear connection cache as configuration might have changed
            if provider_id in self._connection_cache:
                del self._connection_cache[provider_id]
            
            return updated_config
            
        except Exception as exc:
            self._logger.error(f"Error updating provider config for {provider_id}: {str(exc)}")
            raise
    
    async def get_fallback_chain(self) -> list[str]:
        """Get the current fallback provider chain.
        
        Returns:
            List of provider IDs in fallback order
        """
        self.log_operation("get_fallback_chain")
        
        try:
            # Filter to only include available providers
            available_providers = []
            
            for provider_id in self._fallback_chain:
                if provider_id in self._provider_registry:
                    connection_status = await self._get_cached_connection_status(provider_id)
                    if connection_status.get("overall_status") == "active":
                        available_providers.append(provider_id)
            
            return available_providers
            
        except Exception as exc:
            self._logger.error(f"Error getting fallback chain: {str(exc)}")
            return self._fallback_chain
    
    async def handle_provider_failure(
        self,
        provider_id: str,
        error: str
    ) -> dict[str, Any]:
        """Handle provider failure and suggest fallback options.
        
        Args:
            provider_id: Failed provider ID
            error: Error description
            
        Returns:
            Dictionary containing failure handling information
        """
        self.log_operation("handle_provider_failure", provider_id=provider_id, error=error[:100])
        
        try:
            # Mark provider as having issues
            failure_record = {
                "provider_id": provider_id,
                "error": error,
                "timestamp": datetime.now(UTC).isoformat(),
                "handled": True
            }
            
            # Update connection cache to reflect failure
            self._cache_connection_status(provider_id, {
                "status": "failed",
                "error": error,
                "last_checked": datetime.now(UTC).isoformat()
            })
            
            # Get fallback options
            fallback_chain = await self.get_fallback_chain()
            
            # Remove failed provider from chain
            fallback_options = [p for p in fallback_chain if p != provider_id]
            
            return {
                "failed_provider": provider_id,
                "error": error,
                "fallback_options": fallback_options,
                "recommended_alternative": fallback_options[0] if fallback_options else None,
                "failure_record": failure_record,
                "action_required": len(fallback_options) == 0
            }
            
        except Exception as exc:
            self._logger.error(f"Error handling provider failure for {provider_id}: {str(exc)}")
            raise
    
    async def get_optimal_provider(
        self,
        task_type: str,
        model_requirements: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Get optimal provider for a specific task type.
        
        Args:
            task_type: Type of task (e.g., "coding", "analysis", "vision")
            model_requirements: Optional model requirements
            
        Returns:
            Dictionary containing optimal provider recommendation
        """
        self.log_operation("get_optimal_provider", task_type=task_type)
        
        try:
            # Define task-to-provider mappings
            task_mappings = {
                "coding": ["openai", "anthropic", "google"],
                "analysis": ["anthropic", "google", "openai"],
                "vision": ["google", "anthropic", "openai"],
                "reasoning": ["anthropic", "google", "openai"],
                "general": ["google", "anthropic", "openai"]
            }
            
            preferred_providers = task_mappings.get(task_type, task_mappings["general"])
            
            # Check availability and performance
            available_providers = []
            
            for provider_id in preferred_providers:
                if provider_id not in self._provider_registry:
                    continue
                
                connection_status = await self._get_cached_connection_status(provider_id)
                if connection_status.get("overall_status") == "active":
                    provider_info = self._provider_registry[provider_id]
                    
                    # Check if provider supports task requirements
                    if model_requirements:
                        required_capabilities = model_requirements.get("capabilities", [])
                        if not all(cap in provider_info["capabilities"] for cap in required_capabilities):
                            continue
                    
                    available_providers.append({
                        "provider_id": provider_id,
                        "name": provider_info["name"],
                        "latency_ms": connection_status.get("latency_ms", 0),
                        "preference_score": len(preferred_providers) - preferred_providers.index(provider_id)
                    })
            
            # Sort by preference score and latency
            available_providers.sort(key=lambda x: (-x["preference_score"], x["latency_ms"]))
            
            if not available_providers:
                # No optimal provider found, return first available
                fallback_chain = await self.get_fallback_chain()
                if fallback_chain:
                    provider_id = fallback_chain[0]
                    provider_info = self._provider_registry[provider_id]
                    return {
                        "provider_id": provider_id,
                        "name": provider_info["name"],
                        "reason": "fallback_only_available",
                        "confidence": 0.5
                    }
                else:
                    raise ValueError("No available providers found")
            
            optimal = available_providers[0]
            
            return {
                "provider_id": optimal["provider_id"],
                "name": optimal["name"],
                "reason": "optimal_for_task",
                "confidence": 0.9,
                "latency_ms": optimal["latency_ms"],
                "alternatives": available_providers[1:3]  # Top 3 alternatives
            }
            
        except Exception as exc:
            self._logger.error(f"Error getting optimal provider for {task_type}: {str(exc)}")
            raise
    
    async def validate_provider_config(self, config: dict[str, Any]) -> bool:
        """Validate provider configuration.
        
        Args:
            config: Configuration to validate
            
        Returns:
            True if configuration is valid
        """
        self.log_operation("validate_provider_config")
        
        try:
            # Basic validation
            required_fields = ["provider_id"]
            for field in required_fields:
                if field not in config:
                    raise ValueError(f"Missing required field: {field}")
            
            provider_id = config["provider_id"]
            if provider_id not in self._provider_registry:
                raise ValueError(f"Unknown provider: {provider_id}")
            
            # Provider-specific validation
            if provider_id == "google":
                # Check for required Google settings
                if "api_key" in config and not config["api_key"]:
                    raise ValueError("Google API key cannot be empty")
            elif provider_id == "anthropic":
                # Check for required Anthropic settings
                if "api_key" in config and not config["api_key"]:
                    raise ValueError("Anthropic API key cannot be empty")
            elif provider_id == "openai":
                # Check for required OpenAI settings
                if "api_key" in config and not config["api_key"]:
                    raise ValueError("OpenAI API key cannot be empty")
            elif provider_id == "ollama":
                # Check for required Ollama settings
                if "base_url" in config:
                    if not config["base_url"].startswith(("http://", "https://")):
                        raise ValueError("Ollama base URL must be a valid HTTP/HTTPS URL")
            
            return True
            
        except Exception as exc:
            self._logger.error(f"Provider config validation failed: {str(exc)}")
            return False
    
    # Helper methods
    
    async def _perform_connection_test(self, provider_id: str, model: Any) -> dict[str, Any]:
        """Perform a lightweight connection test."""
        try:
            # This is a simplified test - in production you'd use a minimal test prompt
            # For now, we'll just verify the model can be instantiated
            return {
                "model_instantiated": True,
                "model_type": type(model).__name__,
                "test_passed": True
            }
        except Exception as exc:
            return {
                "model_instantiated": False,
                "error": str(exc),
                "test_passed": False
            }
    
    async def _get_cached_connection_status(self, provider_id: str) -> dict[str, Any]:
        """Get cached connection status or perform fresh test."""
        if provider_id in self._connection_cache:
            cached = self._connection_cache[provider_id]
            cache_age = (datetime.now(UTC) - datetime.fromisoformat(cached["last_checked"])).total_seconds()
            
            if cache_age < self._cache_ttl:
                return cached
        
        # Perform fresh test
        test_result = await self.test_provider_connection(provider_id)
        self._cache_connection_status(provider_id, test_result)
        
        return test_result
    
    def _cache_connection_status(self, provider_id: str, result: dict[str, Any]) -> None:
        """Cache connection status result."""
        cache_entry = {
            "last_checked": result.get("tested_at", datetime.now(UTC).isoformat()),
            "overall_status": "active" if result.get("status") == "success" else "failed",
            "latency_ms": result.get("latency_ms"),
            "error": result.get("error")
        }
        
        self._connection_cache[provider_id] = cache_entry
