"""Tests for ProviderService."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from mindflow_backend.services.core.provider_service import ProviderService


class TestProviderService:
    """Test suite for ProviderService."""

    @pytest.mark.asyncio
    async def test_google_provider_config_exposes_only_supported_models(self):
        """Google provider should expose only the supported Gemini 3.1 models."""
        service = ProviderService()
        service._get_cached_connection_status = AsyncMock(return_value={"overall_status": "active"})

        config = await service.get_provider_config("google")
        model_ids = [model["id"] for model in config["models"]]

        assert model_ids == [
            "gemini-3.1-flash-lite-preview",
            "gemini-3.1-pro-preview",
            "gemini-3.1-pro-preview-customtools",
        ]
