"""Input normalization layer (between L2 sanitizer and L3 prompt guard).

Applies rule-based noise removal, repetition collapse, and optional
LLM-assisted rewrite for complex messages.
"""

from __future__ import annotations

import re

from mindflow_backend.schemas.config.normalization import NormalizationConfig

_DEFAULT_CONFIG = NormalizationConfig()

# Patterns for excessive punctuation
_EXCESS_EXCLAIM = re.compile(r"!{2,}")
_EXCESS_QUESTION = re.compile(r"\?{2,}")
_EXCESS_DOT = re.compile(r"\.{4,}")
_EXCESS_SPACES = re.compile(r"[ \t]{2,}")
_EXCESS_NEWLINES = re.compile(r"\n{3,}")

# Filler phrases to strip
_FILLER_PHRASES = [
    r"\bbasically\b,?\s*",
    r"\byou know\b,?\s*",
    r"\bI just\b\s+",
    r"\bWell,\s+",
    r"\blike,\s+",
    r"\bI mean,?\s*",
    r"\bactually,?\s+",
    r"\bso,?\s+(?=I )",
]
_FILLER_RE = re.compile("|".join(_FILLER_PHRASES), re.IGNORECASE)

# Code block regex
_CODE_BLOCK_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)


def _extract_code_blocks(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Replace code blocks with placeholders, return mapping."""
    blocks: list[tuple[str, str]] = []
    counter = 0

    def _replace(m: re.Match) -> str:
        nonlocal counter
        placeholder = f"__CODE_BLOCK_{counter}__"
        blocks.append((placeholder, m.group(0)))
        counter += 1
        return placeholder

    cleaned = _CODE_BLOCK_RE.sub(_replace, text)
    return cleaned, blocks


def _restore_code_blocks(text: str, blocks: list[tuple[str, str]]) -> str:
    """Restore code blocks from placeholders."""
    for placeholder, original in blocks:
        text = text.replace(placeholder, original)
    return text


def _apply_noise_removal(text: str) -> str:
    """Apply rule-based noise removal."""
    text = _EXCESS_EXCLAIM.sub("!", text)
    text = _EXCESS_QUESTION.sub("?", text)
    text = _EXCESS_DOT.sub("...", text)
    text = _EXCESS_SPACES.sub(" ", text)
    text = _EXCESS_NEWLINES.sub("\n\n", text)
    text = _FILLER_RE.sub("", text)
    return text.strip()


def _collapse_repetitions(text: str) -> str:
    """Detect and collapse repeated sentences."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    if len(sentences) <= 1:
        return text

    seen: dict[str, int] = {}
    result_parts: list[str] = []

    for sentence in sentences:
        normalized = sentence.strip().lower()
        if normalized in seen:
            seen[normalized] += 1
        else:
            seen[normalized] = 1
            result_parts.append(sentence)

    # Add repetition annotations
    final_parts: list[str] = []
    for part in result_parts:
        count = seen.get(part.strip().lower(), 1)
        if count > 1:
            final_parts.append(f"{part} [repeated {count} times]")
        else:
            final_parts.append(part)

    return " ".join(final_parts)


def normalize_message(
    text: str,
    config: NormalizationConfig | None = None,
) -> str:
    """Normalize user input for improved LLM comprehension.

    Args:
        text: Input text (already passed through L2 sanitizer).
        config: Normalization configuration. Uses defaults if None.

    Returns:
        Normalized text with noise removed and code blocks preserved.
    """
    cfg = config or _DEFAULT_CONFIG

    if not cfg.enabled:
        return text

    # Protect code blocks from normalization
    if cfg.preserve_code_blocks:
        text, blocks = _extract_code_blocks(text)
    else:
        blocks = []

    text = _apply_noise_removal(text)
    text = _collapse_repetitions(text)

    # Restore code blocks
    if blocks:
        text = _restore_code_blocks(text, blocks)

    return text
