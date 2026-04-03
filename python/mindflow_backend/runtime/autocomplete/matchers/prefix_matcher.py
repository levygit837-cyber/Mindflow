"""Prefix matcher for autocomplete suggestions.

Provides exact prefix matching with scoring.
"""

from __future__ import annotations


def prefix_match(query: str, candidate: str) -> float:
    """Match por prefixo exato.

    Args:
        query: Texto de busca do usuário
        candidate: Candidato a ser comparado

    Returns:
        Score entre 0.0 (sem match) e 1.0 (match perfeito)

    Example:
        >>> prefix_match("/hel", "/help")
        0.8
        >>> prefix_match("/help", "/help")
        1.0
        >>> prefix_match("/xyz", "/help")
        0.0
    """
    if not query or not candidate:
        return 0.0

    query_lower = query.lower()
    candidate_lower = candidate.lower()

    # Match exato
    if query_lower == candidate_lower:
        return 1.0

    # Prefix match
    if candidate_lower.startswith(query_lower):
        # Score baseado na proporção de caracteres matched
        return 0.5 + (len(query_lower) / len(candidate_lower)) * 0.5

    return 0.0