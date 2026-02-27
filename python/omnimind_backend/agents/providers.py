import json
import os
from pathlib import Path

from omnimind_backend.infra.config import get_settings
from omnimind_backend.schemas.common import LLMProvider


def _load_vertex_project_id(credentials_path: str | None) -> str | None:
    if not credentials_path:
        return None
    try:
        data = json.loads(Path(credentials_path).read_text(encoding="utf-8"))
        return data.get("project_id")
    except Exception:
        return None


def _ensure_vertex_env() -> None:
    settings = get_settings()
    credentials_path = (
        settings.google_application_credentials or settings.vertexai_credentials_path
    )
    if credentials_path and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

    project_id = _load_vertex_project_id(credentials_path)
    if project_id:
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
        os.environ.setdefault("GCLOUD_PROJECT", project_id)


def get_model_for_provider(
    provider: LLMProvider,
    model: str,
    api_key: str | None = None,
    base_url: str | None = None,
):
    settings = get_settings()

    if provider == "vertexai":
        _ensure_vertex_env()
        from langchain_google_vertexai import ChatVertexAI

        kwargs = {
            "model": model,
            "location": "global" if model.startswith("gemini-3") else "us-central1",
            "reasoning_effort": "high",
        }
        if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            kwargs["api_key"] = api_key or settings.google_api_key
        return ChatVertexAI(**kwargs)

    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key or settings.google_api_key,
            thinking_config={"include_thoughts": True, "thinking_level": "HIGH"},
        )

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

    raise ValueError(f"Unknown provider: {provider}")
