"""Unit tests for the canonical embedding provider factory."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from mindflow_backend.memory.shared.embeddings.factory import (
    EmbeddingBackend,
    EmbeddingProviderFactory,
    OllamaProvider,
)


def test_factory_defaults_to_ollama_nomic_embed_v2_moe() -> None:
    settings = SimpleNamespace(
        embedding_backend="ollama",
        embedding_model_name="nomic-embed-text-v2-moe:latest",
        embedding_dims=768,
        ollama_base_url="http://localhost:11434",
        google_api_key=None,
    )

    with patch("mindflow_backend.infra.config.get_settings", return_value=settings):
        provider = EmbeddingProviderFactory.from_settings()

    assert isinstance(provider, OllamaProvider)
    assert provider.backend() == EmbeddingBackend.OLLAMA
    assert provider.dimension() == 768
    assert provider._model_name == "nomic-embed-text-v2-moe:latest"


@pytest.mark.asyncio
async def test_validate_ollama_embedding_provider_checks_capability_and_dims() -> None:
    provider = EmbeddingProviderFactory.create(
        EmbeddingBackend.OLLAMA,
        model_name="nomic-embed-text-v2-moe:latest",
        dims=768,
        base_url="http://localhost:11434",
    )

    with patch(
        "mindflow_backend.memory.shared.embeddings.factory._probe_ollama_model",
        return_value=(True, None),
    ) as probe:
        health = await EmbeddingProviderFactory.validate_provider(provider)

    assert health.is_healthy is True
    assert health.backend == "ollama"
    assert health.model == "nomic-embed-text-v2-moe:latest"
    probe.assert_awaited_once()
