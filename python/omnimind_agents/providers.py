from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_PROVIDER = "vertexai"
DEFAULT_MODEL = "gemini-3-flash-preview"


def _get_vertex_project_id() -> Optional[str]:
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("VERTEXAI_CREDENTIALS_PATH")
    if not credentials_path:
        return None

    try:
        raw = Path(credentials_path).read_text(encoding="utf-8")
        parsed = json.loads(raw)
        return parsed.get("project_id")
    except Exception:
        return None


def _get_vertex_location(model: str) -> str:
    if model.startswith("gemini-3"):
        return "global"
    return "us-central1"


def ensure_vertex_env() -> None:
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("VERTEXAI_CREDENTIALS_PATH")
    if credentials_path and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS") and Path(credentials_path).exists():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

    project_id = _get_vertex_project_id()
    if project_id:
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
        os.environ.setdefault("GCLOUD_PROJECT", project_id)


def get_model_for_provider(provider: str, model: str, options: Optional[Dict[str, Any]] = None) -> Any:
    """Best-effort provider loader for Python LangChain ecosystem.

    This keeps parity with the TS provider matrix while failing fast with clear
    import guidance when optional dependencies are missing.
    """
    options = options or {}

    if provider == "vertexai":
        ensure_vertex_env()
        try:
            from langchain_google_vertexai import ChatVertexAI
        except ImportError as exc:
            raise RuntimeError("Missing dependency: pip install langchain-google-vertexai") from exc
        return ChatVertexAI(
            model=model,
            location=_get_vertex_location(model),
            api_key=options.get("api_key") or os.getenv("API_KEY") or os.getenv("GOOGLE_API_KEY"),
        )

    if provider == "google":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as exc:
            raise RuntimeError("Missing dependency: pip install langchain-google-genai") from exc
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=options.get("api_key") or os.getenv("GOOGLE_API_KEY"),
        )

    if provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError as exc:
            raise RuntimeError("Missing dependency: pip install langchain-anthropic") from exc
        return ChatAnthropic(
            model=model,
            anthropic_api_key=options.get("api_key") or os.getenv("ANTHROPIC_API_KEY"),
        )

    if provider == "openai":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise RuntimeError("Missing dependency: pip install langchain-openai") from exc
        return ChatOpenAI(
            model=model,
            api_key=options.get("api_key") or os.getenv("OPENAI_API_KEY"),
        )

    if provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
        except ImportError as exc:
            raise RuntimeError("Missing dependency: pip install langchain-ollama") from exc
        return ChatOllama(
            model=model,
            base_url=options.get("base_url") or os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434",
        )

    raise ValueError(f"Unknown provider: {provider}")
