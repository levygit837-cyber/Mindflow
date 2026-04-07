"""LLM Service for text generation and completion.

This module provides a unified interface for LLM text generation operations,
supporting multiple providers (OpenAI, Anthropic, Google, Vertex AI, Ollama).
"""

from __future__ import annotations

from typing import Any

from langchain.schema import HumanMessage, SystemMessage

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.runtime.providers.providers import get_model_for_provider
from mindflow_backend.schemas.core.common import LLMProvider

_logger = get_logger(__name__)


class LLMService:
    """Service for LLM text generation and completion.
    
    This service provides a unified interface for generating text using
    various LLM providers, with automatic provider selection and fallback.
    """
    
    def __init__(
        self,
        provider: LLMProvider | None = None,
        model: str | None = None,
        api_key: str | None = None,
    ) -> None:
        """Initialize the LLM service.
        
        Args:
            provider: LLM provider to use (defaults to settings)
            model: Model name to use (defaults to settings)
            api_key: Optional API key (defaults to settings/env)
        """
        settings = get_settings()
        
        self._provider = provider or getattr(settings, 'default_llm_provider', 'openai')
        self._model = model or getattr(settings, 'default_llm_model', 'gpt-4o-mini')
        self._api_key = api_key
        self._model_instance: Any | None = None
    
    def _get_model(self) -> Any:
        """Get or create the model instance."""
        if self._model_instance is None:
            self._model_instance = get_model_for_provider(
                provider=self._provider,
                model=self._model,
                api_key=self._api_key,
            )
        return self._model_instance
    
    async def generate(
        self,
        prompt: str,
        *,
        system_message: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """Generate text from a prompt.
        
        Args:
            prompt: The user prompt to send to the LLM
            system_message: Optional system message for context
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text response
            
        Raises:
            RuntimeError: If generation fails
        """
        try:
            model = self._get_model()
            
            messages = []
            if system_message:
                messages.append(SystemMessage(content=system_message))
            messages.append(HumanMessage(content=prompt))
            
            kwargs: dict[str, Any] = {"temperature": temperature}
            if max_tokens:
                kwargs["max_tokens"] = max_tokens
            
            response = await model.ainvoke(messages, **kwargs)
            
            # Handle different response formats
            if hasattr(response, 'content'):
                return str(response.content)
            return str(response)
            
        except Exception as exc:
            _logger.error(
                "llm_generation_failed",
                provider=self._provider,
                model=self._model,
                error=str(exc),
                exc_info=True,
            )
            raise RuntimeError(f"LLM generation failed: {exc}") from exc
    
    async def generate_with_fallback(
        self,
        prompt: str,
        *,
        system_message: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        fallback_provider: LLMProvider | None = None,
        fallback_model: str | None = None,
    ) -> str:
        """Generate text with automatic fallback on failure.
        
        Args:
            prompt: The user prompt
            system_message: Optional system message
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            fallback_provider: Provider to use if primary fails
            fallback_model: Model to use if primary fails
            
        Returns:
            Generated text response
        """
        try:
            return await self.generate(
                prompt,
                system_message=system_message,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            if fallback_provider and fallback_model:
                _logger.warning(
                    "llm_fallback_activated",
                    primary_provider=self._provider,
                    fallback_provider=fallback_provider,
                    error=str(exc),
                )
                
                # Create fallback service
                fallback_service = LLMService(
                    provider=fallback_provider,
                    model=fallback_model,
                )
                return await fallback_service.generate(
                    prompt,
                    system_message=system_message,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            raise


# Singleton instance
_llm_service: LLMService | None = None


def get_llm_service(
    provider: LLMProvider | None = None,
    model: str | None = None,
) -> LLMService:
    """Get the singleton LLM service instance.
    
    Args:
        provider: Optional provider override
        model: Optional model override
        
    Returns:
        LLMService instance
    """
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService(provider=provider, model=model)
    return _llm_service


def reset_llm_service() -> None:
    """Reset the singleton instance (useful for testing)."""
    global _llm_service
    _llm_service = None
