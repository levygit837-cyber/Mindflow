"""Orchestrator router — keyword-based message routing.

Analyzes the user message and produces an ``OrchestratorDecision``
selecting the most appropriate agent personality, tool scopes, and
execution parameters.

Phase 2 uses heuristic keyword matching.  Phase 3 will add LLM-powered
intent classification for higher accuracy.
"""

from __future__ import annotations

import re

from omnimind_backend.infra.logging import get_logger
from omnimind_backend.schemas.orchestrator import (
    AgentType,
    OrchestratorDecision,
    Priority,
    ThinkingLevel,
    ToolScope,
)

_logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Keyword maps
# ---------------------------------------------------------------------------

_AGENT_KEYWORDS: dict[AgentType, list[str]] = {
    AgentType.CODER: [
        "code", "implement", "fix", "bug", "debug", "refactor", "function",
        "class", "module", "script", "compile", "build", "deploy", "test",
        "error", "exception", "syntax", "import", "package", "install",
        "migrate", "endpoint", "api", "backend", "frontend", "commit",
        "coding", "programm", "codigo", "implementar", "corrigir",
    ],
    AgentType.ANALYST: [
        "analyze", "data", "metrics", "insight", "statistic", "dashboard",
        "report", "trend", "pattern", "performance", "benchmark", "measure",
        "count", "average", "median", "distribution", "analis", "dados",
        "relatório",
    ],
    AgentType.RESEARCHER: [
        "research", "search", "find", "latest", "news", "documentation",
        "docs", "paper", "article", "tutorial", "guide", "learn",
        "compare", "alternative", "library", "framework", "tool",
        "pesquis", "buscar", "procurar", "noticia",
    ],
    AgentType.ARCH_TECH: [
        "architecture", "design", "system", "pattern", "scale", "microservice",
        "monolith", "database", "schema", "infrastructure", "cloud",
        "container", "kubernetes", "docker", "ci/cd", "pipeline",
        "tradeoff", "trade-off", "arquitetura", "projeto", "sistema",
    ],
    AgentType.CRITIC: [
        "review", "critique", "evaluate", "improve", "feedback", "quality",
        "smell", "anti-pattern", "best practice", "convention", "style",
        "readability", "maintainability", "coverage", "lint",
        "revisar", "avaliar", "melhorar",
    ],
}

# Pre-compile a single regex per agent for efficient matching.
_AGENT_PATTERNS: dict[AgentType, re.Pattern[str]] = {
    agent_type: re.compile(
        r"\b(?:" + "|".join(re.escape(kw) for kw in keywords) + r")",
        re.IGNORECASE,
    )
    for agent_type, keywords in _AGENT_KEYWORDS.items()
}

# Default tool scopes per agent type.
_AGENT_TOOLS: dict[AgentType, list[ToolScope]] = {
    AgentType.CODER: [ToolScope.FILESYSTEM, ToolScope.SHELL],
    AgentType.ANALYST: [ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM],
    AgentType.RESEARCHER: [ToolScope.WEB_SEARCH],
    AgentType.ARCH_TECH: [ToolScope.FILESYSTEM, ToolScope.CODE_ANALYSIS],
    AgentType.CRITIC: [ToolScope.CODE_ANALYSIS],
}

# Default thinking level per agent type.
_AGENT_THINKING: dict[AgentType, ThinkingLevel] = {
    AgentType.CODER: ThinkingLevel.HIGH,
    AgentType.ANALYST: ThinkingLevel.MEDIUM,
    AgentType.RESEARCHER: ThinkingLevel.MEDIUM,
    AgentType.ARCH_TECH: ThinkingLevel.HIGH,
    AgentType.CRITIC: ThinkingLevel.MEDIUM,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def route_message(message: str) -> OrchestratorDecision:
    """Route a user message to the best-matching agent personality.

    Scores each agent type by keyword hits in the message and selects
    the highest scorer.  Falls back to ``CODER`` on ties or zero hits.
    """
    scores: dict[AgentType, int] = {}
    for agent_type, pattern in _AGENT_PATTERNS.items():
        hits = pattern.findall(message)
        scores[agent_type] = len(hits)

    # Pick the agent with the highest score, defaulting to CODER.
    best_agent = max(scores, key=lambda a: scores[a]) if any(scores.values()) else AgentType.CODER

    # If the best score is 0, fall back to CODER.
    if scores.get(best_agent, 0) == 0:
        best_agent = AgentType.CODER

    decision = OrchestratorDecision(
        rationale=f"Keyword routing selected {best_agent.value} (score: {scores.get(best_agent, 0)})",
        agent=best_agent,
        task=message,
        thinking=_AGENT_THINKING.get(best_agent, ThinkingLevel.MEDIUM),
        tools=_AGENT_TOOLS.get(best_agent, []),
        priority=Priority.NORMAL,
    )

    _logger.info(
        "message_routed",
        agent=best_agent.value,
        scores={k.value: v for k, v in scores.items()},
    )

    return decision
