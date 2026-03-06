"""Token estimation utilities."""

import math


def estimate_token_count(text: str) -> int:
    """Fast token estimate (~4 chars per token)."""
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))
