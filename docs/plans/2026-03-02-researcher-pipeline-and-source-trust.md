# Researcher Pipeline and Source Trust Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add request type classification, query planning, source tiering, relevance/confidence scoring, cross-source reanalysis, and structured citation output to the Researcher agent.

**Architecture:** Creates a `researcher/` module under `agents/` with a pipeline of pure functions: classify → plan_queries → score_sources → cross_analyze → format_output. Each step is independently testable. The existing `search_web` tool feeds raw results into this pipeline.

**Tech Stack:** Python 3.12, Pydantic v2, pytest, existing `agents/tools/search_web.py`

---

## Task 1: Request Type and Source Tier Schemas

**Files:**
- Create: `python/omnimind_backend/schemas/researcher.py`
- Test: `python/tests/test_researcher_schemas.py`

**Step 1: Write the failing test**

Create `python/tests/test_researcher_schemas.py`:

```python
"""Tests for researcher pipeline schemas."""

from omnimind_backend.schemas.researcher import (
    RequestType,
    SourceTier,
    SOURCE_TRUST_WEIGHTS,
    QueryPlan,
    SourceResult,
    ResearchOutput,
)


def test_request_types() -> None:
    assert RequestType.DEFINITION == "definition"
    assert RequestType.TUTORIAL == "tutorial"
    assert RequestType.COMPARISON == "comparison"
    assert RequestType.CURRENT_STATE == "current_state"
    assert RequestType.DEBUG == "debug"


def test_source_tiers() -> None:
    assert SourceTier.OFFICIAL == "official"
    assert SourceTier.ACADEMIC == "academic"
    assert SourceTier.NON_OFFICIAL == "non_official"
    assert SourceTier.UNKNOWN == "unknown"
    assert SourceTier.SOCIAL == "social"


def test_trust_weights() -> None:
    assert SOURCE_TRUST_WEIGHTS[SourceTier.OFFICIAL] == 1.0
    assert SOURCE_TRUST_WEIGHTS[SourceTier.ACADEMIC] == 0.9
    assert SOURCE_TRUST_WEIGHTS[SourceTier.NON_OFFICIAL] == 0.7
    assert SOURCE_TRUST_WEIGHTS[SourceTier.UNKNOWN] == 0.4
    assert SOURCE_TRUST_WEIGHTS[SourceTier.SOCIAL] == 0.3


def test_query_plan() -> None:
    plan = QueryPlan(
        request_type=RequestType.COMPARISON,
        queries=["Python vs Go performance", "Python Go benchmark 2026"],
        complexity="medium",
    )
    assert len(plan.queries) == 2


def test_source_result() -> None:
    r = SourceResult(
        url="https://docs.python.org/3/",
        tier=SourceTier.OFFICIAL,
        relevance=0.95,
        confidence=88,
        key_findings=["Python 3.12 supports better typing"],
    )
    assert r.confidence >= 20  # Above filtering threshold


def test_research_output_round_trip() -> None:
    output = ResearchOutput(
        summary="Python is faster in 3.12",
        answer="Use Python 3.12 for better perf",
        citations=["https://docs.python.org/3/"],
    )
    data = output.model_dump()
    assert data["summary"] == "Python is faster in 3.12"
```

**Step 2: Run test to verify it fails**

Run: `cd python && python -m pytest tests/test_researcher_schemas.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `python/omnimind_backend/schemas/researcher.py`:

```python
"""Researcher pipeline schemas.

Defines request types, source tiers, query plans, and the structured
research output contract as specified in researcher-pipeline-and-source-trust.md.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class RequestType(StrEnum):
    """Classification of research requests."""

    DEFINITION = "definition"
    TUTORIAL = "tutorial"
    COMPARISON = "comparison"
    CURRENT_STATE = "current_state"
    DEBUG = "debug"
    GENERAL = "general"
    INFORMATION = "information"
    DOCUMENTATION = "documentation"


class SourceTier(StrEnum):
    """Trust classification of information sources."""

    OFFICIAL = "official"
    ACADEMIC = "academic"
    NON_OFFICIAL = "non_official"
    UNKNOWN = "unknown"
    SOCIAL = "social"


SOURCE_TRUST_WEIGHTS: dict[SourceTier, float] = {
    SourceTier.OFFICIAL: 1.0,
    SourceTier.ACADEMIC: 0.9,
    SourceTier.NON_OFFICIAL: 0.7,
    SourceTier.UNKNOWN: 0.4,
    SourceTier.SOCIAL: 0.3,
}


class QueryPlan(BaseModel):
    """Planned queries for a research session."""

    request_type: RequestType
    queries: list[str] = Field(default_factory=list)
    complexity: str = "low"


class SourceResult(BaseModel):
    """A single source result with scoring."""

    url: str
    tier: SourceTier = SourceTier.UNKNOWN
    relevance: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence: int = Field(default=0, ge=0, le=100)
    key_findings: list[str] = Field(default_factory=list)


class ResearchPath(BaseModel):
    """A single query execution path."""

    query: str
    sources_found: int = 0
    sources_used: int = 0
    sources: list[SourceResult] = Field(default_factory=list)


class ResearchOutput(BaseModel):
    """Full structured output from the Researcher pipeline."""

    summary: str = ""
    research_path: list[ResearchPath] = Field(default_factory=list)
    results: list[SourceResult] = Field(default_factory=list)
    cross_analysis: str = ""
    answer: str = ""
    citations: list[str] = Field(default_factory=list)
    points: list[str] = Field(default_factory=list)
```

**Step 4: Run test to verify it passes**

Run: `cd python && python -m pytest tests/test_researcher_schemas.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python/omnimind_backend/schemas/researcher.py python/tests/test_researcher_schemas.py
git commit -m "feat(schemas): add researcher pipeline schemas with source tiering"
```

---

## Task 2: Request Type Classifier

**Files:**
- Create: `python/omnimind_backend/agents/researcher/classifier.py`
- Test: `python/tests/test_researcher_classifier.py`

**Step 1: Write the failing test**

Create `python/tests/test_researcher_classifier.py`:

```python
"""Tests for research request type classifier."""

from omnimind_backend.agents.researcher.classifier import classify_request
from omnimind_backend.schemas.researcher import RequestType


def test_definition_request() -> None:
    assert classify_request("What is a microservice?") == RequestType.DEFINITION


def test_tutorial_request() -> None:
    assert classify_request("How to set up Docker Compose?") == RequestType.TUTORIAL


def test_comparison_request() -> None:
    assert classify_request("Python vs Go for web APIs") == RequestType.COMPARISON


def test_current_state_request() -> None:
    assert classify_request("What is the latest version of React?") == RequestType.CURRENT_STATE


def test_debug_request() -> None:
    assert classify_request("Why does my app crash on startup?") == RequestType.DEBUG


def test_documentation_request() -> None:
    assert classify_request("Show me the FastAPI documentation for middleware") == RequestType.DOCUMENTATION


def test_fallback_to_general() -> None:
    assert classify_request("Tell me about cats") == RequestType.GENERAL
```

**Step 2: Run test to verify it fails**

Run: `cd python && python -m pytest tests/test_researcher_classifier.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `python/omnimind_backend/agents/researcher/__init__.py` (empty) and:

Create `python/omnimind_backend/agents/researcher/classifier.py`:

```python
"""Research request type classification.

Keyword-based classifier that determines the research approach
based on the user's request pattern.
"""

from __future__ import annotations

import re

from omnimind_backend.schemas.researcher import RequestType

_PATTERNS: list[tuple[RequestType, re.Pattern[str]]] = [
    (RequestType.DEFINITION, re.compile(r"\b(what is|what are|define|meaning of|explain)\b", re.I)),
    (RequestType.TUTORIAL, re.compile(r"\b(how to|how do|step.?by.?step|guide|tutorial|setup|set up)\b", re.I)),
    (RequestType.COMPARISON, re.compile(r"\b(vs|versus|compare|comparison|differ|better)\b", re.I)),
    (RequestType.CURRENT_STATE, re.compile(r"\b(latest|newest|current|recent|update|2026|2025)\b", re.I)),
    (RequestType.DEBUG, re.compile(r"\b(why does|crash|error|fail|bug|broken|not work|issue)\b", re.I)),
    (RequestType.DOCUMENTATION, re.compile(r"\b(documentation|docs|api ref|reference|manual)\b", re.I)),
    (RequestType.INFORMATION, re.compile(r"\b(show me|give me|list|find|get)\b", re.I)),
]


def classify_request(message: str) -> RequestType:
    """Classify a research request by keyword pattern matching.

    Returns the first matching RequestType, or GENERAL as fallback.
    """
    for request_type, pattern in _PATTERNS:
        if pattern.search(message):
            return request_type
    return RequestType.GENERAL
```

**Step 4: Run test to verify it passes**

Run: `cd python && python -m pytest tests/test_researcher_classifier.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python/omnimind_backend/agents/researcher/__init__.py python/omnimind_backend/agents/researcher/classifier.py python/tests/test_researcher_classifier.py
git commit -m "feat(researcher): add request type classifier with keyword patterns"
```

---

## Task 3: Source Tier Classifier

**Files:**
- Create: `python/omnimind_backend/agents/researcher/source_tier.py`
- Test: `python/tests/test_source_tier.py`

**Step 1: Write the failing test**

Create `python/tests/test_source_tier.py`:

```python
"""Tests for source tier classification."""

from omnimind_backend.agents.researcher.source_tier import classify_source
from omnimind_backend.schemas.researcher import SourceTier


def test_official_docs() -> None:
    assert classify_source("https://docs.python.org/3/library/os.html") == SourceTier.OFFICIAL
    assert classify_source("https://developer.mozilla.org/en-US/docs/Web") == SourceTier.OFFICIAL


def test_academic() -> None:
    assert classify_source("https://arxiv.org/abs/2301.12345") == SourceTier.ACADEMIC


def test_social() -> None:
    assert classify_source("https://twitter.com/user/status/123") == SourceTier.SOCIAL
    assert classify_source("https://www.reddit.com/r/python/comments/abc") == SourceTier.SOCIAL


def test_non_official() -> None:
    assert classify_source("https://medium.com/@author/article") == SourceTier.NON_OFFICIAL
    assert classify_source("https://dev.to/user/post") == SourceTier.NON_OFFICIAL


def test_unknown_fallback() -> None:
    assert classify_source("https://random-site.xyz/page") == SourceTier.UNKNOWN
```

**Step 2: Run test to verify it fails**

Run: `cd python && python -m pytest tests/test_source_tier.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `python/omnimind_backend/agents/researcher/source_tier.py`:

```python
"""Source tier classification by URL domain.

Classifies URLs into trust tiers for relevance scoring.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from omnimind_backend.schemas.researcher import SourceTier

_OFFICIAL_DOMAINS = {
    "docs.python.org", "developer.mozilla.org", "docs.oracle.com",
    "learn.microsoft.com", "cloud.google.com", "docs.aws.amazon.com",
    "reactjs.org", "vuejs.org", "angular.io", "fastapi.tiangolo.com",
    "docs.djangoproject.com", "kubernetes.io", "docs.docker.com",
    "pkg.go.dev", "doc.rust-lang.org", "nodejs.org",
}

_ACADEMIC_DOMAINS = {"arxiv.org", "scholar.google.com", "ieee.org", "acm.org", "researchgate.net"}

_SOCIAL_DOMAINS = {
    "twitter.com", "x.com", "reddit.com", "news.ycombinator.com",
    "facebook.com", "linkedin.com",
}

_NON_OFFICIAL_DOMAINS = {
    "medium.com", "dev.to", "hashnode.dev", "substack.com",
    "towardsdatascience.com", "freecodecamp.org", "baeldung.com",
}


def classify_source(url: str) -> SourceTier:
    """Classify a URL into a source trust tier."""
    try:
        domain = urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return SourceTier.UNKNOWN

    if domain in _OFFICIAL_DOMAINS or domain.endswith(".gov"):
        return SourceTier.OFFICIAL
    if domain in _ACADEMIC_DOMAINS or domain.endswith(".edu"):
        return SourceTier.ACADEMIC
    if domain in _SOCIAL_DOMAINS:
        return SourceTier.SOCIAL
    if domain in _NON_OFFICIAL_DOMAINS:
        return SourceTier.NON_OFFICIAL

    # Check for official subdomains (e.g., docs.*.io)
    if domain.startswith("docs.") or domain.startswith("api."):
        return SourceTier.OFFICIAL

    return SourceTier.UNKNOWN
```

**Step 4: Run test to verify it passes**

Run: `cd python && python -m pytest tests/test_source_tier.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python/omnimind_backend/agents/researcher/source_tier.py python/tests/test_source_tier.py
git commit -m "feat(researcher): add source tier classifier by URL domain"
```

---

## Task 4: Relevance and Confidence Scoring

**Files:**
- Create: `python/omnimind_backend/agents/researcher/scoring.py`
- Test: `python/tests/test_researcher_scoring.py`

**Step 1: Write the failing test**

Create `python/tests/test_researcher_scoring.py`:

```python
"""Tests for researcher source scoring."""

from omnimind_backend.agents.researcher.scoring import (
    compute_confidence,
    filter_results,
)
from omnimind_backend.schemas.researcher import SourceResult, SourceTier


def test_official_source_high_confidence() -> None:
    score = compute_confidence(tier=SourceTier.OFFICIAL, cross_ref_count=2)
    assert score >= 70


def test_social_source_low_confidence() -> None:
    score = compute_confidence(tier=SourceTier.SOCIAL, cross_ref_count=0)
    assert score <= 40


def test_cross_references_boost() -> None:
    base = compute_confidence(tier=SourceTier.UNKNOWN, cross_ref_count=0)
    boosted = compute_confidence(tier=SourceTier.UNKNOWN, cross_ref_count=3)
    assert boosted > base


def test_filter_low_confidence() -> None:
    results = [
        SourceResult(url="a", relevance=0.5, confidence=50, tier=SourceTier.OFFICIAL),
        SourceResult(url="b", relevance=0.1, confidence=10, tier=SourceTier.UNKNOWN),  # Below threshold
        SourceResult(url="c", relevance=0.8, confidence=80, tier=SourceTier.ACADEMIC),
    ]
    filtered = filter_results(results, min_relevance=0.3, min_confidence=20)
    assert len(filtered) == 2
    assert all(r.url != "b" for r in filtered)
```

**Step 2: Run test to verify it fails**

Run: `cd python && python -m pytest tests/test_researcher_scoring.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `python/omnimind_backend/agents/researcher/scoring.py`:

```python
"""Researcher source relevance and confidence scoring."""

from __future__ import annotations

from omnimind_backend.schemas.researcher import (
    SourceResult,
    SourceTier,
    SOURCE_TRUST_WEIGHTS,
)


def compute_confidence(
    tier: SourceTier,
    cross_ref_count: int = 0,
) -> int:
    """Compute confidence score (0-100) for a source.

    Based on tier trust weight and cross-reference count.
    """
    base = SOURCE_TRUST_WEIGHTS.get(tier, 0.4) * 70
    cross_ref_bonus = min(cross_ref_count * 10, 30)
    return min(int(base + cross_ref_bonus), 100)


def filter_results(
    results: list[SourceResult],
    min_relevance: float = 0.3,
    min_confidence: int = 20,
) -> list[SourceResult]:
    """Filter results below relevance or confidence thresholds."""
    return [
        r for r in results
        if r.relevance >= min_relevance and r.confidence >= min_confidence
    ]
```

**Step 4: Run test to verify it passes**

Run: `cd python && python -m pytest tests/test_researcher_scoring.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python/omnimind_backend/agents/researcher/scoring.py python/tests/test_researcher_scoring.py
git commit -m "feat(researcher): add source confidence scoring and result filtering"
```

---

## Task 5: Full Regression Check

**Step 1: Run the full test suite**

Run: `cd python && python -m pytest tests/ -v --tb=short`
Expected: All tests PASS

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | RequestType + SourceTier + output schemas | `schemas/researcher.py` |
| 2 | Request type classifier | `agents/researcher/classifier.py` |
| 3 | Source tier classifier | `agents/researcher/source_tier.py` |
| 4 | Confidence scoring + result filtering | `agents/researcher/scoring.py` |
| 5 | Full regression check | — |
