"""Common prompt utilities and preamble for agent personalities."""

from __future__ import annotations

MINDFLOW_PREAMBLE = (
    "You are MindFlow, an advanced AI assistant with specialized capabilities. "
    "You are precise, reliable, and action-oriented. "
    "Always ground your answers in facts and evidence."
)


def build_system_prompt(personality_prompt: str) -> str:
    """Combine the MindFlow preamble with a personality-specific prompt."""
    return f"{MINDFLOW_PREAMBLE}\n\n{personality_prompt}"
