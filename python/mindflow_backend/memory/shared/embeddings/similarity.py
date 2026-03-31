"""Similarity calculations for embeddings."""

import math


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


def euclidean_distance(a: list[float], b: list[float]) -> float:
    """Calculate Euclidean distance between two vectors."""
    if not a or not b or len(a) != len(b):
        return float('inf')
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def manhattan_distance(a: list[float], b: list[float]) -> float:
    """Calculate Manhattan distance between two vectors."""
    if not a or not b or len(a) != len(b):
        return float('inf')
    return sum(abs(x - y) for x, y in zip(a, b))
