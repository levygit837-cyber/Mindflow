from types import SimpleNamespace

import pytest

from mindflow_backend.runtime import providers


class _PrimaryFailureModel:
    async def ainvoke(self, _messages):
        raise RuntimeError("primary failed")


class _FallbackModel:
    async def ainvoke(self, _messages):
        return "fallback-ok"


@pytest.mark.asyncio
async def test_vertex_api_key_path_falls_back_to_service_account(monkeypatch) -> None:
    monkeypatch.setattr(
        providers,
        "get_settings",
        lambda: SimpleNamespace(
            google_api_key="api-key",
            google_application_credentials=None,
            vertexai_credentials_path=None,
            google_cloud_project=None,
            anthropic_api_key=None,
            openai_api_key=None,
            ollama_base_url="http://localhost:11434",
        ),
    )
    monkeypatch.setattr(providers, "_ensure_vertex_env", lambda: ("/tmp/serviceaccount.json", "demo-project"))
    monkeypatch.setattr(providers, "_build_vertex_api_key_model", lambda **_kwargs: _PrimaryFailureModel())
    monkeypatch.setattr(providers, "_build_vertex_service_account_model", lambda **_kwargs: _FallbackModel())

    model = providers.get_model_for_provider("vertexai", "gemini-3-flash-preview")
    result = await model.ainvoke(["hello"])
    assert result == "fallback-ok"


def test_vertex_requires_api_key_or_service_account(monkeypatch) -> None:
    monkeypatch.setattr(
        providers,
        "get_settings",
        lambda: SimpleNamespace(
            google_api_key=None,
            google_application_credentials=None,
            vertexai_credentials_path=None,
            google_cloud_project=None,
            anthropic_api_key=None,
            openai_api_key=None,
            ollama_base_url="http://localhost:11434",
        ),
    )
    monkeypatch.setattr(providers, "_ensure_vertex_env", lambda: (None, None))

    with pytest.raises(ValueError):
        providers.get_model_for_provider("vertexai", "gemini-3-flash-preview")


def test_vertex_provider_uses_google_genai_vertex_mode(monkeypatch) -> None:
    import langchain_google_genai

    captured: dict[str, object] = {}

    class FakeModel:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(
        providers,
        "get_settings",
        lambda: SimpleNamespace(
            google_api_key=None,
            google_application_credentials=None,
            vertexai_credentials_path=None,
            google_cloud_project=None,
            anthropic_api_key=None,
            openai_api_key=None,
            ollama_base_url="http://localhost:11434",
        ),
    )
    monkeypatch.setattr(providers, "_ensure_vertex_env", lambda: (None, "demo-project"))
    monkeypatch.setattr(langchain_google_genai, "ChatGoogleGenerativeAI", FakeModel)

    providers.get_model_for_provider("vertexai", "gemini-3-flash-preview", api_key="api-key")

    assert captured["vertexai"] is True
    assert captured["model"] == "gemini-3-flash-preview"
    assert captured["include_thoughts"] is True
    assert captured["thinking_level"] == "high"
