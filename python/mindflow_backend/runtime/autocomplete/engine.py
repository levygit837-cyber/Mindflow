"""Autocomplete Engine for MindFlow.

Central engine that coordinates suggestion providers and returns
ranked suggestions to the user.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class SuggestionCategory(str, Enum):
    """Categorias de sugestões."""
    COMMAND = "command"
    FILE = "file"
    TOOL = "tool"
    HISTORY = "history"


@dataclass
class Suggestion:
    """Uma sugestão de autocomplete.

    Attributes:
        text: Texto que será inserido se aceito
        display_text: Texto exibido na lista de sugestões
        description: Descrição da sugestão
        category: Categoria da sugestão
        score: Score de relevância (0.0 a 1.0)
        metadata: Metadados adicionais
    """
    text: str
    display_text: str = ""
    description: str = ""
    category: SuggestionCategory = SuggestionCategory.COMMAND
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.display_text:
            self.display_text = self.text


@dataclass
class AutocompleteRequest:
    """Request de autocomplete.

    Attributes:
        input_text: Texto digitado pelo usuário
        cursor_position: Posição do cursor no texto
        session_id: ID da sessão (para history)
        mode: Modo atual (chat, command, etc.)
    """
    input_text: str
    cursor_position: int = 0
    session_id: str = ""
    mode: str = "chat"


@dataclass
class AutocompleteResponse:
    """Response de autocomplete.

    Attributes:
        suggestions: Lista de sugestões ordenadas por score
        latency_ms: Latência da busca em milissegundos
    """
    suggestions: list[Suggestion] = field(default_factory=list)
    latency_ms: int = 0


class SuggestionProvider(Protocol):
    """Protocolo para providers de sugestão."""

    async def get_suggestions(
        self, request: AutocompleteRequest
    ) -> list[Suggestion]:
        """Retorna sugestões para o request dado."""
        ...


class AutocompleteEngine:
    """Engine central de autocomplete.

    Coordena múltiplos providers de sugestão e retorna
    resultados ranqueados ao usuário.

    Usage:
        engine = AutocompleteEngine()
        engine.register_provider(CommandProvider())
        engine.register_provider(FileProvider())

        response = await engine.suggest(AutocompleteRequest(
            input_text="/hel",
            cursor_position=4
        ))
    """

    def __init__(
        self,
        max_results: int = 10,
        min_score: float = 0.1,
    ) -> None:
        self._providers: list[SuggestionProvider] = []
        self._max_results = max_results
        self._min_score = min_score

    def register_provider(self, provider: SuggestionProvider) -> None:
        """Registra um provider de sugestão."""
        self._providers.append(provider)
        _logger.info(
            "autocomplete_provider_registered",
            provider=type(provider).__name__,
        )

    async def suggest(
        self, request: AutocompleteRequest
    ) -> AutocompleteResponse:
        """Retorna sugestões para o request dado.

        Coleta sugestões de todos os providers, deduplica,
        ordena por score e retorna os top N resultados.
        """
        start_time = time.time()

        # Coletar sugestões de todos os providers
        all_suggestions: list[Suggestion] = []
        for provider in self._providers:
            try:
                suggestions = await provider.get_suggestions(request)
                all_suggestions.extend(suggestions)
            except Exception as e:
                _logger.warning(
                    "autocomplete_provider_error",
                    provider=type(provider).__name__,
                    error=str(e),
                )

        # Deduplicar por texto
        seen: set[str] = set()
        unique: list[Suggestion] = []
        for s in all_suggestions:
            if s.text not in seen and s.score >= self._min_score:
                seen.add(s.text)
                unique.append(s)

        # Ordenar por score (decrescente)
        unique.sort(key=lambda s: s.score, reverse=True)

        # Limitar resultados
        top_suggestions = unique[: self._max_results]

        latency_ms = int((time.time() - start_time) * 1000)

        _logger.debug(
            "autocomplete_suggestions",
            input_text=request.input_text,
            total=len(all_suggestions),
            returned=len(top_suggestions),
            latency_ms=latency_ms,
        )

        return AutocompleteResponse(
            suggestions=top_suggestions,
            latency_ms=latency_ms,
        )