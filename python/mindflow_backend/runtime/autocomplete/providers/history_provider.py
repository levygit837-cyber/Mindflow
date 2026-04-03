"""History Provider for Autocomplete.

Sugere comandos do histórico de sessão, ordenados por recência
com deduplicação automática.
"""

from __future__ import annotations

from collections import defaultdict

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.runtime.autocomplete.engine import (
    AutocompleteRequest,
    Suggestion,
    SuggestionCategory,
)
from mindflow_backend.runtime.autocomplete.matchers.fuzzy_matcher import fuzzy_match

_logger = get_logger(__name__)


class HistoryProvider:
    """Provider de histórico de comandos.

    Sugere comandos do histórico de sessão do usuário.
    Ordenado por recência com deduplicação automática.

    Usage:
        provider = HistoryProvider()
        provider.add_entry("session-1", "read file config.yaml")
        provider.add_entry("session-1", "run tests")

        suggestions = await provider.get_suggestions(
            AutocompleteRequest(input_text="read", session_id="session-1")
        )
    """

    def __init__(self, max_history_per_session: int = 100) -> None:
        self._max_history = max_history_per_session
        # session_id -> list of (input_text, timestamp)
        self._history: dict[str, list[tuple[str, float]]] = defaultdict(list)

    def add_entry(self, session_id: str, input_text: str, timestamp: float = 0) -> None:
        """Adiciona entrada ao histórico de uma sessão."""
        import time
        ts = timestamp or time.time()

        history = self._history[session_id]

        # Deduplicação - remove entrada anterior se existir
        history[:] = [(text, t) for text, t in history if text != input_text]

        # Adiciona no início (mais recente primeiro)
        history.insert(0, (input_text, ts))

        # Limitar tamanho
        if len(history) > self._max_history:
            self._history[session_id] = history[: self._max_history]

    def clear_session(self, session_id: str) -> None:
        """Limpa histórico de uma sessão."""
        self._history.pop(session_id, None)

    def clear_all(self) -> None:
        """Limpa todo o histórico."""
        self._history.clear()

    async def get_suggestions(
        self, request: AutocompleteRequest
    ) -> list[Suggestion]:
        """Retorna sugestões do histórico baseadas no input."""
        input_text = request.input_text.strip().lower()

        if not input_text or not request.session_id:
            return []

        history = self._history.get(request.session_id, [])
        if not history:
            return []

        suggestions: list[Suggestion] = []
        seen: set[str] = set()

        for hist_text, timestamp in history:
            if hist_text in seen:
                continue
            seen.add(hist_text)

            # Calcular score
            score = fuzzy_match(input_text, hist_text.lower())

            if score > 0.3:
                suggestions.append(
                    Suggestion(
                        text=hist_text,
                        display_text=hist_text,
                        description="From history",
                        category=SuggestionCategory.HISTORY,
                        score=score * 0.8,  # Score ligeiramente menor que outros providers
                        metadata={"timestamp": timestamp},
                    )
                )

        return suggestions