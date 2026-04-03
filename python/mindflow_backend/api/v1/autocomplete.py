"""Autocomplete API endpoints.

Provides REST API for the autocomplete system.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.runtime.autocomplete.engine import (
    AutocompleteEngine,
    AutocompleteRequest,
    AutocompleteResponse,
    Suggestion,
    SuggestionCategory,
)
from mindflow_backend.runtime.autocomplete.providers.command_provider import CommandProvider
from mindflow_backend.runtime.autocomplete.providers.file_provider import FileProvider
from mindflow_backend.runtime.autocomplete.providers.tool_provider import ToolProvider
from mindflow_backend.runtime.autocomplete.providers.history_provider import HistoryProvider

_logger = get_logger(__name__)

router = APIRouter(prefix="/autocomplete", tags=["autocomplete"])


# Singleton engine instance
_engine: AutocompleteEngine | None = None


def get_autocomplete_engine() -> AutocompleteEngine:
    """Retorna instância singleton do engine de autocomplete."""
    global _engine
    if _engine is None:
        _engine = AutocompleteEngine()
        _engine.register_provider(CommandProvider())
        _engine.register_provider(FileProvider())
        _engine.register_provider(ToolProvider())
        _engine.register_provider(HistoryProvider())
        _logger.info("autocomplete_engine_initialized")
    return _engine


class SuggestionItem(BaseModel):
    """Modelo de sugestão na response."""
    text: str
    display_text: str
    description: str
    category: str
    score: float


class AutocompleteRequestBody(BaseModel):
    """Request body para o endpoint de autocomplete."""
    input_text: str = Field(..., description="Texto digitado pelo usuário")
    cursor_position: int = Field(default=0, description="Posição do cursor")
    session_id: str = Field(default="", description="ID da sessão")
    mode: str = Field(default="chat", description="Modo atual")


class AutocompleteResponseBody(BaseModel):
    """Response body do endpoint de autocomplete."""
    suggestions: list[SuggestionItem]
    latency_ms: int


@router.post("", response_model=AutocompleteResponseBody)
async def autocomplete(request: AutocompleteRequestBody) -> AutocompleteResponseBody:
    """Retorna sugestões de autocomplete.

    POST /api/v1/autocomplete

    Request:
    {
        "input_text": "/hel",
        "cursor_position": 4,
        "session_id": "abc123",
        "mode": "chat"
    }

    Response:
    {
        "suggestions": [
            {
                "text": "/help",
                "display_text": "/help",
                "description": "Show help information",
                "category": "command",
                "score": 1.0
            }
        ],
        "latency_ms": 12
    }
    """
    try:
        engine = get_autocomplete_engine()

        autocomplete_request = AutocompleteRequest(
            input_text=request.input_text,
            cursor_position=request.cursor_position,
            session_id=request.session_id,
            mode=request.mode,
        )

        response = await engine.suggest(autocomplete_request)

        return AutocompleteResponseBody(
            suggestions=[
                SuggestionItem(
                    text=s.text,
                    display_text=s.display_text,
                    description=s.description,
                    category=s.category.value,
                    score=s.score,
                )
                for s in response.suggestions
            ],
            latency_ms=response.latency_ms,
        )

    except Exception as e:
        _logger.error("autocomplete_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def autocomplete_health() -> dict[str, str]:
    """Health check do sistema de autocomplete."""
    return {"status": "healthy", "module": "autocomplete"}