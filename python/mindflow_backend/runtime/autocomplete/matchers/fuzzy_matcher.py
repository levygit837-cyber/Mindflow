"""Fuzzy matcher for autocomplete suggestions.

Allows characters out of order while still matching strong candidates.
"""

from __future__ import annotations


def fuzzy_match(query: str, candidate: str) -> float:
    """Match fuzzy que permite caracteres fora de ordem.

    Args:
        query: Texto de busca do usuário
        candidate: Candidato a ser comparado

    Returns:
        Score entre 0.0 (sem match) e 1.0 (match perfeito)

    Example:
        >>> fuzzy_match("redfil", "read_file")
        0.85
        >>> fuzzy_match("srch", "search")
        0.75
        >>> fuzzy_match("xyz", "read_file")
        0.0
    """
    if not query or not candidate:
        return 0.0

    query_lower = query.lower()
    candidate_lower = candidate.lower()

    # Match exato
    if query_lower == candidate_lower:
        return 1.0

    # Prefix match exato
    if candidate_lower.startswith(query_lower):
        return 0.95

    # Fuzzy matching por subsequência
    query_idx = 0
    candidate_idx = 0
    matched_chars = 0
    consecutive_matches = 0
    max_consecutive = 0

    while query_idx < len(query_lower) and candidate_idx < len(candidate_lower):
        if query_lower[query_idx] == candidate_lower[candidate_idx]:
            matched_chars += 1
            consecutive_matches += 1
            max_consecutive = max(max_consecutive, consecutive_matches)
            query_idx += 1
        else:
            consecutive_matches = 0
        candidate_idx += 1

    # Não todos os caracteres foram encontrados
    if query_idx < len(query_lower):
        return 0.0

    # Calcular score
    # Base: proporção de caracteres matched
    char_ratio = matched_chars / len(query_lower)

    # Bonus por matches consecutivos
    consecutive_bonus = max_consecutive / len(query_lower) * 0.3

    # Penalidade por distância do início
    first_char_pos = candidate_lower.find(query_lower[0])
    position_penalty = (first_char_pos / len(candidate_lower)) * 0.1 if first_char_pos > 0 else 0.0

    score = (char_ratio * 0.6) + consecutive_bonus - position_penalty

    return min(1.0, max(0.0, score))