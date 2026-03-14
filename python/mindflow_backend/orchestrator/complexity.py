"""Complexity scoring for orchestrator routing decisions."""

from __future__ import annotations

import re


_COMPLEX_PATTERNS = [
    r"\b(analise|analisa|compare|comparar|arquitetura|refactor|refatorar|implement|implemente)\b",
    r"\b(microservice|microservi[çc]o|sistema|plataforma|infraestrutura)\b",
    r"\b(pr[oó]s e contras|trade-?off|vantagens|desvantagens)\b",
    r"\b(multi|v[aá]rios|m[úu]ltiplos|complex|completo)\b",
    r"\?(.*\?){1,}",  # multiple question marks
]
_SIMPLE_PATTERNS = [
    r"^(ol[aá]|oi|hey|hello|hi)\b",
    r"^(quem [eé] voc[eê]|o que [eé] isso)",
    r"^\w{1,30}\??$",  # very short single-word queries
]

_DECOMPOSE_THRESHOLD = 0.7


class ComplexityScorer:
    """Heuristic complexity scorer for routing messages to appropriate agents."""

    async def get_complexity_score(
        self,
        message: str,
        provider: str | None = None,
        model: str | None = None,
    ) -> float:
        """Score message complexity between 0.0 (simple) and 1.0 (complex).

        Uses lightweight heuristics so it never requires an LLM call.
        """
        text = message.lower().strip()

        # Short messages are simple
        words = text.split()
        if len(words) <= 5:
            return 0.2

        # Check simple patterns first
        for pattern in _SIMPLE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return 0.2

        score = 0.3  # base score for non-trivial messages

        # Length bonus
        score += min(len(words) / 100, 0.2)

        # Complex keyword bonus
        for pattern in _COMPLEX_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                score += 0.1

        return min(score, 1.0)

    def should_decompose(self, score: float) -> bool:
        """Return True if complexity warrants task decomposition."""
        return score >= _DECOMPOSE_THRESHOLD
