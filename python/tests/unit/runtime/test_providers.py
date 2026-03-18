from types import SimpleNamespace

import pytest

from mindflow_backend.runtime.providers import providers as provider_impl


class _PrimaryFailureModel:
    async def ainvoke(self, _messages):
        raise RuntimeError("primary failed")


class _FallbackModel:
    async def ainvoke(self, _messages):
        return "fallback-ok"


def _settings_stub(**overrides):
    base = {
        "google_api_key": None,
        "google_application_credentials": None,
        "vertexai_credentials_path": None,
        "google_cloud_project": None,
        "anthropic_api_key": None,
        "openai_api_key": None,
        "ollama_base_url": "http://localhost:11434",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_vertex_api_key_path_falls_back_to_service_account(monkeypatch) -> None:
    monkeypatch.setattr(provider_impl, "get_settings", lambda: _settings_stub(google_api_key="api-key"))
    monkeypatch.setattr(provider_impl, "_ensure_vertex_env", lambda: ("/tmp/serviceaccount.json", "demo-project"))
    monkeypatch.setattr(provider_impl, "_build_vertex_api_key_model", lambda **_kwargs: _PrimaryFailureModel())
    monkeypatch.setattr(provider_impl, "_build_vertex_service_account_model", lambda **_kwargs: _FallbackModel())

    model = provider_impl.get_model_for_provider("vertexai", "gemini-3-flash-preview")
    result = await model.ainvoke(["hello"])
    assert result == "fallback-ok"


def test_vertex_requires_api_key_or_service_account(monkeypatch) -> None:
    monkeypatch.setattr(provider_impl, "get_settings", _settings_stub)
    monkeypatch.setattr(provider_impl, "_ensure_vertex_env", lambda: (None, None))

    with pytest.raises(ValueError):
        provider_impl.get_model_for_provider("vertexai", "gemini-3-flash-preview")


def test_vertex_provider_uses_google_genai_vertex_mode(monkeypatch) -> None:
    import langchain_google_genai

    captured: dict[str, object] = {}

    class FakeModel:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(provider_impl, "get_settings", _settings_stub)
    monkeypatch.setattr(provider_impl, "_ensure_vertex_env", lambda: (None, "demo-project"))
    monkeypatch.setattr(langchain_google_genai, "ChatGoogleGenerativeAI", FakeModel)

    provider_impl.get_model_for_provider("vertexai", "gemini-3-flash-preview", api_key="api-key")

    assert captured["vertexai"] is True
    assert captured["model"] == "gemini-3-flash-preview"
    assert captured["include_thoughts"] is True
    assert captured["thinking_level"] == "high"


def test_removed_codex_provider_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr(provider_impl, "get_settings", _settings_stub)

    with pytest.raises(ValueError, match="Unknown provider: codex"):
        provider_impl.get_model_for_provider("codex", "gpt-5.4")


def test_ollama_tool_binding_raises_clear_error_for_unsupported_model(monkeypatch) -> None:
    monkeypatch.setattr(provider_impl, "get_settings", _settings_stub)

    with pytest.raises(provider_impl.ModelCapabilityError, match="does not support tools"):
        provider_impl.ensure_tools_supported("ollama", "orch:latest", tools_required=True)


def test_ollama_tool_binding_selects_tool_capable_fallback_model(monkeypatch) -> None:
    monkeypatch.setattr(provider_impl, "get_settings", _settings_stub)

    provider, model = provider_impl.resolve_provider_model_for_tools(
        "ollama",
        "orch:latest",
        tools_required=True,
    )

    assert provider == "ollama"
    assert model == "qwen3:8b"
