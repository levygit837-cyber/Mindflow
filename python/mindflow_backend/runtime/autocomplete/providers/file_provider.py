"""File Provider for Autocomplete.

Sugere caminhos de arquivo após @ ou / com suporte a navegação de diretórios.
"""

from __future__ import annotations

import os
from pathlib import Path

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.runtime.autocomplete.engine import (
    AutocompleteRequest,
    Suggestion,
    SuggestionCategory,
)
from mindflow_backend.runtime.autocomplete.matchers.fuzzy_matcher import fuzzy_match

_logger = get_logger(__name__)


class FileProvider:
    """Provider de arquivos e diretórios.

    Sugere caminhos de arquivo quando o input contém @ ou /filepath.
    Suporta navegação de diretórios e indica se é arquivo ou diretório.

    Usage:
        provider = FileProvider(root_path="/home/user/project")
        suggestions = await provider.get_suggestions(
            AutocompleteRequest(input_text="@src/ma")
        )
    """

    def __init__(
        self,
        root_path: str | None = None,
        max_depth: int = 5,
        max_results: int = 20,
    ) -> None:
        self._root = Path(root_path or os.getcwd())
        self._max_depth = max_depth
        self._max_results = max_results

    def _extract_path_query(self, input_text: str) -> str | None:
        """Extrai query de caminho do input.

        Detecta padrões como:
        - @path/to/file
        - /path/to/file
        - path/to/file (se começar com ./ ou ../)
        """
        text = input_text.strip()

        # Padrão @path
        if "@" in text:
            idx = text.rfind("@")
            return text[idx + 1 :]

        # Padrão /path (absoluto)
        if text.startswith("/"):
            return text

        # Padrão relativo
        if text.startswith("./") or text.startswith("../"):
            return text

        return None

    async def get_suggestions(
        self, request: AutocompleteRequest
    ) -> list[Suggestion]:
        """Retorna sugestões de arquivos baseadas no input."""
        path_query = self._extract_path_query(request.input_text)
        if path_query is None:
            return []

        try:
            return self._list_path_suggestions(path_query)
        except Exception as e:
            _logger.debug(
                "file_provider_error",
                query=path_query,
                error=str(e),
            )
            return []

    def _list_path_suggestions(self, query: str) -> list[Suggestion]:
        """Lista sugestões de caminho para uma query."""
        suggestions: list[Suggestion] = []

        # Determinar diretório de busca e prefixo
        if "/" in query:
            dir_part = query.rsplit("/", 1)[0]
            prefix = query.rsplit("/", 1)[1]
        else:
            dir_part = ""
            prefix = query

        # Resolver caminho do diretório
        if dir_part:
            search_dir = self._root / dir_part
        else:
            search_dir = self._root

        if not search_dir.is_dir():
            return []

        # Listar conteúdo do diretório
        try:
            entries = list(search_dir.iterdir())
        except PermissionError:
            return []

        for entry in entries:
            name = entry.name

            # Pular arquivos ocultos
            if name.startswith("."):
                continue

            # Calcular score
            score = fuzzy_match(prefix.lower(), name.lower())
            if score < 0.3:
                continue

            # Construir caminho de exibição
            if dir_part:
                display_path = f"{dir_part}/{name}"
            else:
                display_path = name

            # Indicar se é diretório
            if entry.is_dir():
                display_path += "/"
                description = "Directory"
            else:
                description = f"File ({entry.stat().st_size} bytes)"

            suggestions.append(
                Suggestion(
                    text=f"@{display_path}",
                    display_text=display_path,
                    description=description,
                    category=SuggestionCategory.FILE,
                    score=score,
                    metadata={"path": str(entry), "is_dir": entry.is_dir()},
                )
            )

        # Ordenar: diretórios primeiro, depois por score
        suggestions.sort(
            key=lambda s: (not s.metadata.get("is_dir", False), -s.score)
        )

        return suggestions[: self._max_results]