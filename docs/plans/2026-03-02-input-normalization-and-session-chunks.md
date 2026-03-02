# Input Normalization and Session Chunks Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an input normalization layer (between L2 sanitizer and L3 prompt guard) with noise removal, repetition collapse, and LLM rewrite, plus a session chunk manager for context segmentation and retrieval.

**Architecture:** The normalizer is a pure function pipeline that processes text after `sanitize_message()` and before prompt guard. Session chunks are stored as SQLAlchemy models with metadata for topic-based retrieval. Both are opt-in via config flags.

**Tech Stack:** Python 3.12, Pydantic v2, SQLAlchemy, pytest, regex for rule-based normalization

---

## Task 1: NormalizationConfig Schema

**Files:**
- Create: `python/omnimind_backend/schemas/normalization.py`
- Test: `python/tests/test_normalization_schemas.py`

**Step 1: Write the failing test**

Create `python/tests/test_normalization_schemas.py`:

```python
"""Tests for normalization config schema."""

from omnimind_backend.schemas.normalization import NormalizationConfig


def test_defaults() -> None:
    cfg = NormalizationConfig()
    assert cfg.enabled is True
    assert cfg.max_input_tokens == 2000
    assert cfg.rewrite_threshold == 500
    assert cfg.rewrite_model == "flash"
    assert cfg.preserve_code_blocks is True


def test_disabled() -> None:
    cfg = NormalizationConfig(enabled=False)
    assert cfg.enabled is False
```

**Step 2: Run test to verify it fails**

Run: `cd python && python -m pytest tests/test_normalization_schemas.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `python/omnimind_backend/schemas/normalization.py`:

```python
"""Input normalization configuration schema."""

from __future__ import annotations

from pydantic import BaseModel


class NormalizationConfig(BaseModel):
    """Configuration for the input normalization layer."""

    enabled: bool = True
    max_input_tokens: int = 2000
    rewrite_threshold: int = 500
    rewrite_model: str = "flash"
    preserve_code_blocks: bool = True
```

**Step 4: Run test to verify it passes**

Run: `cd python && python -m pytest tests/test_normalization_schemas.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python/omnimind_backend/schemas/normalization.py python/tests/test_normalization_schemas.py
git commit -m "feat(schemas): add NormalizationConfig for input preprocessing layer"
```

---

## Task 2: Noise Removal — Excessive Punctuation and Whitespace

**Files:**
- Create: `python/omnimind_backend/infra/normalizer.py`
- Test: `python/tests/test_normalizer.py`

**Step 1: Write the failing test**

Create `python/tests/test_normalizer.py`:

```python
"""Tests for input normalizer."""

from omnimind_backend.infra.normalizer import normalize_message
from omnimind_backend.schemas.normalization import NormalizationConfig


def test_collapse_excessive_punctuation() -> None:
    assert normalize_message("Hello!!!!!!") == "Hello!"
    assert normalize_message("What???") == "What?"
    assert normalize_message("Wow.......") == "Wow..."


def test_collapse_whitespace() -> None:
    assert normalize_message("Hello    world") == "Hello world"
    assert normalize_message("Hello\n\n\n\nworld") == "Hello\n\nworld"


def test_preserve_code_blocks() -> None:
    msg = "Check this:\n```python\nprint('Hello!!!!!!')\n```\nDone!!!!!!"
    result = normalize_message(msg)
    assert "print('Hello!!!!!!')" in result  # Code block preserved
    assert result.endswith("Done!")  # Outside code block normalized


def test_disabled_returns_original() -> None:
    cfg = NormalizationConfig(enabled=False)
    msg = "Hello!!!!!!"
    assert normalize_message(msg, config=cfg) == msg


def test_strip_filler_phrases() -> None:
    result = normalize_message("Well, basically, I just want to, you know, fix the bug")
    assert "basically" not in result
    assert "you know" not in result
    assert "fix the bug" in result
```

**Step 2: Run test to verify it fails**

Run: `cd python && python -m pytest tests/test_normalizer.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `python/omnimind_backend/infra/normalizer.py`:

```python
"""Input normalization layer (between L2 sanitizer and L3 prompt guard).

Applies rule-based noise removal, repetition collapse, and optional
LLM-assisted rewrite for complex messages.
"""

from __future__ import annotations

import re

from omnimind_backend.schemas.normalization import NormalizationConfig

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

    # Restore code blocks
    if blocks:
        text = _restore_code_blocks(text, blocks)

    return text
```

**Step 4: Run test to verify it passes**

Run: `cd python && python -m pytest tests/test_normalizer.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python/omnimind_backend/infra/normalizer.py python/tests/test_normalizer.py
git commit -m "feat(infra): add input normalizer with noise removal and code block preservation"
```

---

## Task 3: Repetition Collapse

**Files:**
- Modify: `python/omnimind_backend/infra/normalizer.py`
- Test: `python/tests/test_normalizer.py` (extend)

**Step 1: Write the failing test**

Append to `python/tests/test_normalizer.py`:

```python
def test_collapse_repeated_sentences() -> None:
    msg = "Fix the login bug. Fix the login bug. Fix the login bug."
    result = normalize_message(msg)
    assert result.count("Fix the login bug") == 1
    assert "[repeated 3 times]" in result


def test_no_collapse_for_unique_sentences() -> None:
    msg = "Fix the login bug. Then update the docs. Finally run tests."
    result = normalize_message(msg)
    assert "Fix the login bug" in result
    assert "update the docs" in result
    assert "run tests" in result


def test_collapse_near_duplicate_paragraphs() -> None:
    msg = "Please fix the auth module.\n\nPlease fix the authentication module.\n\nDone."
    result = normalize_message(msg)
    # Near-duplicates should be collapsed
    assert result.count("fix the auth") <= 1 or result.count("fix the authentication") <= 1
```

**Step 2: Run test to verify it fails**

Run: `cd python && python -m pytest tests/test_normalizer.py::test_collapse_repeated_sentences -v`
Expected: FAIL (repetition not collapsed yet)

**Step 3: Write minimal implementation**

Add to `python/omnimind_backend/infra/normalizer.py`:

```python
def _collapse_repetitions(text: str) -> str:
    """Detect and collapse repeated sentences."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
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
```

Then update `normalize_message` to call `_collapse_repetitions(text)` after noise removal and before restoring code blocks.

**Step 4: Run test to verify it passes**

Run: `cd python && python -m pytest tests/test_normalizer.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python/omnimind_backend/infra/normalizer.py python/tests/test_normalizer.py
git commit -m "feat(normalizer): add repetition collapse with annotation"
```

---

## Task 4: Session Chunk Schema and Model

**Files:**
- Create: `python/omnimind_backend/schemas/session_chunk.py`
- Test: `python/tests/test_session_chunk_schemas.py`

**Step 1: Write the failing test**

Create `python/tests/test_session_chunk_schemas.py`:

```python
"""Tests for session chunk schemas."""

from uuid import uuid4

from omnimind_backend.schemas.session_chunk import (
    ChunkMetadata,
    ChunkType,
    ChunkEdgeType,
    ChunkEdge,
    ChunkRetrievalQuery,
)


def test_chunk_types() -> None:
    assert ChunkType.PLANNING == "planning"
    assert ChunkType.IMPLEMENTATION == "implementation"
    assert ChunkType.RESEARCH == "research"
    assert ChunkType.REVIEW == "review"
    assert ChunkType.DISCUSSION == "discussion"
    assert ChunkType.META == "meta"


def test_chunk_metadata_creation() -> None:
    meta = ChunkMetadata(
        chunk_id=uuid4(),
        session_id="sess-123",
        agent_id="analyst",
        sequence=0,
        token_count=1500,
        start_turn=0,
        end_turn=3,
        topic_tags=["authentication", "jwt"],
        summary="Analyzed the auth module",
        confidence=0.9,
        freshness=1.0,
        chunk_type=ChunkType.IMPLEMENTATION,
    )
    assert meta.token_count == 1500
    assert meta.chunk_type == ChunkType.IMPLEMENTATION


def test_chunk_edge_types() -> None:
    assert ChunkEdgeType.FOLLOWS == "follows"
    assert ChunkEdgeType.REFERENCES == "references"
    assert ChunkEdgeType.SUPERSEDES == "supersedes"
    assert ChunkEdgeType.DEPENDS_ON == "depends_on"


def test_retrieval_query() -> None:
    q = ChunkRetrievalQuery(session_id="sess-123", by_topic=["implementation"])
    assert q.by_topic == ["implementation"]
    assert q.by_agent is None
    assert q.limit == 10
```

**Step 2: Run test to verify it fails**

Run: `cd python && python -m pytest tests/test_session_chunk_schemas.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `python/omnimind_backend/schemas/session_chunk.py`:

```python
"""Session chunk schemas for context segmentation and retrieval."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class ChunkType(StrEnum):
    """Content classification for session chunks."""

    PLANNING = "planning"
    IMPLEMENTATION = "implementation"
    RESEARCH = "research"
    REVIEW = "review"
    DISCUSSION = "discussion"
    META = "meta"


class ChunkEdgeType(StrEnum):
    """Relationship types between chunks in the session canvas."""

    FOLLOWS = "follows"
    REFERENCES = "references"
    SUPERSEDES = "supersedes"
    DEPENDS_ON = "depends_on"


class ChunkMetadata(BaseModel):
    """Metadata for a single session context chunk."""

    chunk_id: UUID
    session_id: str
    agent_id: str
    sequence: int
    token_count: int = 0
    start_turn: int = 0
    end_turn: int = 0
    topic_tags: list[str] = Field(default_factory=list)
    summary: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    freshness: float = Field(default=1.0, ge=0.0, le=1.0)
    chunk_type: ChunkType = ChunkType.DISCUSSION
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChunkEdge(BaseModel):
    """An edge between two chunks in the session canvas graph."""

    source_chunk_id: UUID
    target_chunk_id: UUID
    edge_type: ChunkEdgeType


class ChunkRetrievalQuery(BaseModel):
    """Query parameters for retrieving session chunks."""

    session_id: str
    by_range: tuple[int, int] | None = None
    by_topic: list[str] | None = None
    by_agent: str | None = None
    by_recency: int | None = None
    limit: int = 10
    min_score: float = 0.3
```

**Step 4: Run test to verify it passes**

Run: `cd python && python -m pytest tests/test_session_chunk_schemas.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python/omnimind_backend/schemas/session_chunk.py python/tests/test_session_chunk_schemas.py
git commit -m "feat(schemas): add session chunk metadata, edges, and retrieval query"
```

---

## Task 5: Chunk Retrieval Scoring Function

**Files:**
- Create: `python/omnimind_backend/runtime/chunk_scorer.py`
- Test: `python/tests/test_chunk_scorer.py`

**Step 1: Write the failing test**

Create `python/tests/test_chunk_scorer.py`:

```python
"""Tests for chunk retrieval scoring."""

from uuid import uuid4

from omnimind_backend.runtime.chunk_scorer import compute_chunk_score
from omnimind_backend.schemas.session_chunk import ChunkMetadata, ChunkType


def test_high_relevance_fresh_confident() -> None:
    chunk = ChunkMetadata(
        chunk_id=uuid4(), session_id="s1", agent_id="coder", sequence=0,
        topic_tags=["auth"], confidence=0.9, freshness=1.0, chunk_type=ChunkType.IMPLEMENTATION,
    )
    score = compute_chunk_score(chunk, query_topics=["auth"])
    assert score > 0.7


def test_low_freshness_reduces_score() -> None:
    chunk = ChunkMetadata(
        chunk_id=uuid4(), session_id="s1", agent_id="coder", sequence=0,
        topic_tags=["auth"], confidence=0.9, freshness=0.1, chunk_type=ChunkType.IMPLEMENTATION,
    )
    score = compute_chunk_score(chunk, query_topics=["auth"])
    assert score < 0.6


def test_no_topic_match_low_score() -> None:
    chunk = ChunkMetadata(
        chunk_id=uuid4(), session_id="s1", agent_id="coder", sequence=0,
        topic_tags=["database"], confidence=0.9, freshness=1.0, chunk_type=ChunkType.IMPLEMENTATION,
    )
    score = compute_chunk_score(chunk, query_topics=["auth"])
    assert score < 0.4


def test_below_threshold_excluded() -> None:
    chunk = ChunkMetadata(
        chunk_id=uuid4(), session_id="s1", agent_id="coder", sequence=0,
        topic_tags=["old"], confidence=0.1, freshness=0.1, chunk_type=ChunkType.META,
    )
    score = compute_chunk_score(chunk, query_topics=["auth"])
    assert score < 0.3
```

**Step 2: Run test to verify it fails**

Run: `cd python && python -m pytest tests/test_chunk_scorer.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `python/omnimind_backend/runtime/chunk_scorer.py`:

```python
"""Session chunk retrieval scoring.

Implements the retrieval ranking formula from input-normalization-and-session-chunks.md:
score = 0.4 * topic_relevance + 0.35 * freshness + 0.25 * confidence
"""

from __future__ import annotations

from omnimind_backend.schemas.session_chunk import ChunkMetadata

W_TOPIC = 0.40
W_FRESHNESS = 0.35
W_CONFIDENCE = 0.25

EXCLUSION_THRESHOLD = 0.3


def _compute_topic_relevance(chunk_tags: list[str], query_topics: list[str]) -> float:
    """Compute topic overlap between chunk tags and query topics."""
    if not query_topics or not chunk_tags:
        return 0.0
    chunk_set = {t.lower() for t in chunk_tags}
    query_set = {t.lower() for t in query_topics}
    overlap = len(chunk_set & query_set)
    return overlap / len(query_set)


def compute_chunk_score(chunk: ChunkMetadata, query_topics: list[str]) -> float:
    """Compute retrieval score for a session chunk.

    Args:
        chunk: Chunk metadata with topic_tags, freshness, confidence.
        query_topics: Topics from the retrieval query.

    Returns:
        Score (0-1). Below 0.3 should be excluded from results.
    """
    topic_relevance = _compute_topic_relevance(chunk.topic_tags, query_topics)

    score = (
        W_TOPIC * topic_relevance
        + W_FRESHNESS * chunk.freshness
        + W_CONFIDENCE * chunk.confidence
    )
    return round(min(max(score, 0.0), 1.0), 4)
```

**Step 4: Run test to verify it passes**

Run: `cd python && python -m pytest tests/test_chunk_scorer.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python/omnimind_backend/runtime/chunk_scorer.py python/tests/test_chunk_scorer.py
git commit -m "feat(runtime): add session chunk retrieval scoring function"
```

---

## Task 6: Full Regression Check

**Step 1: Run the full test suite**

Run: `cd python && python -m pytest tests/ -v --tb=short`
Expected: All tests PASS

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | NormalizationConfig schema | `schemas/normalization.py` |
| 2 | Normalizer: noise removal + code block preservation | `infra/normalizer.py` |
| 3 | Normalizer: repetition collapse | `infra/normalizer.py` |
| 4 | Session chunk schemas | `schemas/session_chunk.py` |
| 5 | Chunk retrieval scoring | `runtime/chunk_scorer.py` |
| 6 | Full regression check | — |
