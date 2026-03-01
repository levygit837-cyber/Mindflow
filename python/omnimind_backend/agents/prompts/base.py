"""Common prompt utilities and preamble for agent personalities."""

from __future__ import annotations

OMNIMIND_PREAMBLE = (
    "You are OmniMind, an advanced AI assistant with specialized capabilities. "
    "You are precise, reliable, and action-oriented. "
    "Always ground your answers in facts and evidence."
)


def build_system_prompt(personality_prompt: str) -> str:
    """Combine the OmniMind preamble with a personality-specific prompt."""
    return f"{OMNIMIND_PREAMBLE}\n\n{personality_prompt}"
