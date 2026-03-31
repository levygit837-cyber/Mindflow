"""Classification and hygiene helpers for semantic memory indexing."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

_CONTINUATION_PATTERNS = (
    r"\bretom",
    r"\bcontinue\b",
    r"\bcontinuar\b",
    r"\bsess[aã]o anterior\b",
    r"\bcomo antes\b",
    r"\brelemb",
    r"\bdecis[aã]o anterior\b",
    r"\bo que fizemos\b",
)
_PLACEHOLDER_PATTERNS = (
    r"<marker>.*?</marker>",
    r"\bplaceholder\b",
    r"\btodo\b",
    r"\bno response generated\b",
    r"\bcomo posso ajudar\?\b",
)
_TOOL_ERROR_PATTERNS = (
    r"\berro\b",
    r"\bexception\b",
    r"\btraceback\b",
    r"\bfailed\b",
    r"\bnot found\b",
    r"\bgitnexus\b",
)


@dataclass(slots=True)
class MemoryIndexingDecision:
    indexable: bool
    content_kind: str
    quality_flags: list[str] = field(default_factory=list)
    skipped_reasons: list[str] = field(default_factory=list)
    answer_bearing: bool = False
    derived_from_recall: bool = False


def normalize_text(text: str) -> str:
    lowered = (text or "").strip().lower()
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered


def normalized_lexical_similarity(left: str, right: str) -> float:
    left_norm = normalize_text(left)
    right_norm = normalize_text(right)
    if not left_norm or not right_norm:
        return 0.0
    return SequenceMatcher(None, left_norm, right_norm).ratio()


def is_continuation_prompt(text: str) -> bool:
    normalized = normalize_text(text)
    return any(re.search(pattern, normalized) for pattern in _CONTINUATION_PATTERNS)


def classify_memory_content(
    *,
    role: str,
    content: str,
    source_status: str = "final",
    derived_from_recall: bool = False,
    prompt_reference: str | None = None,
) -> MemoryIndexingDecision:
    normalized = normalize_text(content)
    flags: list[str] = []
    skipped: list[str] = []
    continuation = is_continuation_prompt(normalized)
    if continuation:
        derived_from_recall = True

    if not normalized:
        return MemoryIndexingDecision(
            indexable=False,
            content_kind="placeholder",
            quality_flags=["empty"],
            skipped_reasons=["empty_content"],
            derived_from_recall=derived_from_recall,
        )

    if role == "user":
        return MemoryIndexingDecision(
            indexable=True,
            content_kind="continuation_prompt" if continuation else "query",
            derived_from_recall=derived_from_recall,
        )

    if source_status == "partial":
        return MemoryIndexingDecision(
            indexable=False,
            content_kind="answer",
            quality_flags=["partial_stream"],
            skipped_reasons=["partial_stream"],
            derived_from_recall=derived_from_recall,
        )

    if source_status == "failed":
        return MemoryIndexingDecision(
            indexable=False,
            content_kind="tool_error",
            quality_flags=["tool_error"],
            skipped_reasons=["tool_error"],
            derived_from_recall=derived_from_recall,
        )

    if any(re.search(pattern, normalized) for pattern in _PLACEHOLDER_PATTERNS):
        flags.append("placeholder")
        skipped.append("placeholder")

    if any(re.search(pattern, normalized) for pattern in _TOOL_ERROR_PATTERNS):
        flags.append("tool_error")
        skipped.append("tool_error")

    if prompt_reference and normalized_lexical_similarity(normalized, prompt_reference) > 0.92:
        flags.append("prompt_echo")
        skipped.append("prompt_echo")

    if skipped:
        return MemoryIndexingDecision(
            indexable=False,
            content_kind="placeholder" if "placeholder" in flags else "tool_error",
            quality_flags=list(dict.fromkeys(flags)),
            skipped_reasons=list(dict.fromkeys(skipped)),
            derived_from_recall=derived_from_recall,
        )

    return MemoryIndexingDecision(
        indexable=True,
        content_kind="answer",
        answer_bearing=True,
        derived_from_recall=derived_from_recall,
    )
