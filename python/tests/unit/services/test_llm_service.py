"""Tests for LLMService.

This module tests the LLM service implementation including:
- Service initialization
- Text generation
- Fallback mechanisms
- Provider integration
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mindflow_backend.services.llm import LLMService, get_llm_service, reset_llm_service


class TestLLMService:
    """Test LLMService functionality."""

    def test_service_initialization(self):
        """Test LLMService can be initialized."""
        service = LLMService(
            provider="openai",
            model="gpt-4o-mini",
        )
        assert service._provider == "openai"
        assert service._model == "gpt-4o-mini"
        assert service._model_instance is None  # Lazy loaded

    def test_singleton_factory(self):
        """Test get_llm_service returns singleton."""
        reset_llm_service()
        
        service1 = get_llm_service()
        service2 = get_llm_service()
        
        assert service1 is service2
        
        reset_llm_service()

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Test successful text generation."""
        service = LLMService(provider="openai", model="gpt-4o-mini")
        
        # Mock the model
        mock_model = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "Generated response"
        mock_model.ainvoke.return_value = mock_response
        
        with patch.object(service, '_get_model', return_value=mock_model):
            result = await service.generate(
                prompt="Test prompt",
                system_message="You are a test assistant",
                temperature=0.5,
            )
        
        assert result == "Generated response"
        mock_model.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_without_system_message(self):
        """Test generation without system message."""
        service = LLMService(provider="openai", model="gpt-4o-mini")
        
        mock_model = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "Simple response"
        mock_model.ainvoke.return_value = mock_response
        
        with patch.object(service, '_get_model', return_value=mock_model):
            result = await service.generate(prompt="Test prompt")
        
        assert result == "Simple response"

    @pytest.mark.asyncio
    async def test_generate_error(self):
        """Test error handling during generation."""
        service = LLMService(provider="openai", model="gpt-4o-mini")
        
        mock_model = AsyncMock()
        mock_model.ainvoke.side_effect = Exception("API Error")
        
        with patch.object(service, '_get_model', return_value=mock_model):
            with pytest.raises(RuntimeError) as exc_info:
                await service.generate(prompt="Test prompt")
        
        assert "LLM generation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_with_max_tokens(self):
        """Test generation with max_tokens parameter."""
        service = LLMService(provider="openai", model="gpt-4o-mini")
        
        mock_model = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "Short response"
        mock_model.ainvoke.return_value = mock_response
        
        with patch.object(service, '_get_model', return_value=mock_model):
            result = await service.generate(
                prompt="Test prompt",
                max_tokens=100,
            )
        
        assert result == "Short response"
        # Verify max_tokens was passed
        call_kwargs = mock_model.ainvoke.call_args[1]
        assert call_kwargs.get('max_tokens') == 100

    @pytest.mark.asyncio
    async def test_generate_with_fallback_success(self):
        """Test successful fallback to secondary provider."""
        service = LLMService(provider="openai", model="gpt-4")
        
        # Primary fails, fallback succeeds
        mock_primary = AsyncMock()
        mock_primary.ainvoke.side_effect = Exception("Primary API Error")
        
        mock_fallback = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "Fallback response"
        mock_fallback.ainvoke.return_value = mock_response
        
        with patch.object(service, '_get_model', return_value=mock_primary):
            with patch('mindflow_backend.services.llm.LLMService') as mock_fallback_class:
                mock_fallback_instance = MagicMock()
                mock_fallback_instance.generate = AsyncMock(return_value="Fallback response")
                mock_fallback_class.return_value = mock_fallback_instance
                
                result = await service.generate_with_fallback(
                    prompt="Test prompt",
                    fallback_provider="anthropic",
                    fallback_model="claude-3-haiku",
                )
        
        # Should get result from primary or fallback
        assert result is not None


class TestLLMServiceFactory:
    """Test LLM service factory functions."""

    def test_reset_llm_service(self):
        """Test reset_llm_service clears singleton."""
        reset_llm_service()
        
        service1 = get_llm_service()
        reset_llm_service()
        service2 = get_llm_service()
        
        # After reset, should be different instance
        assert service1 is not service2
        
        # Cleanup
        reset_llm_service()

    def test_get_llm_service_with_overrides(self):
        """Test factory with provider/model overrides."""
        reset_llm_service()
        
        service = get_llm_service(provider="anthropic", model="claude-3-opus")
        
        assert service._provider == "anthropic"
        assert service._model == "claude-3-opus"
        
        reset_llm_service()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
