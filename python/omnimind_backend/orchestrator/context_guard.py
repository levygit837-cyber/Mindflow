"""No-raw-context payload guard.

Rejects oversized payloads from explorer agents (Analyst, Researcher)
before they reach the orchestrator context window.
"""

from __future__ import annotations

_CHARS_PER_TOKEN = 4


class PayloadTooLargeError(ValueError):
    """Raised when a payload exceeds the maximum token limit."""


def estimate_tokens(text: str) -> int:
    """Estimate token count from character length."""
    return len(text) // _CHARS_PER_TOKEN


def validate_payload_size(
    payload: str,
    max_tokens: int = 1000,
) -> None:
    """Reject payloads that exceed the token limit.

    Args:
        payload: Text content to validate.
        max_tokens: Maximum allowed tokens (default: 1000).

    Raises:
        PayloadTooLargeError: If payload exceeds max_tokens.
    """
    tokens = estimate_tokens(payload)
    if tokens > max_tokens:
        raise PayloadTooLargeError(
            f"Payload has ~{tokens} tokens, exceeds limit of {max_tokens}. "
            "Please re-summarize before sending to orchestrator."
        )