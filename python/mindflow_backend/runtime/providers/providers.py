from __future__ import annotations

import json
import os
from collections.abc import AsyncGenerator, Callable
from pathlib import Path
from typing import Any

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.core.common import LLMProvider

_logger = get_logger(__name__)


def _normalized(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _load_vertex_project_id(credentials_path: str | None) -> str | None:
    if not credentials_path:
        return None
    try:
        data = json.loads(Path(credentials_path).read_text(encoding="utf-8"))
        project_id = data.get("project_id")
        if isinstance(project_id, str):
            return _normalized(project_id)
    except Exception:
        return None
    return None


def _vertex_location(model: str) -> str:
    # Most thinking models are currently global or in specific US regions
    return "global" if "gemini-3" in model.lower() or "thinking" in model.lower() else "us-central1"


def _is_thinking_supported(model: str) -> bool:
    m = model.lower()
    return "thinking" in m or "gemini-2.0" in m or "gemini-3" in m


def _ensure_vertex_env() -> tuple[str | None, str | None]:
    settings = get_settings()

    credentials_path = (
        _normalized(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
        or _normalized(settings.google_application_credentials)
        or _normalized(settings.vertexai_credentials_path)
    )
    if credentials_path and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

    project_id = (
        _normalized(os.getenv("GOOGLE_CLOUD_PROJECT"))
        or _normalized(settings.google_cloud_project)
        or _load_vertex_project_id(credentials_path)
    )
    if project_id:
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
        os.environ.setdefault("GCLOUD_PROJECT", project_id)

    return credentials_path, project_id


def _build_vertex_service_account_model(*, model: str, project_id: str | None):
    from langchain_google_genai import ChatGoogleGenerativeAI

    kwargs: dict[str, Any] = {
        "model": model,
        "vertexai": True,
        "location": _vertex_location(model),
    }
    if project_id:
        kwargs["project"] = project_id
    if _is_thinking_supported(model):
        kwargs["include_thoughts"] = True
        kwargs["thinking_level"] = "high"
    return ChatGoogleGenerativeAI(**kwargs)


def _build_vertex_api_key_model(*, model: str, api_key: str, project_id: str | None):
    from langchain_google_genai import ChatGoogleGenerativeAI

    kwargs: dict[str, Any] = {
        "model": model,
        "google_api_key": api_key,
        "vertexai": True,
        "location": _vertex_location(model),
    }

    if project_id:
        kwargs["project"] = project_id
    if _is_thinking_supported(model):
        kwargs["include_thoughts"] = True
        kwargs["thinking_level"] = "high"
    return ChatGoogleGenerativeAI(**kwargs)


class _AinvokeFallbackModel:
    def __init__(self, *, primary_model: Any, fallback_factory: Callable[[], Any] | None) -> None:
        self._primary_model = primary_model
        self._fallback_factory = fallback_factory
        self._fallback_model: Any | None = None
        self._using_fallback = False

    def _get_active_model(self) -> Any:
        if self._using_fallback:
            if self._fallback_model is None:
                if self._fallback_factory is None:
                    raise RuntimeError("Fallback model factory not configured")
                self._fallback_model = self._fallback_factory()
            return self._fallback_model
        return self._primary_model

    async def ainvoke(self, messages: Any, **kwargs: Any) -> Any:
        try:
            return await self._get_active_model().ainvoke(messages, **kwargs)
        except Exception as exc:
            if not self._using_fallback and self._fallback_factory:
                _logger.warning("vertex_api_key_fallback", error=str(exc))
                self._using_fallback = True
                return await self.ainvoke(messages, **kwargs)
            raise

    async def astream(self, messages: Any, **kwargs: Any) -> AsyncGenerator[Any, None]:
        try:
            async for chunk in self._get_active_model().astream(messages, **kwargs):
                yield chunk
        except Exception as exc:
            if not self._using_fallback and self._fallback_factory:
                _logger.warning("vertex_api_key_stream_fallback", error=str(exc))
                self._using_fallback = True
                async for chunk in self.astream(messages, **kwargs):
                    yield chunk
            else:
                raise

    async def astream_events(self, *args: Any, **kwargs: Any) -> AsyncGenerator[Any, None]:
        try:
            async for event in self._get_active_model().astream_events(*args, **kwargs):
                yield event
        except Exception as exc:
            if not self._using_fallback and self._fallback_factory:
                _logger.warning("vertex_api_key_astream_events_fallback", error=str(exc))
                self._using_fallback = True
                async for event in self.astream_events(*args, **kwargs):
                    yield event
            else:
                raise

    def bind_tools(self, tools: Any, **kwargs: Any) -> _AinvokeFallbackModel:
        # Wrap the models with tools bound
        primary_with_tools = self._primary_model.bind_tools(tools, **kwargs)
        
        fallback_factory_with_tools: Callable[[], Any] | None = None
        if self._fallback_factory:
            def _factory():
                return self._fallback_factory().bind_tools(tools, **kwargs)
            fallback_factory_with_tools = _factory
            
        return _AinvokeFallbackModel(
            primary_model=primary_with_tools,
            fallback_factory=fallback_factory_with_tools
        )


def get_model_for_provider(
    provider: LLMProvider,
    model: str,
    api_key: str | None = None,
    base_url: str | None = None,
):
    settings = get_settings()

    if provider == "vertexai":
        credentials_path, project_id = _ensure_vertex_env()
        # Final effort to find API key
        google_api_key = api_key or settings.google_api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_CLOUD_API_KEY")

        def _fallback_factory() -> Any:
            return _build_vertex_service_account_model(
                model=model,
                project_id=project_id,
            )

        fallback_factory: Callable[[], Any] | None = None
        if credentials_path:
            fallback_factory = _fallback_factory

        if google_api_key:
            primary_model = _build_vertex_api_key_model(
                model=model,
                api_key=google_api_key,
                project_id=project_id,
            )
            return _AinvokeFallbackModel(
                primary_model=primary_model,
                fallback_factory=fallback_factory,
            )

        if fallback_factory:
            return fallback_factory()

        raise ValueError(
            "Vertex AI auth missing: set GOOGLE_API_KEY/GOOGLE_CLOUD_API_KEY, or configure "
            "GOOGLE_APPLICATION_CREDENTIALS/VERTEXAI_CREDENTIALS_PATH."
        )

    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        # Final effort to find API key
        google_api_key = api_key or settings.google_api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

        kwargs = {
            "model": model,
            "google_api_key": google_api_key,
        }
        
        if _is_thinking_supported(model):
            kwargs["thinking_config"] = {"include_thoughts": True, "thinking_level": "HIGH"}
            
        return ChatGoogleGenerativeAI(**kwargs)

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        kwargs = {
            "model": model,
            "anthropic_api_key": api_key or settings.anthropic_api_key,
        }
        return ChatAnthropic(**kwargs)

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=model, api_key=api_key or settings.openai_api_key)

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=model,
            base_url=base_url or settings.ollama_base_url,
        )

    if provider == "codex":
        from langchain_openai import ChatOpenAI
        
        # CodeX uses OpenAI-compatible API with custom base URL
        codex_base_url = os.getenv("CODEX_API_URL", "https://api.openai.com/v1")
        codex_api_key = api_key or os.getenv("CODEX_API_KEY")
        codex_organization = os.getenv("CODEX_ORGANIZATION")  # Business account support
        
        if not codex_api_key:
            raise ValueError("CODEX_API_KEY environment variable is required for CodeX provider")
            
        kwargs = {
            "model": model,
            "api_key": codex_api_key,
            "base_url": codex_base_url,
            "timeout": 60,
            "max_retries": 3,
        }
        
        # Add organization for business accounts
        if codex_organization:
            kwargs["organization"] = codex_organization
            _logger.info("codex_organization_configured", organization=codex_organization)
        
        # Use CodeX 5.4 as default model if not specified
        if model == "default" or model == "codex":
            kwargs["model"] = "gpt-5.4"
        
        _logger.info(
            "codex_provider_initialized",
            model=kwargs["model"],
            base_url=codex_base_url,
            organization=codex_organization or "none"
        )
        
        return ChatOpenAI(**kwargs)

    raise ValueError(f"Unknown provider: {provider}")
