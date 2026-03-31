"""Shared Retrieval Algorithms.

Algoritmos genéricos de recuperação de contexto para suporte a:
- Busca semântica por similaridade de cosseno
- Busca híbrida combinando múltiplas estratégias
- Ranking e reordenação de resultados
- Otimizações de performance e caching
"""

from .context import ContextRetriever
from .ranking import ResultRanker
from .semantic import SemanticRetriever

__all__ = [
    "SemanticRetriever",
    "ContextRetriever",
    "ResultRanker",
]
